"""Stroke manipulation operations (rotation, stitching, baseline calculations)."""

from typing import Optional
import numpy as np

from handwriting_synthesis import drawing


def get_stroke_width(stroke: np.ndarray) -> float:
    """
    Calculate the horizontal width of a stroke sequence.

    Args:
        stroke: Stroke sequence (offsets).

    Returns:
        Horizontal width in coordinate units.
    """
    if len(stroke) == 0:
        return 0.0
    coords = drawing.offsets_to_coords(stroke)
    return float(np.max(coords[:, 0]) - np.min(coords[:, 0]))


def calculate_baseline_angle(stroke: np.ndarray, use_last_portion: float = 1.0) -> float:
    """
    Calculate the baseline angle by comparing bottom Y coordinates at front and back ends.

    This simpler approach directly measures the slant by:
    1. Finding the lowest Y point at the start.
    2. Finding the lowest Y point at the end.
    3. Calculating angle = arctan((y_end - y_start) / (x_end - x_start)).

    Args:
        stroke: Input stroke sequence (offsets).
        use_last_portion: Fraction of stroke to use (1.0 = all, 0.5 = last 50%).

    Returns:
        Baseline angle in radians.
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


def rotate_stroke(
    stroke: np.ndarray,
    angle: float,
    pivot_point: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Rotate a stroke by a given angle around a pivot point.

    Args:
        stroke: Input stroke sequence (offsets).
        angle: Rotation angle in radians (positive = counter-clockwise).
        pivot_point: Point to rotate around (default: center of stroke).

    Returns:
        Rotated stroke sequence (offsets).
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


def get_baseline_y(coords: np.ndarray, use_region: str = 'all') -> float:
    """
    Calculate a consistent baseline Y position for a set of stroke coordinates.

    Uses a robust method that focuses on the main body of text, excluding
    extreme points (descenders and ascenders).

    Args:
        coords: Stroke coordinates.
        use_region: Which region to analyze - 'all', 'start', or 'end'.

    Returns:
        Y position of the baseline.
    """
    if len(coords) == 0:
        return 0.0

    # Select region of interest
    if use_region == 'start':
        region_size = max(10, len(coords) // 4)
        region_coords = coords[:region_size]
    elif use_region == 'end':
        region_size = max(10, len(coords) // 4)
        region_coords = coords[-region_size:]
    else:
        region_coords = coords

    y_values = region_coords[:, 1]

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


def smooth_chunk_boundary(
    stroke: np.ndarray,
    boundary_idx: int,
    window_size: int = 5,
    smooth_x: bool = False
) -> np.ndarray:
    """
    Smooth the transition at a chunk boundary to reduce visible seams.

    Uses a blend of Gaussian smoothing and linear interpolation to create
    a natural-looking transition that preserves the character of both chunks.

    Args:
        stroke: Combined stroke sequence (offsets).
        boundary_idx: Index where the boundary occurs.
        window_size: Number of points to smooth on each side.
        smooth_x: If True, also smooth X coordinates (usually False to preserve spacing).

    Returns:
        Smoothed stroke sequence.
    """
    if len(stroke) == 0 or boundary_idx < window_size or boundary_idx >= len(stroke) - window_size:
        return stroke

    coords = drawing.offsets_to_coords(stroke)

    # Extract the boundary region with some extra context
    start_idx = boundary_idx - window_size
    end_idx = boundary_idx + window_size + 1

    # Create smooth blending weights using smoothstep function
    # This provides C1 continuity at the boundaries
    region_len = end_idx - start_idx
    t = np.linspace(0, 1, region_len)
    # Smoothstep: 3t^2 - 2t^3 (has zero derivative at t=0 and t=1)
    blend_weights = 3 * t**2 - 2 * t**3

    # Get anchor points from just outside the blend region
    pre_boundary_y = coords[max(0, start_idx - 3):start_idx, 1]
    post_boundary_y = coords[end_idx:min(len(coords), end_idx + 3), 1]

    if len(pre_boundary_y) > 0 and len(post_boundary_y) > 0:
        # Use the trend from anchor points to guide the blend
        y_start = np.mean(pre_boundary_y)
        y_end = np.mean(post_boundary_y)

        # Linear guide through the boundary
        linear_guide = y_start + blend_weights * (y_end - y_start)

        # Original Y values in boundary region
        original_y = coords[start_idx:end_idx, 1].copy()

        # Blend: smoothly transition from original to guide near boundary center
        # Use a Gaussian-weighted blend that's strongest at the exact boundary
        center_idx = window_size  # Index of boundary within region
        center_weight = np.exp(-((np.arange(region_len) - center_idx) ** 2) / (window_size ** 2))
        center_weight = center_weight * 0.4  # Max 40% blend toward guide

        # Apply blend
        coords[start_idx:end_idx, 1] = (1 - center_weight) * original_y + center_weight * linear_guide

    # Also apply gentle Gaussian smoothing for micro-scale roughness
    sigma = window_size / 2.5
    x = np.arange(-window_size, window_size + 1)
    kernel = np.exp(-x ** 2 / (2 * sigma ** 2))
    kernel = kernel / kernel.sum()

    # Expand region for convolution
    conv_start = max(0, start_idx - window_size)
    conv_end = min(len(coords), end_idx + window_size)

    if conv_end - conv_start >= len(kernel):
        smoothed_y = np.convolve(coords[conv_start:conv_end, 1], kernel, mode='same')
        # Apply only to the boundary region with tapering
        taper = np.exp(-((np.arange(region_len) - window_size) ** 2) / (window_size ** 2))
        blend_start = start_idx - conv_start
        blend_end = blend_start + region_len
        if blend_end <= len(smoothed_y):
            smoothed_region = smoothed_y[blend_start:blend_end]
            original_region = coords[start_idx:end_idx, 1]
            coords[start_idx:end_idx, 1] = (1 - taper * 0.3) * original_region + taper * 0.3 * smoothed_region

    return drawing.coords_to_offsets(coords)


def calculate_adaptive_spacing(
    stroke1: np.ndarray,
    stroke2: np.ndarray,
    base_spacing: float = 8.0
) -> float:
    """
    Calculate adaptive spacing between chunks based on their characteristics.

    Considers:
    - Stroke density at the boundary (dense strokes need more spacing)
    - Vertical extent of ending/starting strokes (tall letters need more room)
    - Whether strokes end/start with ascenders or descenders

    Args:
        stroke1: First stroke sequence.
        stroke2: Second stroke sequence.
        base_spacing: Base spacing value.

    Returns:
        Adjusted spacing value.
    """
    if len(stroke1) == 0 or len(stroke2) == 0:
        return base_spacing

    # Get the characteristics of the ending and starting strokes
    coords1 = drawing.offsets_to_coords(stroke1)
    coords2 = drawing.offsets_to_coords(stroke2)

    # Look at the last few points of stroke1 and first few of stroke2
    num_end_points = min(15, len(coords1))
    num_start_points = min(15, len(coords2))
    end_points = coords1[-num_end_points:]
    start_points = coords2[:num_start_points]

    # Calculate the density (how spread out the strokes are)
    end_x_range = np.max(end_points[:, 0]) - np.min(end_points[:, 0])
    start_x_range = np.max(start_points[:, 0]) - np.min(start_points[:, 0])

    # Calculate vertical extent at boundaries
    end_y_range = np.max(end_points[:, 1]) - np.min(end_points[:, 1])
    start_y_range = np.max(start_points[:, 1]) - np.min(start_points[:, 1])

    spacing_multiplier = 1.0

    # Adjust based on horizontal density
    avg_density = (end_x_range + start_x_range) / 2.0
    if avg_density < 5.0:
        # Dense strokes (like 'i', 'l') - use more spacing
        spacing_multiplier *= 1.15
    elif avg_density > 20.0:
        # Sparse strokes (like 'w', 'm') - use less spacing
        spacing_multiplier *= 0.9

    # Adjust based on vertical extent (tall letters at boundary)
    avg_y_extent = (end_y_range + start_y_range) / 2.0
    if avg_y_extent > 40.0:
        # Tall strokes (ascenders/descenders) - slightly more spacing
        spacing_multiplier *= 1.08
    elif avg_y_extent < 15.0:
        # Short strokes (like 'a', 'e', 'o') - can be tighter
        spacing_multiplier *= 0.95

    # Check if ending stroke trails off (ends lower than average)
    # This suggests the end of a word or natural pause point
    end_final_y = end_points[-1, 1]
    end_avg_y = np.mean(end_points[:, 1])
    if end_final_y > end_avg_y + 5.0:
        # Stroke ends with a descending trail - add slight spacing
        spacing_multiplier *= 1.05

    return base_spacing * spacing_multiplier


def stitch_strokes(
    stroke1: np.ndarray,
    stroke2: np.ndarray,
    spacing: float = 0.0,
    rotate_to_match: bool = True,
    smooth_boundary: bool = True,
    adaptive_spacing: bool = True,
    local_baseline_align: bool = True
) -> np.ndarray:
    """
    Stitch two stroke sequences together with comprehensive improvements.

    This method includes:
    1. Baseline angle correction (horizontal alignment).
    2. Adaptive spacing (context-aware gaps).
    3. Local baseline alignment (match Y at boundary for seamless join).
    4. Boundary smoothing (seamless transitions).

    Args:
        stroke1: First stroke sequence (offsets).
        stroke2: Second stroke sequence (offsets).
        spacing: Base horizontal spacing between strokes.
        rotate_to_match: If True, apply rotation correction.
        smooth_boundary: If True, smooth the transition at chunk boundary.
        adaptive_spacing: If True, use context-aware spacing.
        local_baseline_align: If True, fine-tune Y alignment at the boundary.

    Returns:
        Combined stroke sequence with all improvements applied.
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
        # Pre-correction of stroke2 to horizontal
        angle2 = calculate_baseline_angle(stroke2, use_last_portion=1.0)

        if abs(angle2) > 0.003:  # ~0.17 degrees threshold
            y_values2 = coords2[:, 1]
            baseline2_y = np.percentile(y_values2, 70)
            x_mid = (np.max(coords2[:, 0]) + np.min(coords2[:, 0])) / 2
            pivot = np.array([x_mid, baseline2_y])

            stroke2 = rotate_stroke(stroke2, -angle2, pivot)
            coords2 = drawing.offsets_to_coords(stroke2)

    # IMPROVEMENT 2: Adaptive spacing
    actual_spacing = spacing
    if adaptive_spacing:
        actual_spacing = calculate_adaptive_spacing(stroke1, stroke2, spacing)

    # Calculate horizontal offset
    max_x1 = np.max(coords1[:, 0])
    min_x2 = np.min(coords2[:, 0])
    x_offset = max_x1 - min_x2 + actual_spacing

    # IMPROVEMENT 3: Baseline alignment with local refinement
    # First, do global baseline alignment
    baseline1_global = get_baseline_y(coords1)
    baseline2_global = get_baseline_y(coords2)
    y_offset = baseline1_global - baseline2_global

    # Then refine with local alignment at the boundary
    if local_baseline_align:
        # Get baseline at the end of stroke1 and start of stroke2
        baseline1_end = get_baseline_y(coords1, use_region='end')
        baseline2_start = get_baseline_y(coords2, use_region='start')

        # Weighted blend: 70% local, 30% global for smoother result
        local_y_offset = baseline1_end - baseline2_start
        y_offset = 0.7 * local_y_offset + 0.3 * y_offset

    # Apply offsets to stroke2
    coords2[:, 0] += x_offset
    coords2[:, 1] += y_offset

    # IMPROVEMENT 4: Fine Y adjustment at boundary to minimize discontinuity
    if local_baseline_align and len(coords1) >= 5 and len(coords2) >= 5:
        # Get the Y trend at end of stroke1 and start of stroke2
        end_region = coords1[-5:]
        start_region = coords2[:5]

        # Calculate the Y discontinuity at the exact boundary
        end_y_trend = np.mean(end_region[-3:, 1])  # Last 3 points
        start_y_trend = np.mean(start_region[:3, 1])  # First 3 points

        y_discontinuity = start_y_trend - end_y_trend

        # If there's a noticeable jump, apply a gradual correction to stroke2
        if abs(y_discontinuity) > 1.0:
            # Create a tapered correction that fades out over the first portion of stroke2
            taper_len = min(len(coords2), max(20, len(coords2) // 4))
            taper = np.exp(-np.arange(taper_len) / (taper_len / 3.0))

            # Apply tapered correction
            correction = -y_discontinuity * 0.5  # Correct 50% of discontinuity
            coords2[:taper_len, 1] += correction * taper

    # Combine coordinates
    combined_coords = np.vstack([coords1, coords2])
    combined_offsets = drawing.coords_to_offsets(combined_coords)

    # IMPROVEMENT 5: Boundary smoothing
    if smooth_boundary:
        combined_offsets = smooth_chunk_boundary(
            combined_offsets,
            boundary_idx,
            window_size=4  # Slightly larger window for smoother blends
        )

    # IMPROVEMENT 6: Final angle correction with gentler approach
    if rotate_to_match:
        final_angle = calculate_baseline_angle(combined_offsets, use_last_portion=0.5)

        # Only correct significant drift, and do it gently
        if abs(final_angle) > 0.005:  # Slightly higher threshold
            combined_coords = drawing.offsets_to_coords(combined_offsets)

            end_portion_start = int(len(combined_coords) * 0.5)
            end_coords = combined_coords[end_portion_start:]
            baseline_end_y = get_baseline_y(end_coords)

            pivot_x = max_x1
            pivot = np.array([pivot_x, baseline_end_y])

            # Apply partial correction (80%) to avoid over-correction
            combined_offsets = rotate_stroke(combined_offsets, -final_angle * 0.8, pivot)

    return combined_offsets
