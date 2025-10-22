#!/usr/bin/env python3
"""
One-time script to generate SVG samples for each available handwriting style.
This creates preview images for the style dropdown in the web UI.
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from handwriting_synthesis.hand.Hand import Hand

def generate_style_samples():
    """Generate SVG sample files for each available style."""

    # Initialize the Hand model
    print("Initializing Hand model...")
    hand = Hand()

    # Sample text to display for each style
    sample_text = "Sample Style"

    # Output directory for SVG samples
    output_dir = os.path.join(PROJECT_ROOT, "model", "style")

    # Available styles (1-12 based on the directory listing)
    styles = range(1, 13)

    print(f"\nGenerating SVG samples for {len(list(styles))} styles...")
    print(f"Output directory: {output_dir}\n")

    for style_id in styles:
        output_file = os.path.join(output_dir, f"style-{style_id}.svg")

        try:
            print(f"Generating style {style_id}...", end=" ")

            # Generate handwriting with compact settings for dropdown preview
            hand.write_chunked(
                filename=output_file,
                text=sample_text,
                max_line_width=400.0,  # Compact width for preview
                words_per_chunk=3,
                chunk_spacing=8.0,
                rotate_chunks=True,
                min_words_per_chunk=2,
                max_words_per_chunk=4,
                target_chars_per_chunk=25,
                adaptive_chunking=True,
                adaptive_strategy="balanced",
                biases=0.75,  # Default bias for consistency
                styles=style_id,  # The style to generate
                stroke_colors="black",
                stroke_widths=2,
                page_size=[50, 10],  # Small page size for compact preview (mm)
                units="mm",
                margins=[1, 1, 1, 1],  # Minimal margins
                line_height=None,  # Auto line height
                align="left",
                background="transparent",  # Transparent background for dropdown
                global_scale=6.0,
                orientation="landscape",
                legibility="normal",
                x_stretch=1.0,
                denoise=True,
                empty_line_spacing=None,
                auto_size=True,
                manual_size_scale=1.0,
            )

            print(f"✓ Created {output_file}")

        except Exception as e:
            print(f"✗ Error: {str(e)}")
            continue

    print(f"\n✓ Sample generation complete!")
    print(f"Generated samples are located in: {output_dir}")
    print(f"Files are named: style-1.svg, style-2.svg, ... style-12.svg\n")


if __name__ == "__main__":
    generate_style_samples()
