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
    line_segments,  # Changed from 'strokes' to 'line_segments'
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
    overrides_dict=None,  # New parameter
):
    # Load character overrides if not provided
    if overrides_dict is None:
        overrides_dict = {}
        if character_override_collection_id is not None:
            try:
                from handwriting_synthesis.hand.character_override_utils import get_character_overrides
                overrides_dict = get_character_overrides(character_override_collection_id)
            except Exception as e:
                print(f"Warning: Could not load character overrides: {e}")

    stroke_colors = stroke_colors or ['black'] * len(lines)
    stroke_widths = stroke_widths or [2] * len(lines)

    default_line_height_px = 60.0
    width_px, height_px, svg_size = _resolve_page_size(page_size, units, len(line_segments), default_line_height_px)
    m_top, m_right, m_bottom, m_left = _normalize_margins(margins, units)

    content_width_px = max(1.0, width_px - (m_left + m_right))
    content_height_px = max(1.0, height_px - (m_top + m_bottom))

    line_height_px = _to_px(line_height, units) if line_height is not None else default_line_height_px
    # Ensure all lines fit vertically
    max_line_height_px = content_height_px / max(1, len(line_segments) + 0)
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
    preprocessed_lines = []
    scale_limits = []
    target_h = 0.95 * line_height_px

    for line_idx, segment_list in enumerate(line_segments):
        if not segment_list:
            preprocessed_lines.append([{'empty': True}])
            continue

        preprocessed_segments = []
        color = stroke_colors[line_idx]
        width = stroke_widths[line_idx]

        for segment in segment_list:
            if segment['type'] == 'override':
                # Get random override variant
                from handwriting_synthesis.hand.character_override_utils import get_random_override, estimate_override_width
                override_data = get_random_override(overrides_dict, segment['text'])
                if override_data:
                    # Estimate width for this override
                    estimated_width = estimate_override_width(override_data, target_h, x_stretch)
                    preprocessed_segments.append({
                        'type': 'override',
                        'char': segment['text'],
                        'override_data': override_data,
                        'estimated_width': estimated_width,
                        'color': color,
                        'width': width
                    })
                else:
                    # No override found - log detailed warning
                    available_chars = ', '.join(sorted(overrides_dict.keys())) if overrides_dict else 'none'
                    print(f"WARNING: No override data found for character '{segment['text']}'")
                    print(f"  Available override characters: {available_chars}")
                    print(f"  This character will be skipped in the output (will appear as a gap)")
            else:
                # Generated segment
                offsets = segment['strokes']
                if offsets.shape[0] == 0:
                    preprocessed_segments.append({'type': 'empty'})
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
                    preprocessed_segments.append({'type': 'empty'})
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
                preprocessed_segments.append({
                    'type': 'generated',
                    'strokes': ls,
                    'color': color,
                    'width': width
                })

        preprocessed_lines.append(preprocessed_segments if preprocessed_segments else [{'empty': True}])

    # Determine global scale: automatic or manual
    if auto_size:
        s_global = min(scale_limits) if scale_limits else 1.0
    else:
        s_global = float(manual_size_scale)

    # Second pass: render with uniform scale across lines for consistent letter size
    cursor_y = m_top + (3.0 * line_height_px / 4.0)
    rng = np.random.RandomState(42)
    x_stretch = float(x_stretch) if x_stretch is not None else 1.0

    for preprocessed_segments in preprocessed_lines:
        # Check if entire line is empty
        if len(preprocessed_segments) == 1 and preprocessed_segments[0].get('empty'):
            cursor_y += empty_line_spacing_px
            continue

        # Calculate total line width by summing all segments
        total_line_width = 0.0
        for segment in preprocessed_segments:
            if segment.get('type') == 'generated':
                ls_temp = segment['strokes'].copy()
                ls_temp[:, :2] *= s_global
                if x_stretch != 1.0:
                    ls_temp[:, 0] *= x_stretch
                total_line_width += ls_temp[:, 0].max()
            elif segment.get('type') == 'override':
                # Use estimated width scaled
                total_line_width += segment['estimated_width'] * s_global

        # Horizontal alignment
        if align == 'center':
            line_offset_x = m_left + (content_width_px - total_line_width) / 2.0
        elif align == 'right':
            line_offset_x = m_left + (content_width_px - total_line_width)
        else:
            line_offset_x = m_left

        utilization_ratio = total_line_width / max(1.0, content_width_px)
        if indent_max_frac > 0.0 and utilization_ratio < 0.6:
            line_offset_x += float(rng.uniform(0.0, indent_max_frac) * content_width_px)

        if baseline_jitter_frac > 0.0:
            line_offset_y = cursor_y + float(rng.uniform(-baseline_jitter_frac, baseline_jitter_frac) * line_height_px)
        else:
            line_offset_y = cursor_y

        # Render each segment on the line
        cursor_x = line_offset_x
        for segment in preprocessed_segments:
            if segment.get('type') == 'generated':
                ls = segment['strokes'].copy()
                ls[:, :2] *= s_global
                if x_stretch != 1.0:
                    ls[:, 0] *= x_stretch

                # Track segment width before translating
                segment_width = ls[:, 0].max()

                ls[:, 0] += cursor_x
                ls[:, 1] += line_offset_y

                prev_eos = 1.0
                commands = []
                for x, y, eos in zip(*ls.T):
                    commands.append('{}{},{}'.format('M' if prev_eos == 1.0 else 'L', x, y))
                    prev_eos = eos
                p = ' '.join(commands)
                path = svgwrite.path.Path(p)
                path = path.stroke(color=segment['color'], width=segment['width'], linecap='round', linejoin='round', miterlimit=2).fill('none')
                dwg.add(path)

                # Advance cursor by segment width
                cursor_x += segment_width

            elif segment.get('type') == 'override':
                # Insert override SVG
                override_data = segment['override_data']

                # Calculate scaling
                vb_height = override_data['viewbox_height']
                if vb_height > 0:
                    scale = (target_h / vb_height) * s_global
                else:
                    scale = s_global

                # Apply x_stretch
                scale_x = scale * x_stretch
                scale_y = scale

                # Position: cursor_x, baseline adjusted
                # The baseline should account for the scaled height, not the target height
                baseline_offset = override_data.get('baseline_offset', 0.0)
                pos_x = cursor_x
                pos_y = line_offset_y - (target_h * s_global * 0.75) + baseline_offset * s_global

                # Create a group for the override character
                g = dwg.g(transform=f"translate({pos_x},{pos_y}) scale({scale_x},{scale_y})")

                # Parse and add SVG paths
                import xml.etree.ElementTree as ET
                try:
                    svg_root = ET.fromstring(override_data['svg_data'])
                    for elem in svg_root.iter():
                        if elem.tag.endswith('path'):
                            d = elem.get('d')
                            if d:
                                # Get original attributes
                                orig_fill = elem.get('fill')
                                orig_stroke = elem.get('stroke')
                                orig_stroke_width = elem.get('stroke-width')
                                orig_stroke_linecap = elem.get('stroke-linecap')
                                orig_stroke_linejoin = elem.get('stroke-linejoin')

                                # Determine if this path uses fill or stroke
                                uses_stroke = (orig_stroke and orig_stroke.lower() not in ('none', 'transparent'))
                                uses_fill = (not orig_fill or orig_fill.lower() not in ('none', 'transparent'))

                                # Create path with appropriate attributes
                                if uses_stroke and not uses_fill:
                                    # Stroke-based rendering
                                    path = dwg.path(d=d)
                                    path = path.stroke(
                                        color=segment['color'],
                                        width=float(orig_stroke_width) if orig_stroke_width else segment['width'],
                                        linecap=orig_stroke_linecap or 'round',
                                        linejoin=orig_stroke_linejoin or 'round'
                                    ).fill('none')
                                else:
                                    # Fill-based rendering (default)
                                    path = dwg.path(d=d, fill=segment['color'])
                                    if uses_stroke:
                                        # Has both fill and stroke
                                        path = path.stroke(
                                            color=segment['color'],
                                            width=float(orig_stroke_width) if orig_stroke_width else 1
                                        )

                                g.add(path)
                        # Add support for other SVG elements if needed
                except Exception as e:
                    print(f"Error rendering override character '{segment['char']}': {e}")

                dwg.add(g)

                # Advance cursor
                cursor_x += segment['estimated_width'] * s_global

        cursor_y += line_height_px

    # Add metadata comment if character overrides are enabled
    if character_override_collection_id is not None and overrides_dict:
        try:
            dwg.set_desc(desc=f"Character overrides enabled: collection {character_override_collection_id} with {len(overrides_dict)} characters")
        except Exception as e:
            print(f"Note: Could not add override metadata comment: {e}")

    dwg.save()
