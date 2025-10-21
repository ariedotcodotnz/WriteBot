## WriteBot – Realistic Handwriting Synthesis (TensorFlow 2)

WriteBot converts digital text into realistic handwritten SVGs using an RNN with attention (inspired by Alex Graves' "Generating Sequences with Recurrent Neural Networks"). This repository packages the model, a Python API, a CLI for batch generation, and a local web app for interactive use. A pretrained model is included, so you can generate handwriting immediately.

### Key Features

- 13 handwriting styles (priming)
- Neatness control via bias
- Per-line stroke colors and widths
- Page size, margins, orientation, alignment, line height, background
- Canvas-aware word wrapping with a hard cap of 75 characters per line
- Optional legibility mode, horizontal stretch, and denoising
- REST API and interactive web UI
- Batch CSV processing (CLI and streaming UI)

---

## Quick Start

Prerequisites:
- Python 3.10 or 3.11 (TensorFlow 2.12 compatible)
- Windows 10/11, macOS, or Linux

Setup:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

Generate a quick sample (Python API):
```python
from handwriting_synthesis.hand.Hand import Hand

hand = Hand()
hand.write(
    filename='sample.svg',
    lines=[
        "Father time, I'm running late",
        "I'm winding down, I'm growing tired",
        "Seconds drift into the night",
        "The clock just ticks till my time expires",
    ],
    biases=[0.75, 0.75, 0.75, 0.75],
    styles=[9, 9, 9, 9],
)
```

Open `sample.svg` in a browser or vector editor.

---

## Web App (Local UI)

Run the Flask server:
```bash
python webapp/app.py
```

Then open `http://localhost:5000` and use the UI to generate SVGs, adjust parameters, and export.

Optional: build a minified, hashed frontend (requires Node.js):
```bash
cd webapp
npm install
npm run build
# Restart the Flask app; it will serve the built file under webapp/dist/
```

---

## REST API

The server exposes two main endpoints. Start it with `python webapp/app.py`.

- POST `/api/generate` → returns raw SVG (Content-Type: image/svg+xml)
- POST `/api/v1/generate` → returns JSON: `{ "svg": "<svg...>", "meta": {...} }`

Example request:
```bash
curl -sS http://localhost:5000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from WriteBot!",
    "page_size": "A4",
    "units": "mm",
    "margins": 20,
    "biases": [0.75],
    "styles": [9],
    "legibility": "normal",
    "x_stretch": 1.0,
    "denoise": true
  }'
```

Accepted fields (all optional unless noted):
- Required content: one of `text` (string with newlines) or `lines` (array of strings)
- Styling per line: `biases: number[]`, `styles: number[]`, `stroke_colors: string[]`, `stroke_widths: number[]`
- Page: `page_size: "A5"|"A4"|"Letter"|"Legal"|"custom"`, `units: "mm"|"px"`, `page_width`, `page_height`, `orientation: "portrait"|"landscape"`
- Layout: `margins` (number | [t,r,b,l] | {top,right,bottom,left}), `line_height`, `align: "left"|"center"|"right"`, `background`, `global_scale`
- Wrapping: `wrap_char_px`, `wrap_ratio`, `wrap_utilization`
- Rendering: `legibility: "natural"|"normal"|"high"`, `x_stretch`, `denoise: true|false`

Note: Lines are hard-limited to 75 characters. The service performs canvas-aware wrapping to respect this.

---

## Batch Generation

### CLI (CSV → SVGs)

```bash
python scripts/batch_generate.py path/to/input.csv --out-dir out
```

CSV columns (header row), all optional unless noted:
```
filename,text,page_size,units,page_width,page_height,margins,line_height,align,background,global_scale,orientation,biases,styles,stroke_colors,stroke_widths,wrap_char_px,wrap_ratio,wrap_utilization,legibility,x_stretch,denoise
```

Examples:
```
filename,text,biases,styles,stroke_colors,stroke_widths,page_size,units,margins,align
note.svg,"Hello world",0.75,9,black,2,A4,mm,20,left
poem.svg,"Roses are red\nViolets are blue",0.7|0.8,9|9,black|#333,2|2,Letter,mm,15,center
```

### Web UI (streaming batch)

Use the "Batch CSV" section in the UI. The server streams per-row status and provides a ZIP download on completion.

---

## Sample CSVs

Quick demo CSVs are included under `samples/`:

- `samples/batch_basic.csv` – Minimal fields, just `text` and `styles`
- `samples/batch_full.csv` – Demonstrates most options including custom page sizes
- `samples/batch_edge_cases.csv` – Tests empty/partial list values and long wrapping

Download via UI or test via CLI:

```bash
curl -F "file=@samples/batch_basic.csv" http://localhost:5000/api/batch -o writebot_batch.zip
```

You can also stream progress via the UI's batch section.

## Python API

```python
from handwriting_synthesis.hand.Hand import Hand

hand = Hand()
hand.write(
    filename='out.svg',
    lines=["Hello", "from", "WriteBot"],
    biases=[0.75, 0.75, 0.75],        # optional per-line
    styles=[9, 9, 9],                  # optional per-line (0–12)
    stroke_colors=['black','black','black'],
    stroke_widths=[2,2,2],
    page_size='A4', units='mm',
    margins=20,                        # number | [t,r,b,l] | {top,right,bottom,left}
    line_height=None, align='left',
    background=None, global_scale=1.0,
    orientation='portrait',
    legibility='normal',               # 'natural' | 'normal' | 'high'
    x_stretch=1.0, denoise=True,
)
```

Rules and validation:
- Characters must be in the model alphabet (A–Z excluding some letters, a–z, digits, punctuation in `handwriting_synthesis.drawing.operations.alphabet`).
- Each line must be ≤ 75 characters. Provide multiple lines or let the web/REST layer wrap for you.
- Per-line arrays can be length 1 (broadcast) or match the number of lines.

---

## Training a Model (Optional)

This repo includes a pretrained checkpoint under `model/checkpoint/` and style priming data under `model/style/`.
To train your own model, see `model/README.md` for dataset preparation and training instructions.

---

## Project Structure

```
WriteBot/
├── handwriting_synthesis/     # Core model, drawing, and utilities
├── model/                     # Pretrained checkpoint and style data
├── webapp/                    # Flask app and frontend (static and build script)
├── scripts/                   # Utilities (e.g., CSV batch generator)
├── main.py                    # Small demo using the API
├── requirements.txt           # Python dependencies
├── config.json                # App defaults (reference)
├── README.md                  # This file
└── LICENSE.txt                # MIT License
```