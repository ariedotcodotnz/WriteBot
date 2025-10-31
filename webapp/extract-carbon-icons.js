/**
 * Script to extract Carbon Design System icons as SVG strings
 * This helps us generate the SVG code to use directly in HTML templates
 */

const { getAttributes, toString } = require('@carbon/icon-helpers');

// Import icons we need
const ChevronDown = require('@carbon/icons/lib/chevron--down/16');
const Download = require('@carbon/icons/lib/download/16');
const Document = require('@carbon/icons/lib/document/16');
const Copy = require('@carbon/icons/lib/copy/16');
const DocumentBlank = require('@carbon/icons/lib/document--blank/16');
const DocumentAdd = require('@carbon/icons/lib/document--add/16');
const TrashCan = require('@carbon/icons/lib/trash-can/16');
const Close = require('@carbon/icons/lib/close/24');
const DataBase = require('@carbon/icons/lib/data--base/32');
const CSV = require('@carbon/icons/lib/CSV/32');
const Save = require('@carbon/icons/lib/save/16');

// Helper function to generate SVG with custom attributes
function generateSVG(icon, customAttrs = {}) {
  const attrs = getAttributes({
    ...icon.attrs,
    ...customAttrs
  });

  return toString({
    ...icon,
    attrs
  });
}

// Generate icons with standard styling
console.log('=== CHEVRON DOWN (for dropdowns) ===');
console.log(generateSVG(ChevronDown, {
  class: 'bx--select__arrow',
  width: '10',
  height: '6'
}));

console.log('\n=== DOWNLOAD (for download buttons) ===');
console.log(generateSVG(Download, {
  width: '16',
  height: '16',
  fill: 'currentColor',
  style: 'margin-right: 0.5rem;'
}));

console.log('\n=== SAVE (for generate button) ===');
console.log(generateSVG(Save, {
  width: '16',
  height: '16',
  fill: 'currentColor',
  style: 'margin-right: 0.5rem;'
}));

console.log('\n=== DOCUMENT (for page format buttons) ===');
console.log(generateSVG(Document, {
  width: '14',
  height: '14',
  fill: 'currentColor',
  style: 'margin-right: 0.25rem;'
}));

console.log('\n=== COPY (for copy button) ===');
console.log(generateSVG(Copy, {
  width: '16',
  height: '16',
  fill: 'currentColor',
  style: 'margin-right: 0.5rem;'
}));

console.log('\n=== CSV (for CSV dropzone) ===');
console.log(generateSVG(CSV, {
  width: '48',
  height: '48',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '1.5'
}));

console.log('\n=== DOCUMENT-ADD (for batch processing) ===');
console.log(generateSVG(DocumentAdd, {
  width: '16',
  height: '16',
  fill: 'currentColor',
  style: 'margin-right: 0.5rem;'
}));

console.log('\n=== TRASH-CAN (for clear button) ===');
console.log(generateSVG(TrashCan, {
  width: '16',
  height: '16',
  fill: 'currentColor',
  style: 'margin-right: 0.25rem;'
}));

console.log('\n=== CLOSE (for lightbox) ===');
console.log(generateSVG(Close, {
  width: '24',
  height: '24',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
}));
