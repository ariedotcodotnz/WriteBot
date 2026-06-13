# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

WriteBot turns digital text into realistic handwritten SVG/PDF using a trained TensorFlow RNN. There are two layers:

- `handwriting_synthesis/` — the ML engine: model loading, RNN stroke generation, and layout → SVG. No Flask dependency; usable standalone.
- `webapp/` — a multi-user Flask app (auth, batch jobs, character overrides, admin, usage stats) wrapping the engine.

## Commands

Python 3.10 in CI (local `.venv` is 3.11). `pip install -r requirements.txt` pulls TensorFlow + CUDA and is large.

Run the app:
- Dev: `python webapp/app.py` — Flask dev server on port 5000, **single-threaded by design** (see model note below).
- Full stack: `docker compose up` — gunicorn (`webapp.app:app`), a Celery worker, Celery beat, Redis, and nginx. The Docker entrypoint runs `python webapp/init_db.py --auto` first to create/seed the DB.

Tests (model-free, fast — these are the only automated tests):
- All: `python tests/test_operations.py` or `pytest tests/test_operations.py`
- One: `pytest tests/test_operations.py::test_balanced_breaks_at_punctuation`
- They cover `handwriting_synthesis/hand/operations/chunking.py`. Anything that touches `Hand` needs the model checkpoint and is slow, so it is not in the suite.

Lint (as CI runs it): `flake8 webapp --select=E9,F63,F7,F82` (hard gate on syntax/undefined names) and `pylint $(git ls-files '*.py')`.

DB migrations (Flask-Migrate/Alembic, `migrations/`): `FLASK_APP=webapp.app:app flask db migrate -m "..."` then `flask db upgrade`.

CLI batch generation: `python scripts/batch_generate.py` (see `test_batch.csv` for the expected column layout).

## The model — read before changing any generation code

- `Hand()` (`handwriting_synthesis/hand/Hand.py`) builds a `tf.compat.v1` graph and restores a checkpoint (`model/checkpoint/model-17900.*`) plus style-priming arrays (`model/style/style-N-*.npy`). Construction is expensive and the TF session is effectively a **process-global singleton**: route modules instantiate `hand = Hand()` at import time, and `webapp/tasks.py` caches a single lazy `_hand_instance`. This is why the dev server is single-threaded and the Celery worker runs `-P solo --concurrency 1`. Do not assume concurrent calls are safe.
- The model only understands a fixed, restricted ASCII alphabet (`handwriting_synthesis/drawing/operations.py: alphabet`). Input must be normalized to it via `webapp/utils/text_utils.py: normalize_text_for_model` before generation. Limits: `MAX_CHAR_LEN=120` per line, `MAX_STROKE_LEN=2400`. Retraining is out of scope — improvements happen at the chunking / stitching / layout level, not the weights.

## Generation pipeline (the part that requires reading several files)

1. `webapp/routes/{generation,batch,job}_routes.py` receive a request with 30+ parameters.
2. `webapp/utils/generation_utils.py`: `parse_generation_params()` normalizes them; `generate_handwriting_to_file()` dispatches.
3. Text is normalized to the model alphabet. In **non-chunked** mode it is also wrapped to the page width by `text_processor.py` (`TextProcessor`, via `text_utils.wrap_by_canvas`).
4. `Hand.write()` (one RNN sample per line) or `Hand.write_chunked()` (the default) runs. Chunked mode splits each line into small chunks, samples each, and stitches them into lines using **measured** stroke widths — better line filling and shorter RNN sequences. The stages map to `operations/`: `chunking.py` (text → chunks), `sampling.py` (RNN inference), `stroke_ops.py` (stitch / baseline / rotation).
5. `handwriting_synthesis/hand/_draw.py: _draw()` does all page layout: unit conversion (`PX_PER_MM = 96/25.4`), auto-sizing strokes to fit the content box, alignment, line-height, baseline/margin jitter, and SVG emission via `svgwrite`.

Chunked vs non-chunked is the `use_chunked` flag (default true). Generation defaults (chunking strategy, words/chars per chunk, page, style/bias) live in `config.json` under `defaults`.

## Character overrides ("character insert")

Users upload custom SVG glyphs for specific characters that get injected into otherwise model-generated handwriting. Persisted as `CharacterOverride` / `CharacterOverrideCollection` (`webapp/models.py`); helpers in `handwriting_synthesis/hand/character_override_utils.py`; rendered in `_draw.py`'s override path. The current approach generates the line with placeholder spaces, then uses the model's attention `char_indices` to cut the strokes precisely and shift them to open a gap for the inserted glyph (`_render_strokes_with_overrides`, `override_positions`). Override characters are exempt from alphabet validation. This subsystem is intricate and changes often — trace the `char_indices` / `override_positions` flow end-to-end before modifying it. Uploaded SVG is untrusted input.

## Web app layout

- Entry: `webapp/app.py` (`webapp.app:app`); Flask extensions in `webapp/extensions.py`; SQLAlchemy models in `webapp/models.py` (User, CharacterOverride(Collection), BatchJob, PageSize/TemplatePreset, Usage/Activity).
- Routes are split by concern under `webapp/routes/`; reusable logic lives in `webapp/utils/` (`generation_utils`, `text_utils`, `page_utils`, `secure_urls`, `auth_utils`).
- Async/batch work goes through Celery (`webapp/celery_app.py`, `webapp/tasks.py`, Redis broker) and the `BatchJob` model.
- Runtime config comes from env (`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, Sentry, mail) — see `.env.example`.

## Gotchas

- Page geometry is computed in pixels internally but user-facing values may be mm or px (`units`). `PX_PER_MM` and the paper-size table are defined in **both** `_draw.py` and `webapp/utils/page_utils.py` — keep them consistent.
- `legibility` (`high` | `normal` | `natural`) sets jitter/interpolation defaults in `_draw.py`; `high` disables all randomness, which is what you want for deterministic output or tests.
- The RNN/TF code (`handwriting_synthesis/{rnn,tf}/`) uses graph-mode `tf.compat.v1` and legacy Keras (`tf-keras`, `TF_USE_LEGACY_KERAS=1`); it is not idiomatic TF2.
