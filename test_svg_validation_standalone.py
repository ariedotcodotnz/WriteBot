#!/usr/bin/env python3
"""
Standalone test script for SVG validation
Tests validation logic without requiring Flask dependencies
"""

import xml.etree.ElementTree as ET
import re

def parse_svg_viewbox(svg_content):
    """
    Parse SVG content and extract viewBox dimensions.
    Returns tuple: (viewbox_x, viewbox_y, viewbox_width, viewbox_height)
    """
    try:
        root = ET.fromstring(svg_content)
        viewbox = root.get('viewBox') or root.get('viewbox')
        if viewbox:
            viewbox_clean = re.sub(r'[,\s]+', ' ', viewbox.strip())
            parts = viewbox_clean.split()
            if len(parts) == 4:
                try:
                    return tuple(float(x) for x in parts)
                except ValueError as e:
                    print(f"Warning: Could not parse viewBox values: {e}")
                    pass

        width = root.get('width')
        height = root.get('height')
        if width and height:
            try:
                width = re.sub(r'[a-zA-Z%]+$', '', str(width).strip())
                height = re.sub(r'[a-zA-Z%]+$', '', str(height).strip())
                w = float(width)
                h = float(height)
                if w > 0 and h > 0:
                    return (0.0, 0.0, w, h)
            except ValueError as e:
                print(f"Warning: Could not parse width/height: {e}")
                pass

        return None
    except Exception as e:
        print(f"Error parsing SVG: {e}")
        return None


def validate_svg(svg_content):
    """
    Validate SVG content and check if it meets requirements.
    Returns (is_valid, error_message, viewbox_data)
    """
    try:
        if not svg_content or not svg_content.strip():
            return False, "SVG content is empty", None

        try:
            root = ET.fromstring(svg_content)
        except ET.ParseError as e:
            return False, f"Invalid XML format: {str(e)}", None

        tag_name = root.tag.lower()
        if not (tag_name == 'svg' or tag_name.endswith('}svg')):
            return False, f"Root element must be <svg>, found: {root.tag}", None

        viewbox_data = parse_svg_viewbox(svg_content)
        if not viewbox_data:
            return False, "SVG must have a viewBox or width/height attributes with valid numeric values", None

        x, y, width, height = viewbox_data
        if width <= 0 or height <= 0:
            return False, f"Invalid viewBox dimensions: width and height must be positive (got {width}x{height})", None

        has_content = False
        drawable_elements = ['path', 'circle', 'ellipse', 'rect', 'line', 'polyline', 'polygon', 'text']
        for elem in root.iter():
            elem_name = elem.tag.lower()
            for drawable in drawable_elements:
                if drawable in elem_name:
                    has_content = True
                    break
            if has_content:
                break

        if not has_content:
            return False, "SVG appears to be empty (no drawable elements found)", None

        return True, None, viewbox_data

    except Exception as e:
        return False, f"Unexpected error validating SVG: {str(e)}", None


def test_svg_file(filepath, description):
    """Test an SVG file with validation"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"{'='*60}")

    try:
        with open(filepath, 'r') as f:
            svg_content = f.read()

        print(f"File: {filepath}")
        print(f"Size: {len(svg_content)} bytes")

        is_valid, error_message, viewbox_data = validate_svg(svg_content)

        print(f"\nValidation Result: {'✓ PASS' if is_valid else '✗ FAIL'}")
        if error_message:
            print(f"Error: {error_message}")
        if viewbox_data:
            print(f"ViewBox: x={viewbox_data[0]}, y={viewbox_data[1]}, width={viewbox_data[2]}, height={viewbox_data[3]}")

        return is_valid

    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
        return False

def test_svg_string(svg_content, description):
    """Test an SVG string with validation"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"{'='*60}")

    print(f"Size: {len(svg_content)} bytes")

    is_valid, error_message, viewbox_data = validate_svg(svg_content)

    print(f"\nValidation Result: {'✓ PASS' if is_valid else '✗ FAIL'}")
    if error_message:
        print(f"Error: {error_message}")
    if viewbox_data:
        print(f"ViewBox: x={viewbox_data[0]}, y={viewbox_data[1]}, width={viewbox_data[2]}, height={viewbox_data[3]}")

    return is_valid

