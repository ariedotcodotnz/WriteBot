#!/usr/bin/env python3
"""
Simple script to generate placeholder SVG samples for each available handwriting style.
These are basic SVG text previews that can be replaced with actual handwriting samples later.
"""

import os

def generate_simple_svg_sample(style_id, output_path):
    """Generate a simple SVG preview for a style."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="60" viewBox="0 0 400 60">
  <rect width="400" height="60" fill="transparent"/>
  <text x="10" y="35" font-family="'Segoe Script', 'Brush Script MT', cursive" font-size="24" fill="black">
    Style {style_id} Preview
  </text>
</svg>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)

def main():
    """Generate simple SVG sample files for each available style."""

    # Output directory for SVG samples
    project_root = os.path.abspath(os.path.dirname(__file__))
    output_dir = os.path.join(project_root, "model", "style")

    # Available styles (1-12 based on the directory listing)
    styles = range(1, 13)

    print(f"Generating simple SVG samples for {len(list(styles))} styles...")
    print(f"Output directory: {output_dir}\n")

    for style_id in styles:
        output_file = os.path.join(output_dir, f"style-{style_id}.svg")

        try:
            print(f"Generating style {style_id}...", end=" ")
            generate_simple_svg_sample(style_id, output_file)
            print(f"✓ Created {output_file}")

        except Exception as e:
            print(f"✗ Error: {str(e)}")
            continue

    print(f"\n✓ Sample generation complete!")
    print(f"Generated samples are located in: {output_dir}")
    print(f"Files are named: style-1.svg, style-2.svg, ... style-12.svg")
    print(f"\nNote: These are placeholder previews. Run generate_style_samples.py")
    print(f"      with dependencies installed to generate actual handwriting samples.\n")

if __name__ == "__main__":
    main()
