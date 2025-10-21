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


def main():
    parser = argparse.ArgumentParser(description='Batch generate SVG handwriting from CSV')
    parser.add_argument('csv', help='CSV file with rows to generate. Required column: text. Optional: filename, biases, styles, stroke_colors, stroke_widths, page_size, units, margins, line_height, align, background, global_scale, orientation, wrap_char_px, wrap_ratio, wrap_utilization, legibility')
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
        lines = text.splitlines()

        filename = r.get('filename') or f'sample_{idx}.svg'
        out_path = os.path.join(args.out_dir, os.path.basename(filename))

        biases = parse_list(r.get('biases'), float)
        styles = parse_list(r.get('styles'), int)
        stroke_colors = parse_list(r.get('stroke_colors'), str)
        stroke_widths = parse_list(r.get('stroke_widths'), float)
        margins = r.get('margins') or 20
        try:
            if isinstance(margins, str) and ',' in margins:
                margins = [float(x.strip()) for x in margins.split(',')]
            elif isinstance(margins, str) and margins.strip():
                margins = float(margins)
        except Exception:
            margins = 20

        hand.write(
            filename=out_path,
            lines=lines,
            biases=biases,
            styles=styles,
            stroke_colors=stroke_colors,
            stroke_widths=stroke_widths,
            page_size=r.get('page_size', 'A4'),
            units=r.get('units', 'mm'),
            margins=margins,
            line_height=float(r.get('line_height')) if str(r.get('line_height')).strip() else None,
            align=r.get('align', 'left'),
            background=r.get('background') if str(r.get('background')).strip() else None,
            global_scale=float(r.get('global_scale')) if str(r.get('global_scale')).strip() else 1.0,
            orientation=r.get('orientation', 'portrait'),
            legibility=r.get('legibility', 'normal'),
        )
        print(f"Wrote {out_path}")


if __name__ == '__main__':
    main()


