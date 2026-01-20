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
        empty_line_spacing=None,
        auto_size=True,
        manual_size_scale=1.0,
        character_override_collection_id=None,
        margin_jitter_frac=None,
        margin_jitter_coherence=None,
    ):
        """
        Generate handwriting for lines of text.

        This method generates handwriting for a given list of lines and saves it as an SVG file.
        It supports various customization options including styles, biases, colors, and layout.

        Args:
            filename: Output SVG file path.
            lines: List of text lines to write.
            biases: Optional list of bias values (randomness).
                    Lower values increase randomness, higher values increase legibility.
                    Can be a single value or a list corresponding to each line.
            styles: Optional list of style IDs. Can be a single value or a list.
            stroke_colors: Optional list of stroke colors (e.g., "black", "blue", "#FF0000").
                           Can be a single value or a list.
            stroke_widths: Optional list of stroke widths in pixels.
                           Can be a single value or a list.
            page_size: Paper size ('A4', 'Letter', etc.) or custom dimensions.
            units: Unit system ('mm' or 'px') for dimensions and margins.
            margins: Margin size(s). Can be a single value (all sides),
                     a list [top, right, bottom, left], or a dict.
            line_height: Height between lines. If None, calculated automatically.
            align: Text alignment ('left', 'center', 'right').
            background: Background color (e.g., "white", "transparent").
            global_scale: Global scaling factor for the entire output.
            orientation: Page orientation ('portrait' or 'landscape').
            legibility: Legibility mode ('normal', 'high', 'natural').
            x_stretch: Horizontal stretch factor to widen/narrow text.
            denoise: Whether to apply denoising/smoothing to strokes.
            empty_line_spacing: Specific spacing for empty lines.
            auto_size: Whether to automatically scale text to fit page width.
            manual_size_scale: Manual scaling factor if auto_size is False.
            character_override_collection_id: ID of a character override collection to use.

        Returns:
            None
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

        # CRITICAL FIX: Load character overrides FIRST (before validation)
        overrides_dict = {}
        if character_override_collection_id is not None:
            try:
                from handwriting_synthesis.hand.character_override_utils import get_character_overrides
                overrides_dict = get_character_overrides(character_override_collection_id)
                print(f"DEBUG: Loaded overrides for characters: {list(overrides_dict.keys())}")
            except Exception as e:
                print(f"Warning: Could not load character overrides: {e}")

        # CRITICAL FIX: Expand valid character set with overrides BEFORE validation
        valid_char_set = set(drawing.alphabet)
        if overrides_dict:
            valid_char_set = valid_char_set.union(overrides_dict.keys())
            print(f"DEBUG: Expanded character set with override characters: {sorted(overrides_dict.keys())}")
            print(f"DEBUG: Total valid characters: {len(valid_char_set)}")

        # Now validate using the expanded character set
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
                        ).format(repr(char), line_num, sorted(valid_char_set))
                    )

        # Normalize optional sequences to match number of lines
        num_lines = len(lines)
        biases = _normalize_seq(biases, num_lines, float, 'biases')
        styles = _normalize_seq(styles, num_lines, int, 'styles')
        stroke_colors = _normalize_seq(stroke_colors, num_lines, str, 'stroke_colors')
        stroke_widths = _normalize_seq(stroke_widths, num_lines, float, 'stroke_widths')

        # Handle character overrides using SPACE PLACEHOLDER approach
        # Key insight: Generate full lines with SPACES where overrides go.
        # The space creates a natural gap in the stroke sequence (pen lift).
        # We then insert the override SVG into that gap - no stroke clipping needed!
        # This preserves full RNN context for the surrounding text.
        if overrides_dict:
            print(f"DEBUG: Processing text with SPACE-PLACEHOLDER override approach")

            # Use SPACE as placeholder - creates natural gap in strokes
            placeholder_char = ' '

            # Track override positions: {line_idx: [(char_idx, original_char), ...]}
            override_positions = {}
            modified_lines = []

            for line_idx, line in enumerate(lines):
                override_positions[line_idx] = []
                modified_line_chars = []

                for char_idx, char in enumerate(line):
                    if char in overrides_dict:
                        # Track the position and original character
                        override_positions[line_idx].append((char_idx, char))
                        # Replace with SPACE - creates natural gap for override insertion
                        modified_line_chars.append(placeholder_char)
                        print(f"DEBUG: Line {line_idx}, char {char_idx}: replacing '{char}' with SPACE placeholder")
                    else:
                        modified_line_chars.append(char)

                modified_lines.append(''.join(modified_line_chars))

            print(f"DEBUG: Original lines: {lines}")
            print(f"DEBUG: Modified lines (with placeholders): {modified_lines}")
            print(f"DEBUG: Override positions: {override_positions}")

            # Generate strokes for FULL lines with CHAR INDICES from attention
            # This gives us precise knowledge of where each character was written!
            generated_strokes, char_indices_list = self._sample(
                modified_lines, biases=biases, styles=styles, return_char_indices=True
            )

            print(f"DEBUG: Got char_indices for {len(char_indices_list)} lines")
            for i, ci in enumerate(char_indices_list):
                print(f"DEBUG:   Line {i}: {len(ci)} char indices, range [{ci.min() if len(ci) > 0 else 'N/A'}, {ci.max() if len(ci) > 0 else 'N/A'}]")

            # Convert to line_segments format (single segment per line, like non-override)
            line_segments = []
            for line_idx, (original_line, strokes, char_indices) in enumerate(
                zip(lines, generated_strokes, char_indices_list)
            ):
                line_segments.append([{
                    'type': 'generated',
                    'text': original_line,  # Keep original text for reference
                    'modified_text': modified_lines[line_idx],  # Text that was actually generated
                    'strokes': strokes,
                    'char_indices': char_indices,  # NEW: Character index per stroke from attention
                    'line_idx': line_idx,
                    'override_positions': override_positions[line_idx]  # [(char_idx, char), ...]
                }])
        else:
            # No overrides, use normal generation
            print(f"DEBUG: No overrides, using normal generation")
            generated_strokes = self._sample(lines, biases=biases, styles=styles)
            line_segments = []
            for line_idx, (line, strokes) in enumerate(zip(lines, generated_strokes)):
                line_segments.append([{
                    'type': 'generated',
                    'text': line,
                    'strokes': strokes,
                    'line_idx': line_idx
                }])

        print(f"DEBUG: Final line_segments structure: {len(line_segments)} lines")
        for i, segments in enumerate(line_segments):
            print(f"DEBUG:   Line {i}: {len(segments)} segments")
            for j, seg in enumerate(segments):
                print(f"DEBUG:     Segment {j}: type={seg['type']}, text='{seg.get('text', '')}'")

        _draw(
            line_segments,
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
            empty_line_spacing=empty_line_spacing,
            auto_size=auto_size,
            manual_size_scale=manual_size_scale,
            character_override_collection_id=character_override_collection_id,
            overrides_dict=overrides_dict,
            margin_jitter_frac=margin_jitter_frac,
            margin_jitter_coherence=margin_jitter_coherence,
        )

    def _sample(self, lines, biases=None, styles=None, return_char_indices=False):
        """
        Sample stroke sequences from the RNN.

        Args:
            lines: List of text lines
            biases: Optional biases
            styles: Optional styles
            return_char_indices: If True, also return character indices per stroke
                                (from the attention mechanism)

        Returns:
            If return_char_indices is False:
                List of stroke sequences
            If return_char_indices is True:
                Tuple of (strokes_list, char_indices_list)
        """
        return sample_strokes(
            self.nn.session, self.nn, lines, biases, styles,
            return_char_indices=return_char_indices
        )

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
        empty_line_spacing=None,
        auto_size=True,
        manual_size_scale=1.0,
        character_override_collection_id=None,
        margin_jitter_frac=None,
        margin_jitter_coherence=None,
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
        # CRITICAL FIX: Load character overrides FIRST (before validation)
        overrides_dict = {}
        if character_override_collection_id is not None:
            try:
                from handwriting_synthesis.hand.character_override_utils import get_character_overrides
                overrides_dict = get_character_overrides(character_override_collection_id)
                print(f"DEBUG: Loaded overrides for characters: {list(overrides_dict.keys())}")
            except Exception as e:
                print(f"Warning: Could not load character overrides: {e}")

        # Split text by newlines first to preserve line structure
        input_lines = text.split('\n')

        # Process each input line separately
        all_lines = []
        all_line_texts = []

        # If we have overrides, we need to handle text splitting differently
        if overrides_dict:
            from handwriting_synthesis.hand.character_override_utils import split_text_with_overrides

            # Track segments for each line (will be used later for line_segments)
            all_line_segment_data = []

            for input_line in input_lines:
                # Handle blank lines
                if not input_line.strip():
                    all_lines.append(np.empty((0, 3)))
                    all_line_texts.append('')
                    all_line_segment_data.append([])
                    continue

                # Split line into override and non-override chunks
                text_chunks = split_text_with_overrides(input_line, overrides_dict)

                # Process each chunk
                line_segments_data = []
                texts_to_generate = []
                chunk_metadata = []

                for chunk_text, is_override in text_chunks:
                    if is_override:
                        # Mark as override - will be handled during drawing
                        line_segments_data.append({
                            'type': 'override',
                            'text': chunk_text,
                            'is_override': True
                        })
                    else:
                        # Non-override text - chunk it and prepare for generation
                        sub_chunks = split_text_into_chunks(
                            chunk_text,
                            words_per_chunk=words_per_chunk,
                            target_chars_per_chunk=target_chars_per_chunk,
                            min_words=min_words_per_chunk,
                            max_words=max_words_per_chunk,
                            adaptive_chunking=adaptive_chunking,
                            adaptive_strategy=adaptive_strategy
                        )

                        for sub_chunk in sub_chunks:
                            gen_idx = len(texts_to_generate)
                            texts_to_generate.append(sub_chunk)
                            chunk_metadata.append({
                                'gen_idx': gen_idx,
                                'text': sub_chunk
                            })
                            line_segments_data.append({
                                'type': 'generated',
                                'text': sub_chunk,
                                'gen_idx': gen_idx,
                                'is_override': False
                            })

                # Validate characters in texts to generate
                valid_char_set = set(drawing.alphabet)
                for chunk_num, chunk in enumerate(texts_to_generate):
                    for char in chunk:
                        if char not in valid_char_set:
                            raise ValueError(
                                f"Invalid character {char} detected in chunk {chunk_num}. "
                                f"Valid character set is {valid_char_set}"
                            )

                # Generate strokes for non-override chunks only
                if texts_to_generate:
                    chunk_strokes = self._sample(
                        texts_to_generate,
                        biases=[biases] * len(texts_to_generate) if biases is not None else None,
                        styles=[styles] * len(texts_to_generate) if styles is not None else None
                    )

                    # Map generated strokes back to segments
                    for segment in line_segments_data:
                        if segment['type'] == 'generated':
                            segment['strokes'] = chunk_strokes[segment['gen_idx']]
                else:
                    chunk_strokes = []

                # Now stitch the generated chunks together, handling overrides
                current_line_stroke = np.empty((0, 3))
                current_line_text = []
                current_line_width = 0.0
                current_line_segment_list = []

                for seg_idx, segment in enumerate(line_segments_data):
                    if segment['type'] == 'override':
                        # Estimate override width for layout
                        from handwriting_synthesis.hand.character_override_utils import get_random_override, estimate_override_width
                        override_data = get_random_override(overrides_dict, segment['text'])
                        if override_data:
                            # Estimate width (using typical line height of 60px)
                            override_width = estimate_override_width(override_data, target_height=60, x_stretch=1.0)
                        else:
                            override_width = 20  # fallback width

                        # FIXED: Check for adjacent spaces and apply appropriate spacing
                        # This matches the logic in _draw.py for consistent line breaking
                        has_space_before = False
                        if seg_idx > 0:
                            prev_seg = line_segments_data[seg_idx - 1]
                            if prev_seg.get('type') == 'generated':
                                prev_text = prev_seg.get('text', '')
                                has_space_before = prev_text.strip() == '' or prev_text.endswith(' ')

                        has_space_after = False
                        if seg_idx < len(line_segments_data) - 1:
                            next_seg = line_segments_data[seg_idx + 1]
                            if next_seg.get('type') == 'generated':
                                next_text = next_seg.get('text', '')
                                has_space_after = next_text.strip() == '' or next_text.startswith(' ')

                        # When there's a space adjacent, use space-width spacing
                        # When there's no space, use minimal character spacing
                        space_width = override_width * 0.35
                        spacing_before = space_width if has_space_before else override_width * 0.15
                        spacing_after = space_width if has_space_after else override_width * 0.15
                        override_width_with_spacing = spacing_before + override_width + spacing_after

                        potential_width = current_line_width
                        if current_line_width > 0:
                            potential_width += override_width_with_spacing
                        else:
                            potential_width = override_width_with_spacing

                        if potential_width <= max_line_width or current_line_width == 0:
                            # Fits on current line
                            current_line_text.append(segment['text'])
                            current_line_segment_list.append(segment)
                            current_line_width = potential_width
                        else:
                            # Start new line
                            if len(current_line_stroke) > 0 or len(current_line_text) > 0:
                                all_lines.append(current_line_stroke)
                                all_line_texts.append(''.join(current_line_text))
                                all_line_segment_data.append(current_line_segment_list)

                            current_line_stroke = np.empty((0, 3))
                            current_line_text = [segment['text']]
                            current_line_segment_list = [segment]
                            current_line_width = override_width_with_spacing
                    else:
                        # Generated chunk
                        chunk_stroke = segment['strokes']
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
                            else:
                                current_line_stroke = chunk_stroke
                            current_line_text.append(segment['text'])
                            current_line_segment_list.append(segment)
                            current_line_width = potential_width
                        else:
                            # Start new line (width exceeded)
                            if len(current_line_stroke) > 0 or len(current_line_text) > 0:
                                all_lines.append(current_line_stroke)
                                all_line_texts.append(''.join(current_line_text))
                                all_line_segment_data.append(current_line_segment_list)

                            current_line_stroke = chunk_stroke
                            current_line_text = [segment['text']]
                            current_line_segment_list = [segment]
                            current_line_width = chunk_width

                # Add last line from this input line
                if len(current_line_stroke) > 0 or len(current_line_text) > 0:
                    all_lines.append(current_line_stroke)
                    all_line_texts.append(''.join(current_line_text))
                    all_line_segment_data.append(current_line_segment_list)
        else:
            # No overrides - use original logic
            all_line_segment_data = None

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

                # Expand valid character set with overrides
                valid_char_set = set(drawing.alphabet)

                # Validate characters
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

        # Convert to line_segments format with override handling
        if overrides_dict and all_line_segment_data is not None:
            # Use pre-computed segment data (overrides were handled during generation)
            line_segments = []
            for line_idx, segment_list in enumerate(all_line_segment_data):
                # Add line_idx to each segment and prepare for drawing
                line_segment_list = []
                for segment in segment_list:
                    segment_copy = segment.copy()
                    segment_copy['line_idx'] = line_idx
                    line_segment_list.append(segment_copy)
                line_segments.append(line_segment_list)
        else:
            # No overrides, simple conversion
            line_segments = []
            for line_idx, (line_strokes, line_text) in enumerate(zip(lines, line_texts)):
                line_segments.append([{
                    'type': 'generated',
                    'text': line_text,
                    'strokes': line_strokes,
                    'line_idx': line_idx
                }])

        # Draw the result
        _draw(
            line_segments,
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
            empty_line_spacing=empty_line_spacing,
            auto_size=auto_size,
            manual_size_scale=manual_size_scale,
            character_override_collection_id=character_override_collection_id,
            overrides_dict=overrides_dict,
            margin_jitter_frac=margin_jitter_frac,
            margin_jitter_coherence=margin_jitter_coherence,
        )