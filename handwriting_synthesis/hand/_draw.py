import math
import numpy as np
import svgwrite
import xml.etree.ElementTree as ET
import re

from handwriting_synthesis import drawing


PX_PER_MM = 96.0 / 25.4

PAPER_SIZES_MM = {
    'A5': (148.0, 210.0),
    'A4': (210.0, 297.0),
    'Letter': (215.9, 279.4),
    'Legal': (215.9, 355.6),
}


def _to_px(value, units):
    """
    Converts a value to pixels based on the given unit.

    Args:
        value: The value to convert.
        units: The unit of the value ('mm' or 'px').

    Returns:
        The value in pixels.
    """
    if units == 'mm':
        return value * PX_PER_MM
    return float(value)


def _normalize_margins(margins, units):
    """
    Normalizes margins to a tuple of (top, right, bottom, left) in pixels.

    Args:
        margins: Margins as a scalar, list/tuple of 4, or dict.
        units: The unit of the margins.

    Returns:
        Tuple of (top, right, bottom, left) in pixels.
    """
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
    """
    Resolves the page size to width and height in pixels.

    Args:
        page_size: Page size string (e.g., 'A4') or tuple (width, height).
        units: The unit of the page size.
        num_lines: Number of lines to estimate height if needed.
        default_line_height_px: Default line height in pixels.

    Returns:
        Tuple (width_px, height_px, svg_size_str).
    """
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
    margin_jitter_frac=None,  # Bi-directional left margin jitter (fraction of content width)
    margin_jitter_coherence=None,  # Smoothing factor for coherent line-to-line jitter (0-1)
):
    """
    Draws generated handwriting strokes to an SVG file.

    This function handles the layout, scaling, and rendering of handwriting
    strokes onto a page, including support for character overrides and
    various formatting options.

    Args:
        line_segments: List of segments for each line, where each segment
                       contains stroke data or override info.
        lines: Original text lines (used for reference/colors/widths).
        filename: Output SVG file path.
        stroke_colors: List of colors for each line.
        stroke_widths: List of stroke widths for each line.
        page_size: Page size identifier or dimensions.
        units: Units for dimensions ('mm' or 'px').
        margins: Page margins.
        line_height: Vertical spacing between lines.
        align: Horizontal alignment ('left', 'center', 'right').
        background: Background color.
        global_scale: Global scaling factor for strokes.
        orientation: Page orientation ('portrait' or 'landscape').
        legibility: Legibility mode ('normal', 'high', 'natural').
        x_stretch: Horizontal stretch factor.
        denoise: Whether to apply denoising to strokes.
        empty_line_spacing: Spacing for empty lines.
        auto_size: Whether to automatically scale strokes to fit line height.
        manual_size_scale: Manual scaling factor if auto_size is False.
        character_override_collection_id: ID of the character override collection.
        overrides_dict: Dictionary containing character override data.

    Returns:
        None
    """
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

    # Set margin jitter defaults based on legibility if not explicitly provided
    if margin_jitter_frac is None:
        margin_jitter_frac = {'high': 0.0, 'normal': 0.008}.get(legibility, 0.015)
    if margin_jitter_coherence is None:
        margin_jitter_coherence = {'high': 0.0, 'normal': 0.4}.get(legibility, 0.3)

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
                    # No override found, skip or handle error
                    print(f"Warning: No override data found for character '{segment['text']}'")
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
                    'width': width,
                    'text': segment.get('text', '')  # Add original text for spacing checks
                })

        preprocessed_lines.append(preprocessed_segments if preprocessed_segments else [{'empty': True}])

    # Determine global scale: automatic or manual
    if auto_size:
        s_global = min(scale_limits) if scale_limits else 1.0
    else:
        s_global = float(manual_size_scale)

    # BUGFIX: For small pages where auto_size significantly reduces text scale,
    # adjust line height to be proportional to the actual rendered text size.
    # This prevents huge line spacing when text is scaled down to fit narrow pages.
    if auto_size and scale_limits:
        # Calculate what the text height would have been without width constraint
        # scale_limits contains min(s_w, s_h) for each line, where s_h = target_h / raw_h
        # If s_global is much smaller than what s_h alone would give, text is width-constrained
        # In that case, effective line height should scale down proportionally

        # Recalculate scale limits considering only height (not width)
        height_only_scales = []
        for preprocessed_segments in preprocessed_lines:
            for segment in preprocessed_segments:
                if segment.get('type') == 'generated' and 'strokes' in segment:
                    ls = segment['strokes']
                    raw_h = max(1e-6, ls[:, 1].max())
                    s_h = target_h / raw_h
                    height_only_scales.append(s_h)
                    break

        if height_only_scales:
            # The ideal scale based on height alone
            ideal_height_scale = min(height_only_scales)
            # If actual scale is significantly smaller (width-constrained), reduce line height
            if s_global < ideal_height_scale * 0.95:  # Allow 5% tolerance
                scale_ratio = s_global / ideal_height_scale
                # Adjust line height proportionally, but keep some minimum spacing
                adjusted_line_height = line_height_px * scale_ratio
                # Ensure minimum spacing of at least 20% of original to prevent overlapping
                line_height_px = max(adjusted_line_height, line_height_px * 0.2)
                # Also adjust empty line spacing if it was based on line_height_px
                if empty_line_spacing is None:
                    empty_line_spacing_px = line_height_px

    # Second pass: render with uniform scale across lines for consistent letter size
    cursor_y = m_top + (3.0 * line_height_px / 4.0)
    rng = np.random.RandomState(42)
    x_stretch = float(x_stretch) if x_stretch is not None else 1.0

    # Pre-generate bi-directional margin jitter for all lines (Gaussian + coherence smoothing)
    num_lines = len(preprocessed_lines)
    if margin_jitter_frac > 0.0 and num_lines > 0:
        max_jitter = margin_jitter_frac * content_width_px
        sigma = max_jitter * 0.5  # Standard deviation is half the max for natural clustering
        raw_jitters = rng.normal(0, sigma, num_lines)
        raw_jitters = np.clip(raw_jitters, -max_jitter, max_jitter)

        # Apply coherence smoothing (exponential moving average) to prevent jarring jumps
        if margin_jitter_coherence > 0.0:
            alpha = 1.0 - margin_jitter_coherence
            smoothed_jitters = np.zeros(num_lines)
            smoothed_jitters[0] = raw_jitters[0]
            for i in range(1, num_lines):
                smoothed_jitters[i] = alpha * raw_jitters[i] + (1.0 - alpha) * smoothed_jitters[i - 1]
            margin_jitters = smoothed_jitters
        else:
            margin_jitters = raw_jitters
    else:
        margin_jitters = np.zeros(num_lines)

    for line_idx, preprocessed_segments in enumerate(preprocessed_lines):
        # Check if entire line is empty
        if len(preprocessed_segments) == 1 and preprocessed_segments[0].get('empty'):
            cursor_y += empty_line_spacing_px
            continue

        # Calculate total line width by summing all segments
        total_line_width = 0.0
        for seg_idx, segment in enumerate(preprocessed_segments):
            if segment.get('type') == 'generated':
                ls_temp = segment['strokes'].copy()
                ls_temp[:, :2] *= s_global
                if x_stretch != 1.0:
                    ls_temp[:, 0] *= x_stretch
                total_line_width += ls_temp[:, 0].max()
            elif segment.get('type') == 'override':
                # Apply s_global to match generated text scaling
                override_width = segment['estimated_width'] * s_global

                # Check if there's a space before this override character
                has_space_before = False
                if seg_idx > 0:
                    prev_segment = preprocessed_segments[seg_idx - 1]
                    if prev_segment.get('type') == 'generated':
                        prev_text = prev_segment.get('text', '')
                        has_space_before = prev_text.strip() == '' or prev_text.endswith(' ')

                # Check if there's a space after this override character
                has_space_after = False
                if seg_idx < len(preprocessed_segments) - 1:
                    next_segment = preprocessed_segments[seg_idx + 1]
                    if next_segment.get('type') == 'generated':
                        next_text = next_segment.get('text', '')
                        has_space_after = next_text.strip() == '' or next_text.startswith(' ')

                # FIXED: When there's a space adjacent, add space-width spacing
                # When there's no space, add minimal character spacing to prevent touching
                # This accounts for spaces being normalized away in AI-generated segments
                space_width = override_width * 0.35  # Typical space is about 35% of character width
                spacing_before = space_width if has_space_before else override_width * 0.15
                spacing_after = space_width if has_space_after else override_width * 0.15
                total_line_width += spacing_before + override_width + spacing_after

        # BUGFIX: Check if line would overflow page boundary and scale down if needed
        # This prevents text from being cut off on the right edge
        line_scale_x = 1.0
        if total_line_width > content_width_px:
            # Scale down the line to fit within content width
            # Use 0.98 to leave a small margin for safety
            line_scale_x = (content_width_px * 0.98) / total_line_width
            total_line_width = content_width_px * 0.98

        # Horizontal alignment
        if align == 'center':
            line_offset_x = m_left + (content_width_px - total_line_width) / 2.0
        elif align == 'right':
            line_offset_x = m_left + (content_width_px - total_line_width)
        else:
            line_offset_x = m_left

        # Apply bi-directional margin jitter (for ALL lines, all alignments)
        if margin_jitter_frac > 0.0:
            jitter = margin_jitters[line_idx]
            # Safety clamp: don't intrude more than 20% into left margin
            safe_minimum = m_left * 0.8
            line_offset_x = max(safe_minimum, line_offset_x + jitter)
        else:
            # Legacy behavior: positive-only indent for short lines when no margin jitter
            utilization_ratio = total_line_width / max(1.0, content_width_px)
            if indent_max_frac > 0.0 and utilization_ratio < 0.6:
                line_offset_x += float(rng.uniform(0.0, indent_max_frac) * content_width_px)

        if baseline_jitter_frac > 0.0:
            line_offset_y = cursor_y + float(rng.uniform(-baseline_jitter_frac, baseline_jitter_frac) * line_height_px)
        else:
            line_offset_y = cursor_y

        # Render each segment on the line
        cursor_x = line_offset_x
        for seg_idx, segment in enumerate(preprocessed_segments):
            if segment.get('type') == 'generated':
                ls = segment['strokes'].copy()
                ls[:, :2] *= s_global
                if x_stretch != 1.0:
                    ls[:, 0] *= x_stretch

                # Apply line-specific horizontal scaling to prevent overflow
                if line_scale_x != 1.0:
                    ls[:, 0] *= line_scale_x

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
                override_data = segment['override_data']

                # Extract actual character bounds from path data
                try:
                    svg_root = ET.fromstring(override_data['svg_data'])
                    all_x_coords = []
                    all_y_coords = []

                    for elem in svg_root.iter():
                        tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                        if tag_name == 'path':
                            d = elem.get('d', '')
                            coords = re.findall(r'[ML]\s*([-\d.]+)\s+([-\d.]+)', d)
                            for x, y in coords:
                                all_x_coords.append(float(x))
                                all_y_coords.append(float(y))

                    if not all_x_coords or not all_y_coords:
                        print(f"Warning: No coordinates found for override '{segment.get('char', '?')}'")
                        continue

                    # Character bounding box in viewbox coordinates
                    char_min_x = min(all_x_coords)
                    char_max_x = max(all_x_coords)
                    char_min_y = min(all_y_coords)
                    char_max_y = max(all_y_coords)

                    char_width = char_max_x - char_min_x
                    char_height = char_max_y - char_min_y

                    # Calculate scale to match generated text height
                    # Generated text: normalized to start at y=0, height=raw_h, then scaled by s_global
                    # Final height = raw_h * s_global (which may be < target_h when width-constrained)
                    # Override should match: char_height * scale = target_h * s_global
                    effective_target_h = target_h * s_global
                    if char_height > 0:
                        scale = effective_target_h / char_height
                    else:
                        scale = s_global

                    scale_x = scale * x_stretch
                    scale_y = scale

                    # Apply line-specific horizontal scaling to prevent overflow
                    if line_scale_x != 1.0:
                        scale_x *= line_scale_x

                    # Rendered dimensions
                    rendered_width = char_width * scale_x
                    rendered_height = char_height * scale_y

                    # Check if there's a space before this override character
                    has_space_before = False
                    if seg_idx > 0:
                        prev_segment = preprocessed_segments[seg_idx - 1]
                        if prev_segment.get('type') == 'generated':
                            prev_text = prev_segment.get('text', '')
                            # Check if previous segment is all spaces or ends with space
                            has_space_before = prev_text.strip() == '' or prev_text.endswith(' ')

                    # FIXED: Add space-width spacing when there's a space, minimal spacing otherwise
                    # This accounts for spaces being normalized away in AI-generated segments
                    space_width = rendered_width * 0.35  # Typical space is about 35% of character width
                    character_spacing_before = space_width if has_space_before else rendered_width * 0.15
                    cursor_x += character_spacing_before

                    # POSITIONING:
                    # Generated text is normalized so y=0 is at the top, then positioned at line_offset_y
                    # SVG character should match: align its TOP (char_min_y) with line_offset_y

                    pos_x = cursor_x - (char_min_x * scale_x)

                    # Position vertically so the top of the character aligns with line_offset_y
                    # After transform, we want: char_min_y * scale_y + pos_y = line_offset_y
                    # Therefore: pos_y = line_offset_y - (char_min_y * scale_y)
                    pos_y = line_offset_y - (char_min_y * scale_y)

                    # Create group
                    g = dwg.g(transform=f"translate({pos_x},{pos_y}) scale({scale_x},{scale_y})")

                    # Add paths
                    for elem in svg_root.iter():
                        tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

                        if tag_name == 'path':
                            d = elem.get('d')
                            if not d:
                                continue

                            orig_stroke = elem.get('stroke', 'none')

                            path = dwg.path(d=d)

                            if orig_stroke and orig_stroke.lower() not in ('none', 'transparent'):
                                # Use line-level stroke width for consistency with generated text
                                # Compensate for transform scaling to maintain visual thickness
                                line_stroke_width = segment['width']
                                avg_scale = (scale_x + scale_y) / 2.0
                                adjusted_stroke_width = line_stroke_width / avg_scale if avg_scale > 0 else line_stroke_width

                                path = path.stroke(
                                    color=segment['color'],
                                    width=adjusted_stroke_width,
                                    linecap='round',
                                    linejoin='round'
                                ).fill('none')
                            else:
                                path = path.fill(segment['color'])

                            g.add(path)

                    dwg.add(g)

                    # Check if there's a space after this override character
                    has_space_after = False
                    if seg_idx < len(preprocessed_segments) - 1:
                        next_segment = preprocessed_segments[seg_idx + 1]
                        if next_segment.get('type') == 'generated':
                            next_text = next_segment.get('text', '')
                            # Check if next segment is all spaces or starts with space
                            has_space_after = next_text.strip() == '' or next_text.startswith(' ')

                    # FIXED: Add space-width spacing when there's a space, minimal spacing otherwise
                    # This accounts for spaces being normalized away in AI-generated segments
                    space_width = rendered_width * 0.35  # Typical space is about 35% of character width
                    character_spacing_after = space_width if has_space_after else rendered_width * 0.15
                    cursor_x += rendered_width + character_spacing_after

                except Exception as e:
                    print(f"Error rendering override '{segment.get('char', '?')}': {e}")
                    import traceback
                    traceback.print_exc()

        # CRITICAL FIX: Increment cursor_y after processing each line
        cursor_y += line_height_px

    # Add metadata comment if character overrides are enabled
    if character_override_collection_id is not None and overrides_dict:
        try:
            dwg.set_desc(desc=f"Character overrides enabled: collection {character_override_collection_id} with {len(overrides_dict)} characters")
        except Exception as e:
            print(f"Note: Could not add override metadata comment: {e}")

    dwg.save()
