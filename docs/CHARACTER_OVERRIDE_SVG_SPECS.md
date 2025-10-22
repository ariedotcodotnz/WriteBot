# Character Override SVG Specifications

This document describes the requirements and best practices for creating SVG files for use as character overrides in the WriteBot handwriting generation system.

## Overview

Character overrides allow you to replace AI-generated handwritten characters with your own hand-drawn SVG files. When generating handwriting with character overrides enabled, the system will randomly select from your uploaded character variants to create natural-looking variations.

## SVG File Requirements

### 1. File Format
- **Format**: Valid SVG (Scalable Vector Graphics) XML
- **Extension**: `.svg`
- **Encoding**: UTF-8

### 2. ViewBox or Dimensions
Your SVG **must** include either:
- A `viewBox` attribute (recommended), OR
- Both `width` and `height` attributes

```xml
<!-- Recommended: Using viewBox -->
<svg viewBox="0 0 100 150" xmlns="http://www.w3.org/2000/svg">
  <!-- content -->
</svg>

<!-- Alternative: Using width/height -->
<svg width="100" height="150" xmlns="http://www.w3.org/2000/svg">
  <!-- content -->
</svg>
```

### 3. Recommended Dimensions
- **Height**: 100-200px for optimal rendering
- **Width**: Proportional to the character (typically 50-150px)
- **Aspect Ratio**: Should match the natural proportions of the character

### 4. Path Requirements

#### Convert Strokes to Paths
For consistency, convert all strokes to filled paths:
- In Inkscape: Path → Stroke to Path
- In Adobe Illustrator: Object → Path → Outline Stroke
- In other tools: Look for "Expand Stroke" or similar

#### Color Handling
- Use **single color** for all paths (typically black)
- The system will apply the appropriate stroke color during generation
- Avoid gradients or multiple colors

#### Path Simplification
- Simplify complex paths to reduce file size
- Remove unnecessary anchor points
- Optimize curves for smoother rendering

## Best Practices

### 1. Consistency
- **Baseline Alignment**: Ensure all variants of a character align to the same baseline
- **Size Consistency**: Keep similar proportions across variants
- **Style**: Maintain consistent line weight and style across all characters

### 2. Multiple Variants
- Upload **2-5 variants** per character for natural variation
- Make subtle differences between variants (slight angle changes, minor stroke variations)
- Too many identical variants waste storage; too few reduce naturalness

### 3. File Naming Convention
When batch uploading, the system extracts the character from the filename:
- **Format**: `{character}.svg` or `{character}_{variant}.svg`
- **Examples**:
  - `a.svg`, `a_1.svg`, `a_2.svg` → All recognized as variants of 'a'
  - `b.svg`, `b_1.svg` → Variants of 'b'

### 4. Baseline Offset
The **baseline offset** parameter allows you to adjust vertical positioning:
- **0.0** (default): No adjustment
- **Positive values**: Move character down
- **Negative values**: Move character up
- Typical range: -10 to +10

Use this to ensure characters align properly with AI-generated text.

## Creating SVG Characters

### Using Inkscape (Free)
1. Create a new document
2. Draw your character using the pen or brush tool
3. Convert strokes to paths: Path → Stroke to Path
4. Set fill to black, remove stroke
5. Adjust viewBox: File → Document Properties → Resize to Content
6. Save as Plain SVG

### Using Adobe Illustrator
1. Create a new artboard (100x150px recommended)
2. Draw your character
3. Select all paths: Object → Path → Outline Stroke
4. Set fill to black
5. Save As → SVG
6. In SVG Options: Use "Presentation Attributes" for styling

### Using Procreate (iPad)
1. Create canvas (1000x1500px recommended)
2. Draw character in black
3. Export as SVG
4. May need to clean up in Inkscape or Illustrator

## Example SVG Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="0 0 100 150" xmlns="http://www.w3.org/2000/svg">
  <path d="M 50,20 C 30,20 15,35 15,55 C 15,75 30,90 50,90 C 70,90 85,75 85,55 C 85,35 70,20 50,20 Z"
        fill="black"/>
  <path d="M 50,85 L 50,130"
        stroke="black"
        stroke-width="10"
        stroke-linecap="round"/>
</svg>
```

## Character Set

### Currently Supported Characters (via AI)
The base AI model supports:
```
Space, !, ", #, ', (, ), ,, -, .
0-9, :, ;, ?
A-Z (excluding Q, X, Z)
a-z
```

### Expanding the Character Set
Character overrides **allow you to add new characters** not supported by the AI model:
- Upload SVGs for any Unicode character
- Particularly useful for:
  - Accented characters (é, ñ, ü, etc.)
  - Missing letters (Q, X, Z)
  - Special symbols
  - Punctuation

## Troubleshooting

### "Invalid SVG" Error
- Ensure file is valid XML
- Check that viewBox or width/height is present
- Validate SVG using online tools (e.g., https://validator.w3.org/)

### Characters Don't Align
- Adjust the baseline offset parameter
- Ensure consistent viewBox across variants
- Check that character is properly centered in the viewBox

### Characters Look Different from AI Text
- Match the stroke width of AI-generated text (typically 2-3px)
- Keep character height around 100-150px
- Ensure proper scaling in your drawing tool

## Tips for Natural-Looking Results

1. **Study Real Handwriting**: Look at actual handwritten samples for variation
2. **Subtle Variations**: Don't make variants too different; small changes are key
3. **Test Frequently**: Generate samples with your overrides to check alignment
4. **Mix with AI**: You don't need to override every character; mixing creates natural results
5. **Baseline Matters**: Proper baseline alignment is critical for seamless integration

## Advanced: Understanding the Integration

When you enable character overrides during generation:
1. The system scans the input text for characters that have overrides
2. Text is split into chunks around override characters
3. Non-override chunks are generated using the AI model
4. During rendering, override SVGs are inserted at the correct positions
5. The result is seamlessly integrated handwriting with your custom characters

**Implementation Details**:
- Override characters are randomly selected from available variants
- Scaling and positioning are automatically calculated to match generated text
- Baseline offset adjustments ensure proper alignment
- Works with both `write()` and `write_chunked()` methods

## Support

For questions or issues with character overrides:
- Check admin dashboard for collection statistics
- Verify SVG files meet all requirements
- Test with simple characters (like 'a', 'b') first
- Review uploaded character previews in the admin interface

---

Last Updated: 2025-10-22
Version: 1.0.0
