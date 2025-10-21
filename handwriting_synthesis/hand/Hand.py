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

    def _calculate_baseline_angle(self, stroke: np.ndarray) -> float:
        """
        Calculate the baseline angle of a stroke.

        Args:
            stroke: Input stroke sequence (offsets)

        Returns:
            Baseline angle in radians
        """
        if len(stroke) == 0:
            return 0.0

        # Convert to coordinates
        coords = drawing.offsets_to_coords(stroke)

        if len(coords) < 4:
            return 0.0

        y_values = coords[:, 1]
        y_range = np.max(y_values) - np.min(y_values)

        if y_range < 1.0:
            return 0.0

        # Focus on points between 60th-80th percentile (main baseline, excluding descenders)
        y_lower = np.percentile(y_values, 60)
        y_upper = np.percentile(y_values, 80)
        baseline_mask = (y_values >= y_lower) & (y_values <= y_upper)

        baseline_points = coords[baseline_mask]

        if len(baseline_points) < 3:
            y_threshold = np.percentile(y_values, 70)
            baseline_mask = y_values >= y_threshold
            baseline_points = coords[baseline_mask]

        if len(baseline_points) < 2:
            return 0.0

        # Fit linear regression to baseline points: y = mx + b
        x_baseline = baseline_points[:, 0]
        y_baseline = baseline_points[:, 1]

        # Use least squares to find slope
        A = np.vstack([x_baseline, np.ones(len(x_baseline))]).T
        result = np.linalg.lstsq(A, y_baseline, rcond=None)
        m, b = result[0]

        # Calculate rotation angle
        angle = np.arctan(m)

        return angle

    def _rotate_stroke(self, stroke: np.ndarray, angle: float, pivot_point: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Rotate a stroke by a given angle around a pivot point.

        Args:
            stroke: Input stroke sequence (offsets)
            angle: Rotation angle in radians (positive = counter-clockwise)
            pivot_point: Point to rotate around (default: center of stroke)

        Returns:
            Rotated stroke sequence (offsets)
        """
        if len(stroke) == 0 or abs(angle) < 1e-6:
            return stroke

        # Convert to coordinates
        coords = drawing.offsets_to_coords(stroke)

        if pivot_point is None:
            # Use center of stroke as pivot
            pivot_point = np.mean(coords[:, :2], axis=0)

        # Rotation matrix
        cos_angle = np.cos(angle)
        sin_angle = np.sin(angle)
        rotation_matrix = np.array([
            [cos_angle, -sin_angle],
            [sin_angle, cos_angle]
        ])

        # Apply rotation around pivot point
        coords_centered = coords[:, :2] - pivot_point
        coords_rotated = coords_centered @ rotation_matrix.T
        coords[:, :2] = coords_rotated + pivot_point

        # Convert back to offsets
        rotated = drawing.coords_to_offsets(coords)

        return rotated

    def _get_baseline_y(self, coords: np.ndarray) -> float:
        """
        Calculate a consistent baseline Y position for a set of stroke coordinates.

        Uses a robust method that focuses on the main body of text, excluding
        extreme points (descenders and ascenders).

        Args:
            coords: Stroke coordinates

        Returns:
            Y position of the baseline
        """
        if len(coords) == 0:
            return 0.0

        y_values = coords[:, 1]

        # Use the median of points in the lower-middle portion (60th-80th percentile)
        # This represents the main baseline while excluding deep descenders
        y_lower = np.percentile(y_values, 60)
        y_upper = np.percentile(y_values, 80)

        baseline_points = y_values[(y_values >= y_lower) & (y_values <= y_upper)]

        if len(baseline_points) > 0:
            # Use median for robustness against outliers
            return float(np.median(baseline_points))
        else:
            # Fallback: use 75th percentile
            return float(np.percentile(y_values, 75))

    def _stitch_strokes(
        self,
        stroke1: np.ndarray,
        stroke2: np.ndarray,
        spacing: float = 0.0,
        rotate_to_match: bool = True
    ) -> np.ndarray:
        """
        Stitch two stroke sequences together horizontally with improved baseline alignment
        and rotation correction to prevent cumulative slant.

        This method now:
        1. Calculates the baseline angle at the end of stroke1
        2. Rotates stroke2 to match that angle (compensating for cumulative slant)
        3. Aligns baselines vertically
        4. Stitches the strokes together

        Args:
            stroke1: First stroke sequence (offsets)
            stroke2: Second stroke sequence (offsets)
            spacing: Horizontal spacing between strokes
            rotate_to_match: If True, rotate stroke2 to match stroke1's ending angle

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

        if rotate_to_match:
            # Calculate the baseline angle at the end of stroke1
            # Use the last 40% of stroke1 to get the ending angle
            end_portion_start = int(len(coords1) * 0.6)
            end_coords = coords1[end_portion_start:]

            # Calculate ending angle using the same baseline detection
            if len(end_coords) >= 4:
                y_values = end_coords[:, 1]
                y_range = np.max(y_values) - np.min(y_values)

                if y_range >= 1.0:
                    y_lower = np.percentile(y_values, 60)
                    y_upper = np.percentile(y_values, 80)
                    baseline_mask = (y_values >= y_lower) & (y_values <= y_upper)
                    baseline_points = end_coords[baseline_mask]

                    if len(baseline_points) >= 2:
                        x_baseline = baseline_points[:, 0]
                        y_baseline = baseline_points[:, 1]
                        A = np.vstack([x_baseline, np.ones(len(x_baseline))]).T
                        result = np.linalg.lstsq(A, y_baseline, rcond=None)
                        m1, b1 = result[0]
                        ending_angle = np.arctan(m1)

                        # Calculate the baseline angle at the start of stroke2
                        start_angle = self._calculate_baseline_angle(stroke2)

                        # Calculate rotation needed to match angles
                        rotation_needed = ending_angle - start_angle

                        # Only rotate if the difference is significant
                        if abs(rotation_needed) > 0.005:  # ~0.3 degrees
                            # Rotate stroke2 around its starting point to match stroke1's ending angle
                            # Find the baseline point at the start of stroke2
                            y_values2 = coords2[:, 1]
                            baseline2_y = np.percentile(y_values2, 70)
                            baseline_points2 = coords2[coords2[:, 1] >= np.percentile(y_values2, 60)]
                            if len(baseline_points2) > 0:
                                pivot_x = np.min(baseline_points2[:, 0])
                                pivot_y = baseline2_y
                                pivot = np.array([pivot_x, pivot_y])

                                # Apply rotation
                                stroke2 = self._rotate_stroke(stroke2, rotation_needed, pivot)
                                coords2 = drawing.offsets_to_coords(stroke2)

        # Calculate horizontal offset needed for stroke2
        max_x1 = np.max(coords1[:, 0])
        min_x2 = np.min(coords2[:, 0])
        x_offset = max_x1 - min_x2 + spacing

        # Calculate vertical offset to align baselines using improved method
        baseline1 = self._get_baseline_y(coords1)
        baseline2 = self._get_baseline_y(coords2)
        y_offset = baseline1 - baseline2

        # Apply offsets to stroke2
        coords2[:, 0] += x_offset
        coords2[:, 1] += y_offset

        # Combine coordinates
        combined_coords = np.vstack([coords1, coords2])

        # Convert back to offsets
        combined_offsets = drawing.coords_to_offsets(combined_coords)

        return combined_offsets

    def _split_text_into_chunks(
        self,
        text: str,
        words_per_chunk: int = 4,
        target_chars_per_chunk: int = 25,
        min_words: int = 2,
        max_words: int = 8
    ) -> List[str]:
        """
        Split text into chunks with dynamic sizing based on word length.

        This method creates more natural chunks by:
        1. Using more words if they're short (better context for the model)
        2. Using fewer words if they're long (avoid exceeding limits)
        3. Ensuring reasonable min/max bounds

        Args:
            text: Input text to split
            words_per_chunk: Target number of words per chunk (used as baseline)
            target_chars_per_chunk: Target character count per chunk (default: 25)
            min_words: Minimum words per chunk
            max_words: Maximum words per chunk

        Returns:
            List of text chunks
        """
        words = text.split()
        if not words:
            return []

        chunks = []
        i = 0

        while i < len(words):
            # Start with the target words per chunk
            chunk_word_count = words_per_chunk

            # Look ahead to see the average word length
            lookahead_end = min(i + words_per_chunk * 2, len(words))
            lookahead_words = words[i:lookahead_end]

            if lookahead_words:
                avg_word_length = sum(len(w) for w in lookahead_words) / len(lookahead_words)

                # Adjust chunk size based on word length
                if avg_word_length < 4:  # Short words (a, an, the, is, of, etc.)
                    # Use more words to provide better context
                    chunk_word_count = min(max_words, int(words_per_chunk * 1.5))
                elif avg_word_length > 7:  # Long words
                    # Use fewer words to avoid too long chunks
                    chunk_word_count = max(min_words, int(words_per_chunk * 0.75))

            # Ensure we stay within bounds
            chunk_word_count = max(min_words, min(max_words, chunk_word_count))

            # Don't exceed remaining words
            chunk_word_count = min(chunk_word_count, len(words) - i)

            # Create the chunk
            chunk_words = words[i:i + chunk_word_count]
            chunk_text = ' '.join(chunk_words)

            # If chunk is too long (> 50 chars), split it
            if len(chunk_text) > 50 and len(chunk_words) > min_words:
                # Use fewer words
                chunk_word_count = max(min_words, len(chunk_words) // 2)
                chunk_words = words[i:i + chunk_word_count]
                chunk_text = ' '.join(chunk_words)

            chunks.append(chunk_text)
            i += chunk_word_count

        return chunks

    def write_chunked(
        self,
        filename,
        text,
        max_line_width=800.0,  # Increased from 550.0 for longer lines
        words_per_chunk=3,  # Increased from 2 for better context with dynamic sizing
        chunk_spacing=8.0,
        rotate_chunks=True,  # NEW: Enable rotation correction for cumulative slant
        min_words_per_chunk=2,  # NEW: Minimum words per chunk
        max_words_per_chunk=8,  # NEW: Maximum words per chunk
        target_chars_per_chunk=25,  # NEW: Target characters per chunk
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
        1. Splits text by newlines to preserve line breaks
        2. Generates text in small chunks (dynamically sized based on word length)
        3. Rotates chunks during stitching to prevent cumulative slant
        4. Measures the actual width of each generated chunk
        5. Stitches chunks together into lines based on actual measurements

        This allows:
        - Better line filling (using actual widths, not predictions)
        - Shorter RNN sequences (fewer long-range dependencies)
        - More text per line
        - Preserves blank lines and explicit line breaks
        - Natural-looking continuous writing without cumulative slant

        Args:
            filename: Output file path
            text: Full text to write (newlines preserved for line breaks)
            max_line_width: Maximum line width in coordinate units
            words_per_chunk: Target number of words per chunk (adjusted dynamically)
            chunk_spacing: Horizontal spacing between chunks
            rotate_chunks: Enable rotation correction to prevent cumulative slant
            min_words_per_chunk: Minimum words per chunk
            max_words_per_chunk: Maximum words per chunk
            target_chars_per_chunk: Target character count per chunk
            ... (other params same as write())
        """
        # Split text by newlines first to preserve line structure
        input_lines = text.split('\n')

        # Process each input line separately
        all_lines = []
        all_line_texts = []

        for input_line in input_lines:
            # Handle blank lines
            if not input_line.strip():
                all_lines.append(np.empty((0, 3)))
                all_line_texts.append('')
                continue

            # Split line into chunks with dynamic sizing
            chunks = self._split_text_into_chunks(
                input_line,
                words_per_chunk=words_per_chunk,
                target_chars_per_chunk=target_chars_per_chunk,
                min_words=min_words_per_chunk,
                max_words=max_words_per_chunk
            )

            if not chunks:
                all_lines.append(np.empty((0, 3)))
                all_line_texts.append('')
                continue

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
            # Now with rotation correction to prevent cumulative slant
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
                            chunk_spacing,
                            rotate_to_match=rotate_chunks
                        )
                        current_line_text.append(chunk_text)
                    else:
                        current_line_stroke = chunk_stroke
                        current_line_text.append(chunk_text)
                    current_line_width = potential_width
                else:
                    # Start new line (width exceeded)
                    all_lines.append(current_line_stroke)
                    all_line_texts.append(' '.join(current_line_text))

                    current_line_stroke = chunk_stroke
                    current_line_text = [chunk_text]
                    current_line_width = chunk_width

            # Add last line from this input line
            if len(current_line_stroke) > 0 or len(current_line_text) > 0:
                all_lines.append(current_line_stroke)
                all_line_texts.append(' '.join(current_line_text))

        # Use the collected lines
        lines = all_lines
        line_texts = all_line_texts

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
