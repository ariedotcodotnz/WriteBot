"""Dimensional tests for the natural-handwriting sizing in `_draw`.

Model-free: synthetic stroke arrays with a known body height are fed through
`_draw`, then the rendered SVG is parsed and measured in page pixels. These pin
down the *behaviour* of the sizing/spacing logic (consistent x-height, spacing
proportional to size, width does not shrink everything, shrink-to-fit-one-page,
manual scale as a multiple of natural) without judging visual "naturalness".

Run: `python tests/test_sizing.py` or `pytest tests/test_sizing.py`.
"""

import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from handwriting_synthesis import drawing
from handwriting_synthesis.hand import _draw as draw_mod
from handwriting_synthesis.hand._draw import (
    _draw, PX_PER_MM, NATURAL_WRITING_SIZE_MM,
    solve_fill_xheight_px, LINE_SPACING_PER_XHEIGHT,
)

_COORD = re.compile(r'[ML]\s*([-\d.]+)[\s,]+([-\d.]+)')


def _segment(text, width_units=180.0, xheight=20.0, ascender_frac=0.0, n=240, line_idx=0):
    """A synthetic generated segment.

    Most points sit in the body band [0, xheight]; a fraction are pushed up to
    ~2x xheight to emulate ascenders, so the 10..90 percentile band ~= xheight.
    """
    xs = np.linspace(0.0, width_units, n)
    ys = np.abs(np.sin(np.linspace(0.0, 9 * np.pi, n))) * xheight  # body in [0, xheight]
    if ascender_frac > 0:
        k = max(1, int(n * ascender_frac))
        ys[np.linspace(0, n - 1, k).astype(int)] = 2.0 * xheight  # occasional tall strokes
    coords = np.stack([xs, ys, np.zeros(n)], axis=1)
    coords[-1, 2] = 1.0
    return {'type': 'generated', 'text': text, 'strokes': drawing.coords_to_offsets(coords),
            'line_idx': line_idx}


def _render(line_segments, page=(210.0, 297.0), margins=20.0, **kw):
    fd, path = tempfile.mkstemp(suffix='.svg')
    os.close(fd)
    opts = dict(page_size=list(page), units='mm', margins=margins, align='left',
                legibility='high', denoise=False, auto_size=True, background='white')
    opts.update(kw)
    _draw(line_segments, [s[0].get('text', '') for s in line_segments], path, **opts)
    return path


def _line_y_bands(path):
    """Return, per top-level path, (min_y, max_y, p10, p90) of its point y-coords."""
    root = ET.parse(path).getroot()
    bands = []
    for child in root:
        if child.tag.split('}')[-1] != 'path':
            continue
        ys = [float(y) for _, y in _COORD.findall(child.get('d', ''))]
        if ys:
            a = np.array(ys)
            bands.append((a.min(), a.max(), float(np.percentile(a, 10)), float(np.percentile(a, 90))))
    return bands


def _rendered_xheight_mm(path):
    """Median rendered 10..90 body band across lines, in mm."""
    bands = _line_y_bands(path)
    assert bands, "no generated paths in output"
    spans_px = [p90 - p10 for (_, _, p10, p90) in bands]
    return float(np.median(spans_px)) / PX_PER_MM


def _baseline_spacing_mm(path):
    """Median gap between consecutive lines' bottoms (a baseline proxy), in mm."""
    bands = sorted(_line_y_bands(path), key=lambda b: b[1])
    bottoms = [b[1] for b in bands]
    if len(bottoms) < 2:
        return None
    gaps = np.diff(bottoms)
    return float(np.median(gaps)) / PX_PER_MM


def test_default_xheight_is_natural():
    """Default auto-size renders a body x-height ~= NATURAL_WRITING_SIZE_MM."""
    segs = [[_segment("hello world", line_idx=i)] for i in range(4)]
    xh = _rendered_xheight_mm(_render(segs))
    assert abs(xh - NATURAL_WRITING_SIZE_MM) <= 0.9, xh


def test_writing_size_mm_controls_size():
    """Rendered x-height tracks the writing_size_mm knob (and bigger = bigger)."""
    segs = [[_segment("hello world", line_idx=i)] for i in range(4)]
    small = _rendered_xheight_mm(_render(segs, writing_size_mm=3.0))
    big = _rendered_xheight_mm(_render(segs, writing_size_mm=6.0))
    assert abs(small - 3.0) <= 0.8, small
    assert abs(big - 6.0) <= 1.0, big
    assert big > small + 1.5


