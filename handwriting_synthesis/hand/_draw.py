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

    # Empty line spacing: if not specified, use regular line_height_px
    empty_line_spacing_px = _to_px(empty_line_spacing, units) if empty_line_spacing is not None else line_height_px

    # Handle orientation
    if isinstance(svg_size, tuple) and len(svg_size) == 2 and orientation == 'landscape':
        svg_size = (svg_size[1], svg_size[0])
        width_px, height_px = height_px, width_px

    dwg = svgwrite.Drawing(filename=filename, size=svg_size)
    dwg.viewbox(0, 0, width_px, height_px)
    # Only draw a background rectangle if explicitly requested and not 'none'/'transparent'
    if background and str(background).strip().lower() not in ('none', 'transparent'):
        dwg.add(dwg.rect(insert=(0, 0), size=(width_px, height_px), fill=background))

    # Normalize legibility string
    legibility = (legibility or 'normal').lower()

    # Configure naturalness jitter by legibility mode
    if legibility == 'high':
        indent_max_frac = 0.0
        baseline_jitter_frac = 0.0
        interpolate_factor = 2
    elif legibility == 'normal':
        indent_max_frac = 0.01
        baseline_jitter_frac = 0.0025
        interpolate_factor = 1
    else:  # 'natural' (default styling)
        indent_max_frac = 0.02
        baseline_jitter_frac = 0.005
        interpolate_factor = 1

    # First pass: preprocess each line and compute per-line max allowed scale
    preprocessed = []
    scale_limits = []
    target_h = 0.95 * line_height_px
    for offsets, line, color, width in zip(strokes, lines, stroke_colors, stroke_widths):
        if not line:
            preprocessed.append({'empty': True})
            continue
        offsets_cp = offsets.copy()
        offsets_cp[:, :2] *= float(global_scale)
        ls = drawing.offsets_to_coords(offsets_cp)
        if denoise:
            ls = drawing.denoise(ls)
        if interpolate_factor > 1:
            try:
                ls = drawing.interpolate(ls, factor=interpolate_factor)
            except Exception:
                pass
        if ls.shape[0] == 0:
            preprocessed.append({'empty': True})
            continue
        ls[:, :2] = drawing.align(ls[:, :2])
        ls[:, 1] *= -1
        min_xy = ls[:, :2].min(axis=0)
        ls[:, :2] -= min_xy
        raw_w = max(1e-6, ls[:, 0].max())
        raw_h = max(1e-6, ls[:, 1].max())
        s_w = content_width_px / raw_w
        s_h = target_h / raw_h
        scale_limits.append(min(s_w, s_h))
        preprocessed.append({'empty': False, 'strokes': ls, 'color': color, 'width': width})

    # Determine global scale: automatic or manual
    if auto_size:
        s_global = min(scale_limits) if scale_limits else 1.0
    else:
        s_global = float(manual_size_scale)

    # Second pass: render with uniform scale across lines for consistent letter size
    cursor_y = m_top + (3.0 * line_height_px / 4.0)
    rng = np.random.RandomState(42)
    x_stretch = float(x_stretch) if x_stretch is not None else 1.0
    for item in preprocessed:
        if item.get('empty'):
            cursor_y += empty_line_spacing_px
            continue
        ls = item['strokes'].copy()
        ls[:, :2] *= s_global
        if x_stretch != 1.0:
            ls[:, 0] *= x_stretch

        # Horizontal alignment within content box with subtle indent jitter for short lines
        final_w = ls[:, 0].max()
        if align == 'center':
            offset_x = m_left + (content_width_px - final_w) / 2.0
        elif align == 'right':
            offset_x = m_left + (content_width_px - final_w)
        else:
            offset_x = m_left
        utilization_ratio = final_w / max(1.0, content_width_px)
        if indent_max_frac > 0.0 and utilization_ratio < 0.6:
            offset_x += float(rng.uniform(0.0, indent_max_frac) * content_width_px)

        if baseline_jitter_frac > 0.0:
            offset_y = cursor_y + float(rng.uniform(-baseline_jitter_frac, baseline_jitter_frac) * line_height_px)
        else:
            offset_y = cursor_y
        ls[:, 0] += offset_x
        ls[:, 1] += offset_y

        prev_eos = 1.0
        commands = []
        for x, y, eos in zip(*ls.T):
            commands.append('{}{},{}'.format('M' if prev_eos == 1.0 else 'L', x, y))
            prev_eos = eos
        p = ' '.join(commands)
        path = svgwrite.path.Path(p)
        path = path.stroke(color=item['color'], width=item['width'], linecap='round', linejoin='round', miterlimit=2).fill('none')
        dwg.add(path)

        cursor_y += line_height_px

    # Add metadata comment if character overrides are enabled
    if character_override_collection_id is not None:
        try:
            from handwriting_synthesis.hand.character_override_utils import get_character_overrides
            overrides = get_character_overrides(character_override_collection_id)
            if overrides:
                # Add an XML comment to indicate character overrides are enabled
                import xml.etree.ElementTree as ET
                comment = ET.Comment(f"Character overrides enabled: collection {character_override_collection_id} with {len(overrides)} characters")
                dwg.add(comment)
        except Exception as e:
            print(f"Note: Character override collection {character_override_collection_id} specified but could not be loaded: {e}")

    dwg.save()
