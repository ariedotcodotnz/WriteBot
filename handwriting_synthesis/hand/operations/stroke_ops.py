"""Stroke manipulation operations (rotation, stitching, baseline calculations)."""

from typing import Optional
import numpy as np

from handwriting_synthesis import drawing


def get_stroke_width(stroke: np.ndarray) -> float:
    """
    Calculate the horizontal width of a stroke sequence.

    Args:
        stroke: Stroke sequence (offsets)

    Returns:
        Horizontal width in coordinate units
    """
    if len(stroke) == 0:
        return 0.0
    coords = drawing.offsets_to_coords(stroke)
    return float(np.max(coords[:, 0]) - np.min(coords[:, 0]))


def calculate_baseline_angle(stroke: np.ndarray, use_last_portion: float = 1.0) -> float:
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


def rotate_stroke(
    stroke: np.ndarray,
    angle: float,
    pivot_point: Optional[np.ndarray] = None
) -> np.ndarray:
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


def get_baseline_y(coords: np.ndarray) -> float:
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


def smooth_chunk_boundary(
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


def calculate_adaptive_spacing(
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


def stitch_strokes(
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

    # Calculate horizontal and vertical offsets
    max_x1 = np.max(coords1[:, 0])
    min_x2 = np.min(coords2[:, 0])
    x_offset = max_x1 - min_x2 + actual_spacing

    # Improved baseline alignment
    baseline1 = get_baseline_y(coords1)
    baseline2 = get_baseline_y(coords2)
    y_offset = baseline1 - baseline2

    # Apply offsets to stroke2
    coords2[:, 0] += x_offset
    coords2[:, 1] += y_offset

    # Combine coordinates
    combined_coords = np.vstack([coords1, coords2])
    combined_offsets = drawing.coords_to_offsets(combined_coords)

    # IMPROVEMENT 3: Boundary smoothing
    if smooth_boundary:
        combined_offsets = smooth_chunk_boundary(
            combined_offsets,
            boundary_idx,
            window_size=3  # Small window for subtle smoothing
        )

    # Final angle correction
    if rotate_to_match:
        final_angle = calculate_baseline_angle(combined_offsets, use_last_portion=0.5)

        if abs(final_angle) > 0.003:
            combined_coords = drawing.offsets_to_coords(combined_offsets)

            end_portion_start = int(len(combined_coords) * 0.5)
            end_coords = combined_coords[end_portion_start:]
            y_values_end = end_coords[:, 1]
            baseline_end_y = np.percentile(y_values_end, 70)

            pivot_x = max_x1
            pivot = np.array([pivot_x, baseline_end_y])

            combined_offsets = rotate_stroke(combined_offsets, -final_angle, pivot)

    return combined_offsets