def main():
    print("\n" + "="*60)
    print("SVG Validation Test Suite (Standalone)")
    print("="*60)

    results = []

    # Test 1: Existing test @ symbol (user's working example)
    results.append(test_svg_file(
        '/home/user/WriteBot/test_at_symbol.svg',
        'User provided @ symbol that works'
    ))

    # Test 2: Simulated Canvas-generated SVG (simple)
    canvas_svg_simple = """<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="50.00 100.00 150.00 200.00" xmlns="http://www.w3.org/2000/svg">
  <!-- Auto-generated from Canvas drawing -->
  <!-- Pen-plotter compatible: stroke-based, not filled -->
  <path d="M 60.00 120.00 L 70.50 130.25 L 80.75 140.50 L 90.00 150.00" stroke="black" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M 120.00 180.00 L 130.00 190.00 L 140.00 200.00" stroke="black" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>"""
    results.append(test_svg_string(canvas_svg_simple, 'Canvas-generated SVG (simple)'))

    # Test 3: SVG with commas in viewBox
    svg_with_commas = """<svg viewBox="0,0,100,150" xmlns="http://www.w3.org/2000/svg">
  <path d="M 10 10 L 90 90" stroke="black" stroke-width="2" fill="none"/>
</svg>"""
    results.append(test_svg_string(svg_with_commas, 'SVG with commas in viewBox'))

    # Test 4: SVG with width/height instead of viewBox
    svg_width_height = """<svg width="100" height="150" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="75" r="30" stroke="black" stroke-width="2" fill="none"/>
</svg>"""
    results.append(test_svg_string(svg_width_height, 'SVG with width/height attributes'))

    # Test 5: SVG with units in width/height
    svg_with_units = """<svg width="100px" height="150px" xmlns="http://www.w3.org/2000/svg">
  <rect x="10" y="10" width="80" height="130" stroke="black" stroke-width="2" fill="none"/>
</svg>"""
    results.append(test_svg_string(svg_with_units, 'SVG with units (px) in dimensions'))

    # Test 6: Invalid SVG (empty) - should FAIL
    svg_empty = ""
    test_result = test_svg_string(svg_empty, 'Invalid SVG (empty) - should FAIL')
    results.append(not test_result)  # Invert because we expect failure

    # Test 7: Invalid SVG (no viewBox or dimensions) - should FAIL
    svg_no_dimensions = """<svg xmlns="http://www.w3.org/2000/svg">
  <path d="M 10 10 L 90 90" stroke="black" fill="none"/>
</svg>"""
    test_result = test_svg_string(svg_no_dimensions, 'Invalid SVG (no viewBox/dimensions) - should FAIL')
    results.append(not test_result)  # Invert because we expect failure

    # Test 8: Canvas-generated complex SVG
    canvas_svg_complex = """<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="25.50 30.75 180.25 240.50" xmlns="http://www.w3.org/2000/svg">
  <!-- Auto-generated from Canvas drawing -->
  <!-- Pen-plotter compatible: stroke-based, not filled -->
  <path d="M 50.00 100.00 L 52.34 102.11 L 54.67 104.23 L 56.99 106.35 L 59.32 108.47 L 61.65 110.59" stroke="black" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M 80.00 120.00 L 85.25 125.50 L 90.50 131.00 L 95.75 136.50 L 101.00 142.00" stroke="black" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M 120.00 160.00 L 125.00 165.00 L 130.00 170.00" stroke="black" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>"""
    results.append(test_svg_string(canvas_svg_complex, 'Canvas-generated SVG (complex with multiple strokes)'))

    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
