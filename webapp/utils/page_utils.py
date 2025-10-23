"""Page size and margin calculation utilities."""

from typing import List, Dict, Tuple, Union, Optional


# Unit conversion and paper sizes
PX_PER_MM = 96.0 / 25.4

# Hardcoded fallback paper sizes (used when database is unavailable)
PAPER_SIZES_MM = {
    'A5': (148.0, 210.0),
    'A4': (210.0, 297.0),
    'Letter': (215.9, 279.4),
    'Legal': (215.9, 355.6),
}


def get_page_sizes_from_db():
    """
    Get page sizes from database.

    Returns:
        Dict mapping page size names to (width, height) tuples in millimeters,
        or None if database is unavailable.
    """
    try:
        from webapp.models import PageSizePreset
        from flask import has_app_context

        if not has_app_context():
            return None

        presets = PageSizePreset.query.filter_by(is_active=True).all()
        return {preset.name: (preset.width, preset.height) for preset in presets}
    except Exception:
        return None


def get_available_paper_sizes():
    """
    Get all available paper sizes, prioritizing database presets.

    Returns:
        Dict mapping page size names to (width, height) tuples in millimeters.
    """
    db_sizes = get_page_sizes_from_db()
    if db_sizes:
        return db_sizes
    return PAPER_SIZES_MM.copy()


def to_px(v: float, units: str) -> float:
    """
    Convert a value to pixels based on units.

    Args:
        v: Value to convert
        units: Unit type ('mm' or 'px')

    Returns:
        Value in pixels
    """
    try:
        f = float(v)
    except Exception:
        return 0.0
    return f * PX_PER_MM if units == 'mm' else f


def margins_to_px(
    margins: Union[float, int, List[float], Dict[str, float]],
    units: str
) -> Tuple[float, float, float, float]:
    """
    Convert margins to pixels.

    Args:
        margins: Margin specification (single value, list, or dict)
        units: Unit type ('mm' or 'px')

    Returns:
        Tuple of (top, right, bottom, left) in pixels
    """
    def to_tuple(m) -> Tuple[float, float, float, float]:
        if isinstance(m, (int, float)):
            t = r = b = l = float(m)
        elif isinstance(m, (list, tuple)) and len(m) == 4:
            t, r, b, l = [float(x) for x in m]
        elif isinstance(m, dict):
            t = float(m.get('top', 0))
            r = float(m.get('right', 0))
            b = float(m.get('bottom', 0))
            l = float(m.get('left', 0))
        else:
            t = r = b = l = 0.0
        return t, r, b, l

    t, r, b, l = to_tuple(margins)
    return to_px(t, units), to_px(r, units), to_px(b, units), to_px(l, units)


def resolve_page_px(
    page_size: Union[str, List[float], Tuple[float, float]],
    units: str,
    page_width: Optional[float],
    page_height: Optional[float],
    orientation: str
) -> Tuple[float, float]:
    """
    Resolve page dimensions in pixels.

    Args:
        page_size: Standard paper size name or custom dimensions
        units: Unit type ('mm' or 'px')
        page_width: Optional explicit width
        page_height: Optional explicit height
        orientation: 'portrait' or 'landscape'

    Returns:
        Tuple of (width_px, height_px)
    """
    # Explicit dimensions take precedence
    if page_width and page_height:
        w_px, h_px = to_px(page_width, units), to_px(page_height, units)
    elif isinstance(page_size, str):
        # Try database first, then fall back to hardcoded sizes
        paper_sizes = get_available_paper_sizes()
        if page_size in paper_sizes:
            w_mm, h_mm = paper_sizes[page_size]
            w_px, h_px = to_px(w_mm, 'mm'), to_px(h_mm, 'mm')
        else:
            # Default to A4 if size not found
            w_px, h_px = to_px(210, 'mm'), to_px(297, 'mm')
    elif isinstance(page_size, (list, tuple)) and len(page_size) == 2:
        w_px, h_px = to_px(page_size[0], units), to_px(page_size[1], units)
    else:
        # Default to A4
        w_px, h_px = to_px(210, 'mm'), to_px(297, 'mm')

    # Apply orientation
    if orientation == 'landscape':
        w_px, h_px = h_px, w_px

    return w_px, h_px


def line_height_px(units: str, line_height_value: Optional[Union[float, int]]) -> float:
    """
    Convert line height to pixels.

    Args:
        units: Unit type ('mm' or 'px')
        line_height_value: Line height value

    Returns:
        Line height in pixels
    """
    if line_height_value is None or str(line_height_value).strip() == "":
        return 60.0
    try:
        return to_px(float(line_height_value), units)
    except Exception:
        return 60.0
