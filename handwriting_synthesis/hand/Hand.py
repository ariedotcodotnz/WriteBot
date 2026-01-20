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

        # If we have overrides, use SPACE-PLACEHOLDER approach
        # KEY FIX: Chunk the ORIGINAL text first, THEN replace override chars in each chunk.
        # This preserves the position mapping between chunks and the original text.
        if overrides_dict:
            from handwriting_synthesis.hand.character_override_utils import estimate_override_width, get_random_override

            print(f"DEBUG write_chunked: Using SPACE-PLACEHOLDER approach for overrides")

            # Track segments for each line (will be used later for line_segments)
            all_line_segment_data = []

            for input_line in input_lines:
                # Handle blank lines
                if not input_line.strip():
                    all_lines.append(np.empty((0, 3)))
                    all_line_texts.append('')
                    all_line_segment_data.append([])
                    continue

                # STEP 1: Chunk the ORIGINAL text first (before any modification)
                # This preserves word boundaries and spacing correctly
                original_chunks = split_text_into_chunks(
                    input_line,
                    words_per_chunk=words_per_chunk,
                    target_chars_per_chunk=target_chars_per_chunk,
                    min_words=min_words_per_chunk,
                    max_words=max_words_per_chunk,
                    adaptive_chunking=adaptive_chunking,
                    adaptive_strategy=adaptive_strategy
                )

                if not original_chunks:
                    all_lines.append(np.empty((0, 3)))
                    all_line_texts.append('')
                    all_line_segment_data.append([])
                    continue

                print(f"DEBUG: Original line: '{input_line}'")
                print(f"DEBUG: Original chunks: {original_chunks}")

                # STEP 2: For each chunk, identify overrides and create modified version
                modified_chunks = []  # Chunks with override chars replaced by spaces
                chunk_override_info = []  # Override positions for each chunk

                for chunk_idx, original_chunk in enumerate(original_chunks):
                    chunk_overrides = []  # [(local_idx, char), ...]
                    modified_chars = []

                    for char_idx, char in enumerate(original_chunk):
                        if char in overrides_dict:
                            chunk_overrides.append((char_idx, char))
                            modified_chars.append(' ')  # Space placeholder
                            print(f"DEBUG: Chunk {chunk_idx}: Replacing '{char}' at local position {char_idx} with SPACE")
                        else:
                            modified_chars.append(char)

                    modified_chunk = ''.join(modified_chars)
                    modified_chunks.append(modified_chunk)
                    chunk_override_info.append(chunk_overrides)

                    print(f"DEBUG: Chunk {chunk_idx}: original='{original_chunk}' modified='{modified_chunk}' overrides={chunk_overrides}")

                # STEP 3: Validate modified chunks (should only contain valid alphabet chars)
                valid_char_set = set(drawing.alphabet)
                for chunk_num, chunk in enumerate(modified_chunks):
                    for char in chunk:
                        if char not in valid_char_set:
                            raise ValueError(
                                f"Invalid character {char} detected in chunk {chunk_num}. "
                                f"Valid character set is {valid_char_set}"
                            )

                # STEP 4: Calculate style offset (char_indices are offset when styles are used)
                # When styles are used, text is prepended: "style_chars" + " " + actual_text
                # So char_indices for actual text start at len(style_chars) + 1
                style_char_offset = 0
                if styles is not None:
                    try:
                        from handwriting_synthesis.config import style_path
                        style_id = styles if not isinstance(styles, list) else styles[0]
                        style_chars = np.load(f"{style_path}/style-{style_id}-chars.npy").tostring().decode('utf-8')
                        style_char_offset = len(style_chars) + 1  # +1 for the space separator
                        print(f"DEBUG: Style priming active, char_indices offset = {style_char_offset}")
                    except Exception as e:
                        print(f"DEBUG: Could not determine style offset: {e}")
                        style_char_offset = 0

                # STEP 5: Generate strokes for modified chunks WITH char_indices
                chunk_strokes, chunk_char_indices = self._sample(
                    modified_chunks,
                    biases=[biases] * len(modified_chunks) if biases is not None else None,
                    styles=[styles] * len(modified_chunks) if styles is not None else None,
                    return_char_indices=True  # Get char indices from attention
                )

                print(f"DEBUG: Generated {len(modified_chunks)} chunks with char_indices")

                # STEP 6: Build segment data with override info for each chunk
                # Stitch chunks into lines based on actual widths
                current_line_stroke = np.empty((0, 3))
                current_line_text = []
                current_line_width = 0.0
                current_line_segment_list = []

                for chunk_idx, (original_chunk, modified_chunk, chunk_stroke, char_indices, chunk_overrides) in enumerate(
                    zip(original_chunks, modified_chunks, chunk_strokes, chunk_char_indices, chunk_override_info)
                ):
                    has_overrides = len(chunk_overrides) > 0

                    # Adjust override positions for style offset
                    # char_indices from the model include the style prime, so we need to add the offset
                    adjusted_overrides = [(local_idx + style_char_offset, char) for local_idx, char in chunk_overrides]

                    print(f"DEBUG: Processing chunk {chunk_idx} '{modified_chunk}': has_overrides={has_overrides}")
                    print(f"DEBUG:   Original positions: {chunk_overrides}")
                    print(f"DEBUG:   Adjusted positions (with style offset {style_char_offset}): {adjusted_overrides}")
                    if has_overrides:
                        print(f"DEBUG:   char_indices range: [{char_indices.min()}, {char_indices.max()}], unique values: {np.unique(char_indices)[:20]}...")

                    # Calculate chunk width (including estimated override widths)
                    chunk_width = get_stroke_width(chunk_stroke)

                    # For width calculation, estimate how much extra space overrides need
                    extra_override_width = 0.0
                    for local_idx, override_char in chunk_overrides:
                        override_data = get_random_override(overrides_dict, override_char)
                        if override_data:
                            override_w = estimate_override_width(override_data, target_height=60, x_stretch=1.0)
                            extra_override_width += override_w + (override_w * 0.3)

                    effective_chunk_width = chunk_width + extra_override_width

                    # Check if chunk fits on current line
                    potential_width = current_line_width
                    if current_line_width > 0:
                        potential_width += chunk_spacing + effective_chunk_width
                    else:
                        potential_width = effective_chunk_width

                    # Build segment data
                    # NOTE: 'text' is the MODIFIED chunk (what was generated)
                    # override_positions are ADJUSTED for style offset (to match char_indices)
                    segment = {
                        'type': 'generated',
                        'text': modified_chunk,  # Text that was generated (with spaces)
                        'original_text': original_chunk,  # Original text (with override chars)
                        'strokes': chunk_stroke,
                        'char_indices': char_indices,  # Attention-based character indices
                        'override_positions': adjusted_overrides,  # [(adjusted_idx, char), ...] - ADJUSTED for style offset
                    }

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
                        current_line_text.append(original_chunk)
                        current_line_segment_list.append(segment)
                        current_line_width = potential_width
                    else:
                        # Start new line (width exceeded)
                        if len(current_line_stroke) > 0 or len(current_line_text) > 0:
                            all_lines.append(current_line_stroke)
                            all_line_texts.append(''.join(current_line_text))
                            all_line_segment_data.append(current_line_segment_list)

                        current_line_stroke = chunk_stroke
                        current_line_text = [original_chunk]
                        current_line_segment_list = [segment]
                        current_line_width = effective_chunk_width

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