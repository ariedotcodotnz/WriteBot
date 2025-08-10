import math
import numpy as np
import svgwrite

from handwriting_synthesis import drawing


PX_PER_MM = 96.0 / 25.4

PAPER_SIZES_MM = {
    'A5': (148.0, 210.0),
    'A4': (210.0, 297.0),
    'Letter': (215.9, 279.4),
    'Legal': (215.9, 355.6),
}


def _to_px(value, units):
    if units == 'mm':
        return value * PX_PER_MM
    return float(value)


def _normalize_margins(margins, units):
    if isinstance(margins, (int, float)):
        t = r = b = l = float(margins)
    elif isinstance(margins, (list, tuple)) and len(margins) == 4:
        t, r, b, l = [float(x) for x in margins]
    elif isinstance(margins, dict):
        t = float(margins.get('top', 0))
        r = float(margins.get('right', 0))
        b = float(margins.get('bottom', 0))
        l = float(margins.get('left', 0))
    else:
        t = r = b = l = 0.0
    return (_to_px(t, units), _to_px(r, units), _to_px(b, units), _to_px(l, units))


def _resolve_page_size(page_size, units, num_lines, default_line_height_px):
    if isinstance(page_size, str):
        if page_size not in PAPER_SIZES_MM:
            raise ValueError(f"Unknown page_size '{page_size}'. Known sizes: {sorted(PAPER_SIZES_MM.keys())}")
        w_mm, h_mm = PAPER_SIZES_MM[page_size]
        width_px, height_px = _to_px(w_mm, 'mm'), _to_px(h_mm, 'mm')
        svg_size = (f"{w_mm}mm", f"{h_mm}mm")
        return width_px, height_px, svg_size

    if isinstance(page_size, (list, tuple)) and len(page_size) == 2:
        w, h = float(page_size[0]), float(page_size[1])
        width_px, height_px = _to_px(w, units), _to_px(h, units)
        if units == 'mm':
            svg_size = (f"{w}mm", f"{h}mm")
        else:
            svg_size = (width_px, height_px)
        return width_px, height_px, svg_size

    # Fallback: auto height based on lines, fixed width
    width_px = 1000.0
    height_px = (num_lines + 1) * default_line_height_px
    svg_size = (width_px, height_px)
    return width_px, height_px, svg_size


def _draw(
    strokes,
    lines,
    filename,
    stroke_colors=None,
    stroke_widths=None,
    page_size='A4',
    units='mm',
    margins=20,
    line_height=None,
    align='left',
    background='white',
    global_scale=1.0,
    orientation='portrait',
):
    stroke_colors = stroke_colors or ['black'] * len(lines)
    stroke_widths = stroke_widths or [2] * len(lines)

    default_line_height_px = 60.0
    width_px, height_px, svg_size = _resolve_page_size(page_size, units, len(strokes), default_line_height_px)
    m_top, m_right, m_bottom, m_left = _normalize_margins(margins, units)

    content_width_px = max(1.0, width_px - (m_left + m_right))
    content_height_px = max(1.0, height_px - (m_top + m_bottom))

    line_height_px = _to_px(line_height, units) if line_height is not None else default_line_height_px
    # Ensure all lines fit vertically
    max_line_height_px = content_height_px / max(1, len(strokes) + 0)
    line_height_px = min(line_height_px, max_line_height_px)

    # Handle orientation
    if isinstance(svg_size, tuple) and len(svg_size) == 2 and orientation == 'landscape':
        svg_size = (svg_size[1], svg_size[0])
        width_px, height_px = height_px, width_px

    dwg = svgwrite.Drawing(filename=filename, size=svg_size)
    dwg.viewbox(0, 0, width_px, height_px)
    if background:
        dwg.add(dwg.rect(insert=(0, 0), size=(width_px, height_px), fill=background))

    # Baseline position for first line
    cursor_y = m_top + (3.0 * line_height_px / 4.0)

    for offsets, line, color, width in zip(strokes, lines, stroke_colors, stroke_widths):
        # Handle empty lines (line breaks)
        if not line:
            cursor_y += line_height_px
            continue

        # Build stroke coordinates
        offsets = offsets.copy()
        offsets[:, :2] *= float(global_scale)
        line_strokes = drawing.offsets_to_coords(offsets)
        line_strokes = drawing.denoise(line_strokes)
        if line_strokes.shape[0] == 0:
            cursor_y += line_height_px
            continue
        line_strokes[:, :2] = drawing.align(line_strokes[:, :2])

        # SVG coordinate system is y-down; flip
        line_strokes[:, 1] *= -1

        # Normalize to start at (0,0)
        min_xy = line_strokes[:, :2].min(axis=0)
        line_strokes[:, :2] -= min_xy

        # Compute scale to fit within content box (both width and height)
        raw_w = max(1e-6, line_strokes[:, 0].max())
        raw_h = max(1e-6, line_strokes[:, 1].max())
        target_h = 0.95 * line_height_px
        s_w = content_width_px / raw_w
        s_h = target_h / raw_h
        # Allow upscaling to fill width while respecting height
        s = min(s_w, s_h)
        line_strokes[:, :2] *= s

        # Horizontal alignment within content box
        final_w = line_strokes[:, 0].max()
        if align == 'center':
            offset_x = m_left + (content_width_px - final_w) / 2.0
        elif align == 'right':
            offset_x = m_left + (content_width_px - final_w)
        else:  # left
            offset_x = m_left

        offset_y = cursor_y
        line_strokes[:, 0] += offset_x
        line_strokes[:, 1] += offset_y

        prev_eos = 1.0
        p = "M{},{} ".format(0, 0)
        for x, y, eos in zip(*line_strokes.T):
            p += '{}{},{} '.format('M' if prev_eos == 1.0 else 'L', x, y)
            prev_eos = eos
        path = svgwrite.path.Path(p)
        path = path.stroke(color=color, width=width, linecap='round').fill('none')
        dwg.add(path)

        cursor_y += line_height_px

    dwg.save()