def test_xheight_consistent_despite_ascenders():
    """A line full of ascenders must not shrink the document's x-height.

    This is the core fix: previously the tallest line set a global min scale that
    shrank everything; now sizing uses a robust body height per line.
    """
    no_asc = [[_segment("aaa eee ooo", ascender_frac=0.0, line_idx=i)] for i in range(4)]
    with_asc = [[_segment("aaa eee ooo", ascender_frac=0.0, line_idx=0)],
                [_segment("llll kkkk hhhh", ascender_frac=0.30, line_idx=1)],
                [_segment("aaa eee ooo", ascender_frac=0.0, line_idx=2)],
                [_segment("aaa eee ooo", ascender_frac=0.0, line_idx=3)]]
    xh_plain = _rendered_xheight_mm(_render(no_asc))
    xh_mixed = _rendered_xheight_mm(_render(with_asc))
    assert abs(xh_plain - xh_mixed) <= 0.7, (xh_plain, xh_mixed)


def test_one_wide_line_does_not_shrink_others():
    """A single very long line must not shrink the size of the normal lines."""
    normal = [[_segment("hello", width_units=120.0, line_idx=i)] for i in range(5)]
    with_wide = [[_segment("hello", width_units=120.0, line_idx=0)],
                 [_segment("x" * 50, width_units=2000.0, line_idx=1)]]  # one huge outlier
    with_wide += [[_segment("hello", width_units=120.0, line_idx=i)] for i in range(2, 5)]
    xh_normal = _rendered_xheight_mm(_render(normal))
    xh_wide = _rendered_xheight_mm(_render(with_wide))
    # The outlier is condensed per-line, not allowed to shrink everyone.
    assert xh_wide >= xh_normal - 0.6, (xh_normal, xh_wide)


def test_spacing_tracks_size_when_auto():
    """With auto line height, baseline spacing scales with the writing size."""
    segs = [[_segment("hello world", line_idx=i)] for i in range(5)]
    sp_small = _baseline_spacing_mm(_render(segs, writing_size_mm=3.0))
    sp_big = _baseline_spacing_mm(_render(segs, writing_size_mm=6.0))
    assert sp_small and sp_big and sp_big > sp_small + 2.0, (sp_small, sp_big)


def test_shrinks_to_fit_one_page():
    """Many lines on a short page shrink (size + spacing) to stay on one page."""
    many = [[_segment("hello world", line_idx=i)] for i in range(60)]
    path = _render(many, page=(210.0, 297.0), margins=20.0, writing_size_mm=5.0)
    bands = _line_y_bands(path)
    max_y_px = max(b[1] for b in bands)
    page_h_px = 297.0 * PX_PER_MM
    assert max_y_px <= page_h_px + 2.0, (max_y_px, page_h_px)            # stays on page
    assert _rendered_xheight_mm(path) < 5.0                              # was scaled down


def test_fill_solver_fills_target_height():
    """The solved x-height plugs back into the height model at the fill target."""
    W, mxh, content_w, content_h = 5000.0, 20.0, 600.0, 900.0
    h = solve_fill_xheight_px(W, mxh, 0, content_w, content_h, fill_frac=0.92)
    assert h and h > 0
    n_lines = W * h / (mxh * content_w)
    height = n_lines * LINE_SPACING_PER_XHEIGHT * h
    assert abs(height - 0.92 * content_h) < 1e-6, (height, 0.92 * content_h)


def test_fill_solver_monotonic():
    """More text or more blank lines -> smaller solved size; both reduce h."""
    args = dict(model_xheight=20.0, content_width_px=600.0, content_height_px=900.0)
    h_short = solve_fill_xheight_px(2000.0, n_blank_lines=0, **args)
    h_long = solve_fill_xheight_px(20000.0, n_blank_lines=0, **args)
    h_blanks = solve_fill_xheight_px(2000.0, n_blank_lines=5, **args)
    assert h_long < h_short, (h_long, h_short)
    assert h_blanks < h_short, (h_blanks, h_short)


def test_fill_solver_degenerate_inputs():
    assert solve_fill_xheight_px(0.0, 20.0, 0, 600.0, 900.0) is None
    assert solve_fill_xheight_px(100.0, 0.0, 0, 600.0, 900.0) is None
    assert solve_fill_xheight_px(100.0, 20.0, 0, 0.0, 900.0) is None


def test_manual_scale_is_multiple_of_natural():
    """auto_size=False: manual_size_scale=2 renders ~2x the natural size."""
    segs = [[_segment("hello world", line_idx=i)] for i in range(3)]
    natural = _rendered_xheight_mm(_render(segs, auto_size=True))
    doubled = _rendered_xheight_mm(_render(segs, auto_size=False, manual_size_scale=2.0))
    assert doubled > natural * 1.6, (natural, doubled)


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items())
             if k.startswith('test_') and callable(v)]
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
