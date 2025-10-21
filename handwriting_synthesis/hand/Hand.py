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

    def _calculate_baseline_angle(self, stroke: np.ndarray, use_last_portion: float = 1.0) -> float:
        """
        Calculate the baseline angle by comparing bottom Y coordinates at front and back ends.

        This simpler approach directly measures the slant by:
        1. Finding the lowest Y point at the start
        2. Finding the lowest Y point at the end
        3. Calculating angle = arctan((y_end - y_start) / (x_end - x_start))

        Args:
            stroke: Input stroke sequence (offsets)
            use_last_portion: Fraction of stroke to use (1.0 = all, 0.5 = last 50%)

        Returns:
            Baseline angle in radians
        """
        if len(stroke) == 0:
            return 0.0

        # Convert to coordinates
        coords = drawing.offsets_to_coords(stroke)

        # Use only the specified portion of the stroke
        if use_last_portion < 1.0:
            start_idx = int(len(coords) * (1.0 - use_last_portion))
            coords = coords[start_idx:]

        if len(coords) < 10:
            return 0.0

        # Define front-end and back-end regions (first 20% and last 20%)
        region_size = max(3, int(len(coords) * 0.2))

        front_coords = coords[:region_size]
        back_coords = coords[-region_size:]

        # Get the bottom (maximum Y, since Y increases downward in SVG) of each region
        # Use the average of the lowest few points for robustness
        num_bottom_points = max(2, region_size // 3)

        front_y_sorted = np.sort(front_coords[:, 1])[-num_bottom_points:]
        back_y_sorted = np.sort(back_coords[:, 1])[-num_bottom_points:]

        front_bottom_y = np.mean(front_y_sorted)
        back_bottom_y = np.mean(back_y_sorted)

        # Get X positions at front and back
        front_x = np.mean(front_coords[:, 0])
        back_x = np.mean(back_coords[:, 0])

        # Calculate the horizontal distance
        x_distance = back_x - front_x

        if abs(x_distance) < 1.0:
            return 0.0

        # Calculate Y difference (positive = slanting upward, negative = slanting downward)
        y_difference = back_bottom_y - front_bottom_y

        # Calculate angle: arctan(rise/run)
        angle = np.arctan(y_difference / x_distance)

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

    def _smooth_chunk_boundary(
            self,
            stroke: np.ndarray,
            boundary_idx: int,
            window_size: int = 5
    ) -> np.ndarray:
        """
        Smooth the transition at a chunk boundary to reduce visible seams.

        Args:
            stroke: Combined stroke sequence (offsets)
            boundary_idx: Index where the boundary occurs
            window_size: Number of points to smooth on each side

        Returns:
            Smoothed stroke sequence
        """
        if len(stroke) == 0 or boundary_idx < window_size or boundary_idx >= len(stroke) - window_size:
            return stroke

        coords = drawing.offsets_to_coords(stroke)

        # Extract the boundary region
        start_idx = boundary_idx - window_size
        end_idx = boundary_idx + window_size + 1

        # Apply Gaussian smoothing to Y coordinates in the boundary region
        # This reduces sharp transitions while preserving overall shape
        boundary_y = coords[start_idx:end_idx, 1].copy()

        # Create Gaussian kernel
        sigma = window_size / 3.0
        x = np.arange(-window_size, window_size + 1)
        kernel = np.exp(-x ** 2 / (2 * sigma ** 2))
        kernel = kernel / kernel.sum()

        # Apply smoothing
        smoothed_y = np.convolve(
            coords[max(0, start_idx - window_size):min(len(coords), end_idx + window_size), 1],
            kernel,
            mode='valid'
        )

        # Replace the boundary region with smoothed values
        if len(smoothed_y) >= len(boundary_y):
            coords[start_idx:end_idx, 1] = smoothed_y[:len(boundary_y)]

        return drawing.coords_to_offsets(coords)

    def _calculate_adaptive_spacing(
            self,
            stroke1: np.ndarray,
            stroke2: np.ndarray,
            base_spacing: float = 8.0
    ) -> float:
        """
        Calculate adaptive spacing between chunks based on their characteristics.

        Args:
            stroke1: First stroke sequence
            stroke2: Second stroke sequence
            base_spacing: Base spacing value

        Returns:
            Adjusted spacing value
        """
        if len(stroke1) == 0 or len(stroke2) == 0:
            return base_spacing

        # Get the characteristics of the ending and starting strokes
        coords1 = drawing.offsets_to_coords(stroke1)
        coords2 = drawing.offsets_to_coords(stroke2)

        # Look at the last few points of stroke1 and first few of stroke2
        end_points = coords1[-min(10, len(coords1)):]
        start_points = coords2[:min(10, len(coords2))]

        # Calculate the density (how spread out the strokes are)
        end_x_range = np.max(end_points[:, 0]) - np.min(end_points[:, 0])
        start_x_range = np.max(start_points[:, 0]) - np.min(start_points[:, 0])

        # Adjust spacing based on density
        # If chunks are dense (many points in small space), use more spacing
        # If chunks are sparse, use less spacing
        avg_density = (end_x_range + start_x_range) / 2.0

        if avg_density < 5.0:
            # Dense strokes (like 'i', 'l') - use more spacing
            return base_spacing * 1.2
        elif avg_density > 20.0:
            # Sparse strokes (like 'w', 'm') - use less spacing
            return base_spacing * 0.85

        return base_spacing

    def _stitch_strokes(
            self,
            stroke1: np.ndarray,
            stroke2: np.ndarray,
            spacing: float = 0.0,
            rotate_to_match: bool = True,
            smooth_boundary: bool = True,
            adaptive_spacing: bool = True
    ) -> np.ndarray:
        """
        Stitch two stroke sequences together with comprehensive improvements.

        This method now includes:
        1. Baseline angle correction (horizontal alignment)
        2. Adaptive spacing (context-aware gaps)
        3. Boundary smoothing (seamless transitions)

        Args:
            stroke1: First stroke sequence (offsets)
            stroke2: Second stroke sequence (offsets)
            spacing: Base horizontal spacing between strokes
            rotate_to_match: If True, apply rotation correction
            smooth_boundary: If True, smooth the transition at chunk boundary
            adaptive_spacing: If True, use context-aware spacing

        Returns:
            Combined stroke sequence with all improvements applied
        """
        if len(stroke1) == 0:
            return stroke2
        if len(stroke2) == 0:
            return stroke1

        # Store the boundary index for later smoothing
        boundary_idx = len(stroke1)

        # Convert to coordinates
        coords1 = drawing.offsets_to_coords(stroke1)
        coords2 = drawing.offsets_to_coords(stroke2)

        # IMPROVEMENT 1: Baseline angle correction
        if rotate_to_match:
            # STEP 1: Pre-correction of stroke2 to horizontal
            angle2 = self._calculate_baseline_angle(stroke2, use_last_portion=1.0)

            if abs(angle2) > 0.003:  # ~0.17 degrees threshold
                y_values2 = coords2[:, 1]
                baseline2_y = np.percentile(y_values2, 70)
                x_mid = (np.max(coords2[:, 0]) + np.min(coords2[:, 0])) / 2
                pivot = np.array([x_mid, baseline2_y])

                stroke2 = self._rotate_stroke(stroke2, -angle2, pivot)
                coords2 = drawing.offsets_to_coords(stroke2)

        # IMPROVEMENT 2: Adaptive spacing
        actual_spacing = spacing
        if adaptive_spacing:
            actual_spacing = self._calculate_adaptive_spacing(stroke1, stroke2, spacing)

        # Calculate horizontal and vertical offsets
        max_x1 = np.max(coords1[:, 0])
        min_x2 = np.min(coords2[:, 0])
        x_offset = max_x1 - min_x2 + actual_spacing

        # Improved baseline alignment
        baseline1 = self._get_baseline_y(coords1)
        baseline2 = self._get_baseline_y(coords2)
        y_offset = baseline1 - baseline2

        # Apply offsets to stroke2
        coords2[:, 0] += x_offset
        coords2[:, 1] += y_offset

        # Combine coordinates
        combined_coords = np.vstack([coords1, coords2])
        combined_offsets = drawing.coords_to_offsets(combined_coords)

        # IMPROVEMENT 3: Boundary smoothing
        if smooth_boundary:
            combined_offsets = self._smooth_chunk_boundary(
                combined_offsets,
                boundary_idx,
                window_size=3  # Small window for subtle smoothing
            )

        # Final angle correction
        if rotate_to_match:
            final_angle = self._calculate_baseline_angle(combined_offsets, use_last_portion=0.5)

            if abs(final_angle) > 0.003:
                combined_coords = drawing.offsets_to_coords(combined_offsets)

                end_portion_start = int(len(combined_coords) * 0.5)
                end_coords = combined_coords[end_portion_start:]
                y_values_end = end_coords[:, 1]
                baseline_end_y = np.percentile(y_values_end, 70)

                pivot_x = max_x1
                pivot = np.array([pivot_x, baseline_end_y])

                combined_offsets = self._rotate_stroke(combined_offsets, -final_angle, pivot)

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