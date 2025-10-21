"""
Refactored Hand class for handwriting synthesis.

This module provides the main interface for generating handwritten text using
a trained RNN model. It has been refactored to separate concerns into
distinct operation modules.
"""

import logging
import os
from typing import List, Optional
import numpy as np

from handwriting_synthesis import drawing
from handwriting_synthesis.config import prediction_path, checkpoint_path
from handwriting_synthesis.hand._draw import _draw
from handwriting_synthesis.rnn import RNN
from handwriting_synthesis.hand.operations import (
    get_stroke_width,
    stitch_strokes,
    split_text_into_chunks,
    sample_strokes,
)


class Hand(object):
    """Main class for handwriting synthesis using RNN."""

    def __init__(self):
        """Initialize the Hand with a trained RNN model."""
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
        """
        Generate handwriting for lines of text.

        Args:
            filename: Output SVG file path
            lines: List of text lines to write
            biases: Optional list of bias values (randomness)
            styles: Optional list of style IDs
            stroke_colors: Optional list of stroke colors
            stroke_widths: Optional list of stroke widths
            page_size: Paper size ('A4', 'Letter', etc.)
            units: Unit system ('mm' or 'px')
            margins: Margin size(s)
            line_height: Height between lines
            align: Text alignment ('left', 'center', 'right')
            background: Background color
            global_scale: Global scaling factor
            orientation: Page orientation ('portrait' or 'landscape')
            legibility: Legibility mode ('normal', 'high', etc.)
            x_stretch: Horizontal stretch factor
            denoise: Whether to apply denoising
        """
        def _normalize_seq(value, desired_len, cast_fn=None, name='param'):
            """Normalize a parameter to match the number of lines."""
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
        """
        Sample stroke sequences from the RNN.

        Args:
            lines: List of text lines
            biases: Optional biases
            styles: Optional styles

        Returns:
            List of stroke sequences
        """
        return sample_strokes(self.nn.session, self.nn, lines, biases, styles)

    def write_chunked(
        self,
        filename,
        text,
        max_line_width=800.0,
        words_per_chunk=3,
        chunk_spacing=8.0,
        rotate_chunks=True,
        min_words_per_chunk=2,
        max_words_per_chunk=8,
        target_chars_per_chunk=25,
        adaptive_chunking=True,
        adaptive_strategy='balanced',
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
        2. Generates text in small chunks (adaptively sized based on strategy)
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
            words_per_chunk: Target number of words per chunk (adjusted by strategy)
            chunk_spacing: Horizontal spacing between chunks
            rotate_chunks: Enable rotation correction to prevent cumulative slant
            min_words_per_chunk: Minimum words per chunk
            max_words_per_chunk: Maximum words per chunk
            target_chars_per_chunk: Target character count per chunk
            adaptive_chunking: Enable adaptive chunking (default: True)
            adaptive_strategy: Strategy for adaptive chunking ('balanced', 'word_length',
                             'sentence', 'punctuation', 'off')
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

            # Split line into chunks with adaptive sizing
            chunks = split_text_into_chunks(
                input_line,
                words_per_chunk=words_per_chunk,
                target_chars_per_chunk=target_chars_per_chunk,
                min_words=min_words_per_chunk,
                max_words=max_words_per_chunk,
                adaptive_chunking=adaptive_chunking,
                adaptive_strategy=adaptive_strategy
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
            current_line_stroke = np.empty((0, 3))
            current_line_text = []
            current_line_width = 0.0

            for chunk_text, chunk_stroke in zip(chunks, chunk_strokes):
                chunk_width = get_stroke_width(chunk_stroke)

                # Check if chunk fits on current line
                potential_width = current_line_width
                if current_line_width > 0:
                    potential_width += chunk_spacing + chunk_width
                else:
                    potential_width = chunk_width

                if potential_width <= max_line_width or current_line_width == 0:
                    # Chunk fits on current line
                    if current_line_width > 0:
                        current_line_stroke = stitch_strokes(
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
