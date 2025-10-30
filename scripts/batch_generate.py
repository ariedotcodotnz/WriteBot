import argparse
import os
import sys
import pandas as pd

from handwriting_synthesis.hand.Hand import Hand


def parse_list(s, cast):
    if s is None or s == "":
        return None
    if isinstance(s, list):
        return [cast(x) for x in s]
    try:
        return [cast(x.strip()) for x in str(s).split('|')]
    except Exception:
        return [cast(s)]


def parse_bool(s):
    """Parse a boolean value from CSV."""
    if isinstance(s, bool):
        return s
    if isinstance(s, str):
        return s.strip().lower() in ('true', '1', 'yes', 'on')
    return bool(s)


def parse_float_or_none(s):
    """Parse a float value or return None if empty/invalid."""
    if s is None or s == "" or (isinstance(s, str) and not s.strip()):
        return None
    try:
        return float(s)
    except Exception:
        return None


def parse_int_or_none(s):
    """Parse an int value or return None if empty/invalid."""
    if s is None or s == "" or (isinstance(s, str) and not s.strip()):
        return None
    try:
        return int(s)
    except Exception:
        return None


def parse_str_or_none(s):
    """Parse a string value or return None if empty."""
    if s is None or s == "" or (isinstance(s, str) and not s.strip()):
        return None
    return str(s).strip()


def main():
    parser = argparse.ArgumentParser(description='Batch generate SVG handwriting from CSV')
    parser.add_argument('csv', help='CSV file with rows to generate. Required column: text. Optional: filename, biases, styles, stroke_colors, stroke_widths, page_size, units, page_width, page_height, margins, line_height, align, background, global_scale, orientation, legibility, x_stretch, denoise, empty_line_spacing, auto_size, manual_size_scale, character_override_collection_id, use_chunked, words_per_chunk, chunk_spacing, rotate_chunks, min_words_per_chunk, max_words_per_chunk, target_chars_per_chunk, adaptive_chunking, adaptive_strategy')
    parser.add_argument('--out-dir', default='out', help='Output directory for SVGs')
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    df = pd.read_csv(args.csv)
    hand = Hand()

    for idx, row in df.fillna('').iterrows():
        r = row.to_dict()
        text = str(r.get('text', ''))
        if not text:
            print(f"Skipping row {idx}: empty text")
            continue

        filename = r.get('filename') or f'sample_{idx}.svg'
        out_path = os.path.join(args.out_dir, os.path.basename(filename))

        # Parse list parameters
        biases = parse_list(r.get('biases'), float)
        styles = parse_list(r.get('styles'), int)
        stroke_colors = parse_list(r.get('stroke_colors'), str)
        stroke_widths = parse_list(r.get('stroke_widths'), float)

        # Parse margins
        margins = r.get('margins') or 20
        try:
            if isinstance(margins, str) and ',' in margins:
                margins = [float(x.strip()) for x in margins.split(',')]
            elif isinstance(margins, str) and margins.strip():
                margins = float(margins)
        except Exception:
            margins = 20

        # Parse page dimensions
        page_size = parse_str_or_none(r.get('page_size')) or 'A4'
        units = parse_str_or_none(r.get('units')) or 'mm'
        page_width = parse_float_or_none(r.get('page_width'))
        page_height = parse_float_or_none(r.get('page_height'))

        # Parse optional parameters
        line_height = parse_float_or_none(r.get('line_height'))
        align = parse_str_or_none(r.get('align')) or 'left'
        background = parse_str_or_none(r.get('background'))
        global_scale = parse_float_or_none(r.get('global_scale')) or 1.0
        orientation = parse_str_or_none(r.get('orientation')) or 'portrait'
        legibility = parse_str_or_none(r.get('legibility')) or 'normal'
        x_stretch = parse_float_or_none(r.get('x_stretch')) or 1.0
        denoise = parse_bool(r.get('denoise')) if r.get('denoise') != '' else True
        empty_line_spacing = parse_float_or_none(r.get('empty_line_spacing'))
        auto_size = parse_bool(r.get('auto_size')) if r.get('auto_size') != '' else True
        manual_size_scale = parse_float_or_none(r.get('manual_size_scale')) or 1.0
        character_override_collection_id = parse_str_or_none(r.get('character_override_collection_id'))

        # Check if chunked mode is requested
        use_chunked = parse_bool(r.get('use_chunked')) if r.get('use_chunked') != '' else False

        if use_chunked:
            # Parse chunked mode parameters
            words_per_chunk = parse_int_or_none(r.get('words_per_chunk')) or 3
            chunk_spacing = parse_float_or_none(r.get('chunk_spacing')) or 8.0
            rotate_chunks = parse_bool(r.get('rotate_chunks')) if r.get('rotate_chunks') != '' else True
            min_words_per_chunk = parse_int_or_none(r.get('min_words_per_chunk')) or 2
            max_words_per_chunk = parse_int_or_none(r.get('max_words_per_chunk')) or 8
            target_chars_per_chunk = parse_int_or_none(r.get('target_chars_per_chunk')) or 25
            adaptive_chunking = parse_bool(r.get('adaptive_chunking')) if r.get('adaptive_chunking') != '' else True
            adaptive_strategy = parse_str_or_none(r.get('adaptive_strategy')) or 'balanced'

            # Use write_chunked for chunked mode
            hand.write_chunked(
                filename=out_path,
                text=text,
                words_per_chunk=words_per_chunk,
                chunk_spacing=chunk_spacing,
                rotate_chunks=rotate_chunks,
                min_words_per_chunk=min_words_per_chunk,
                max_words_per_chunk=max_words_per_chunk,
                target_chars_per_chunk=target_chars_per_chunk,
                adaptive_chunking=adaptive_chunking,
                adaptive_strategy=adaptive_strategy,
                biases=biases,
                styles=styles,
                stroke_colors=stroke_colors,
                stroke_widths=stroke_widths,
                page_size=page_size if not (page_width and page_height) else [page_width, page_height],
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
            )
        else:
            # Use regular write for line-by-line mode
            lines = text.splitlines()
            hand.write(
                filename=out_path,
                lines=lines,
                biases=biases,
                styles=styles,
                stroke_colors=stroke_colors,
                stroke_widths=stroke_widths,
                page_size=page_size if not (page_width and page_height) else [page_width, page_height],
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
            )
        print(f"Wrote {out_path}")


if __name__ == '__main__':
    main()


