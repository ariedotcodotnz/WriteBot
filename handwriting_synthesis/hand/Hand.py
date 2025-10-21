import logging
import os
from typing import List, Tuple, Optional

import numpy as np

from handwriting_synthesis import drawing
from handwriting_synthesis.config import prediction_path, checkpoint_path, style_path
from handwriting_synthesis.hand._draw import _draw
from handwriting_synthesis.rnn import RNN


class Hand(object):
    def __init__(self):
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        self.nn = RNN(
            log_dir='logs',
            checkpoint_dir=checkpoint_path,
            prediction_dir=prediction_path,
            learning_rates=[.0001, .00005, .00002],
            batch_sizes=[32, 64, 64],
            patiences=[1500, 1000, 500],
            beta1_decays=[.9, .9, .9],
            validation_batch_size=32,
            optimizer='rms',
            num_training_steps=100000,
            warm_start_init_step=17900,
            regularization_constant=0.0,
            keep_prob=1.0,
            enable_parameter_averaging=False,
            min_steps_to_checkpoint=2000,
            log_interval=20,
            logging_level=logging.CRITICAL,
            grad_clip=10,
            lstm_size=400,
            output_mixture_components=20,
            attention_mixture_components=10
        )
        self.nn.restore()

    def write(
        self,
        filename,
        lines,
        biases=None,
        styles=None,
        stroke_colors=None,
        stroke_widths=None,
        page_size='A4',
        units='mm',
        margins=20,
        line_height=None,
        align='left',
        background=None,
        global_scale=1.0,
        orientation='portrait',
        legibility='normal',
        x_stretch=1.0,
        denoise=True,
    ):
        def _normalize_seq(value, desired_len, cast_fn=None, name='param'):
            if value is None:
                return None
            # Accept scalar -> broadcast
            if not isinstance(value, (list, tuple, np.ndarray)):
                return [cast_fn(value) if cast_fn else value] * desired_len
            seq = list(value)
            if len(seq) == 1 and desired_len > 1:
                return [cast_fn(seq[0]) if cast_fn else seq[0]] * desired_len
            if len(seq) != desired_len:
                raise ValueError(
                    f"Length of {name} ({len(seq)}) must be 1 or equal to number of lines ({desired_len})"
                )
            return [cast_fn(v) if cast_fn else v for v in seq]
        valid_char_set = set(drawing.alphabet)
        for line_num, line in enumerate(lines):
            if len(line) > drawing.MAX_CHAR_LEN:
                raise ValueError(
                    (
                        "Each line must be at most {} characters. "
                        "Line {} contains {}"
                    ).format(drawing.MAX_CHAR_LEN, line_num, len(line))
                )

            for char in line:
                if char not in valid_char_set:
                    raise ValueError(
                        (
                            "Invalid character {} detected in line {}. "
                            "Valid character set is {}"
                        ).format(char, line_num, valid_char_set)
                    )

        # Normalize optional sequences to match number of lines
        num_lines = len(lines)
        biases = _normalize_seq(biases, num_lines, float, 'biases')
        styles = _normalize_seq(styles, num_lines, int, 'styles')
        stroke_colors = _normalize_seq(stroke_colors, num_lines, str, 'stroke_colors')
        stroke_widths = _normalize_seq(stroke_widths, num_lines, float, 'stroke_widths')

        strokes = self._sample(lines, biases=biases, styles=styles)
        _draw(
            strokes,
            lines,
            filename,
            stroke_colors=stroke_colors,
            stroke_widths=stroke_widths,
            page_size=page_size,
            units=units,
            margins=margins,
            line_height=line_height,
            align=align,
            background=background,
            global_scale=global_scale,
            orientation=orientation,
            legibility=legibility,
            x_stretch=x_stretch,
            denoise=denoise,
        )

    def _sample(self, lines, biases=None, styles=None):
        num_samples = len(lines)
        max_tsteps = 40 * max([len(i) for i in lines])
        biases = biases if biases is not None else [0.5] * num_samples

        x_prime = np.zeros([num_samples, drawing.MAX_STROKE_LEN, 3])
        x_prime_len = np.zeros([num_samples])
        chars = np.zeros([num_samples, 120])
        chars_len = np.zeros([num_samples])

        if styles is not None:
            for i, (cs, style) in enumerate(zip(lines, styles)):
                x_p = np.load(f"{style_path}/style-{style}-strokes.npy")
                c_p = np.load(f"{style_path}/style-{style}-chars.npy").tostring().decode('utf-8')

                c_p = str(c_p) + " " + cs
                c_p = drawing.encode_ascii(c_p)
                c_p = np.array(c_p)

                x_prime[i, :len(x_p), :] = x_p
                x_prime_len[i] = len(x_p)
                chars[i, :len(c_p)] = c_p
                chars_len[i] = len(c_p)

        else:
            for i in range(num_samples):
                encoded = drawing.encode_ascii(lines[i])
                chars[i, :len(encoded)] = encoded
                chars_len[i] = len(encoded)

        [samples] = self.nn.session.run(
            [self.nn.sampled_sequence],
            feed_dict={
                self.nn.prime: styles is not None,
                self.nn.x_prime: x_prime,
                self.nn.x_prime_len: x_prime_len,
                self.nn.num_samples: num_samples,
                self.nn.sample_tsteps: max_tsteps,
                self.nn.c: chars,
                self.nn.c_len: chars_len,
                self.nn.bias: biases
            }
        )
        samples = [sample[~np.all(sample == 0.0, axis=1)] for sample in samples]
        return samples

    def _get_stroke_width(self, stroke: np.ndarray) -> float:
        """Calculate the horizontal width of a stroke sequence."""
        if len(stroke) == 0:
            return 0.0
        coords = drawing.offsets_to_coords(stroke)
        return float(np.max(coords[:, 0]) - np.min(coords[:, 0]))

    def _stitch_strokes(
        self,
        stroke1: np.ndarray,
        stroke2: np.ndarray,
        spacing: float = 0.0
    ) -> np.ndarray:
        """
        Stitch two stroke sequences together horizontally.

        Args:
            stroke1: First stroke sequence (offsets)
            stroke2: Second stroke sequence (offsets)
            spacing: Horizontal spacing between strokes

        Returns:
            Combined stroke sequence
        """
        if len(stroke1) == 0:
            return stroke2
        if len(stroke2) == 0:
            return stroke1

        # Convert to coordinates
        coords1 = drawing.offsets_to_coords(stroke1)
        coords2 = drawing.offsets_to_coords(stroke2)

        # Calculate offset needed for stroke2
        max_x1 = np.max(coords1[:, 0])
        min_x2 = np.min(coords2[:, 0])
        x_offset = max_x1 - min_x2 + spacing

        # Apply offset to stroke2
        coords2[:, 0] += x_offset

        # Combine coordinates
        combined_coords = np.vstack([coords1, coords2])

        # Convert back to offsets
        combined_offsets = drawing.coords_to_offsets(combined_coords)

        return combined_offsets

    def _split_text_into_chunks(
        self,
        text: str,
        words_per_chunk: int = 4
    ) -> List[str]:
        """
        Split text into chunks of approximately words_per_chunk words.

        Args:
            text: Input text to split
            words_per_chunk: Target number of words per chunk

        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []

        for i in range(0, len(words), words_per_chunk):
            chunk = ' '.join(words[i:i + words_per_chunk])
            chunks.append(chunk)

        return chunks

    def write_chunked(
        self,
        filename,
        text,
        max_line_width=800.0,  # Increased from 550.0 for longer lines
        words_per_chunk=2,  # Reduced from 4 for better long-range dependency handling
        chunk_spacing=8.0,
        biases=None,
        styles=None,
        stroke_colors=None,
        stroke_widths=None,
        page_size='A4',
        units='mm',
        margins=20,
        line_height=None,
        align='left',
        background=None,
        global_scale=1.0,
        orientation='portrait',
        legibility='normal',
        x_stretch=1.0,
        denoise=True,
    ):
        """
        Generate handwriting using chunk-based approach to overcome long-range dependency.

        Instead of generating line-by-line, this method:
        1. Generates text in small chunks (a few words at a time)
        2. Measures the actual width of each generated chunk
        3. Stitches chunks together into lines based on actual measurements

        This allows:
        - Better line filling (using actual widths, not predictions)
        - Shorter RNN sequences (fewer long-range dependencies)
        - More text per line

        Args:
            filename: Output file path
            text: Full text to write (will be chunked automatically)
            max_line_width: Maximum line width in coordinate units
            words_per_chunk: Number of words to generate per chunk
            chunk_spacing: Horizontal spacing between chunks
            ... (other params same as write())
        """
        # Split text into chunks
        chunks = self._split_text_into_chunks(text, words_per_chunk)

        if not chunks:
            return

        # Validate characters
        valid_char_set = set(drawing.alphabet)
        for chunk_num, chunk in enumerate(chunks):
            for char in chunk:
                if char not in valid_char_set:
                    raise ValueError(
                        f"Invalid character {char} detected in chunk {chunk_num}. "
                        f"Valid character set is {valid_char_set}"
                    )

        # Generate strokes for all chunks
        chunk_strokes = self._sample(
            chunks,
            biases=[biases] * len(chunks) if biases is not None else None,
            styles=[styles] * len(chunks) if styles is not None else None
        )

        # Stitch chunks into lines based on actual widths
        lines = []
        line_texts = []
        current_line_stroke = np.empty((0, 3))
        current_line_text = []
        current_line_width = 0.0

        for chunk_text, chunk_stroke in zip(chunks, chunk_strokes):
            chunk_width = self._get_stroke_width(chunk_stroke)

            # Check if chunk fits on current line
            potential_width = current_line_width
            if current_line_width > 0:
                potential_width += chunk_spacing + chunk_width
            else:
                potential_width = chunk_width

            if potential_width <= max_line_width or current_line_width == 0:
                # Chunk fits on current line
                if current_line_width > 0:
                    current_line_stroke = self._stitch_strokes(
                        current_line_stroke,
                        chunk_stroke,
                        chunk_spacing
                    )
                    current_line_text.append(chunk_text)
                else:
                    current_line_stroke = chunk_stroke
                    current_line_text.append(chunk_text)
                current_line_width = potential_width
            else:
                # Start new line
                lines.append(current_line_stroke)
                line_texts.append(' '.join(current_line_text))

                current_line_stroke = chunk_stroke
                current_line_text = [chunk_text]
                current_line_width = chunk_width

        # Add last line
        if len(current_line_stroke) > 0:
            lines.append(current_line_stroke)
            line_texts.append(' '.join(current_line_text))

        # Normalize optional sequences to match number of lines
        num_lines = len(lines)

        def _normalize_seq(value, desired_len, cast_fn=None, name='param'):
            if value is None:
                return None
            if not isinstance(value, (list, tuple, np.ndarray)):
                return [cast_fn(value) if cast_fn else value] * desired_len
            seq = list(value)
            if len(seq) == 1 and desired_len > 1:
                return [cast_fn(seq[0]) if cast_fn else seq[0]] * desired_len
            if len(seq) != desired_len:
                return [cast_fn(seq[0]) if cast_fn else seq[0]] * desired_len
            return [cast_fn(v) if cast_fn else v for v in seq]

        stroke_colors = _normalize_seq(stroke_colors, num_lines, str, 'stroke_colors')
        stroke_widths = _normalize_seq(stroke_widths, num_lines, float, 'stroke_widths')

        # Draw the result
        _draw(
            lines,
            line_texts,
            filename,
            stroke_colors=stroke_colors,
            stroke_widths=stroke_widths,
            page_size=page_size,
            units=units,
            margins=margins,
            line_height=line_height,
            align=align,
            background=background,
            global_scale=global_scale,
            orientation=orientation,
            legibility=legibility,
            x_stretch=x_stretch,
            denoise=denoise,
        )
