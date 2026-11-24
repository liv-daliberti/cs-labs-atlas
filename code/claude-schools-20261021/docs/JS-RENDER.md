# Rendering JavaScript directory pages (`tools/js_render_capture.py`)

For faculty directories whose list is filled in by JavaScript (HKUST ECE, ZJU CAD&CG, NTU EEE shells). Generic: URLs in, captures out; owner decision 2026-11-10.
Prefer first the page's own embedded JSON or its XHR endpoints (Tsinghua EE embeds `qh_data = [...]` in the static HTML and needs no browser); use the browser only when neither exists.

Rules (enforced in code, tested without a browser in `tests/test_js_render_capture.py`): robots.txt of the exact origin is checked before navigation (AI-agent disallows by name and unreadable robots both mean no);
honest user agent, no stealth, a bot-challenge or login marker in the rendered page stops the host (`challenge`/`login`, nothing stored); one URL at a time, >= 3 s apart, a bounded render wait (20 s, DOM stable or `--wait-css`), a page cap;
the rendered DOM and the raw pre-render HTML are both stored in the school's capture store (table `js_render`: sha256 of each, time, raw HTTP status, requested sub-resource URLs, tool/browser/driver versions); only the given URLs; no Wayback.

Environment (not installed system-wide): `scratch/jsrender-venv` (python -m venv from env/atlas, `pip install selenium` = 4.52.0), geckodriver 0.37.1 fetched by Selenium Manager into `scratch/jsrender-venv/cache/geckodriver/linux64/0.37.1/geckodriver` (sha256 f831b7e61454804e8a307edd951bf8a5f373efe3f718e75454a6485a51f6e39f), Firefox 140.17.0esr (/usr/bin/firefox).
Run on a compute node (the login node's sandbox cannot start a browser), e.g. Slurm `-p all --mem=4G --time=00:20:00`:
```
export JSRENDER_GECKODRIVER=<geckodriver> HOME=<scratch dir> PYTHONPATH=scratch/jsrender-venv/lib/python3.12/site-packages
env/atlas/bin/python tools/js_render_capture.py <school> <url> [<url> ...] [--wait-css SEL] [--cap N] [--gap S] [--wait S]
```
Read a capture with `js_render_capture.stored(con, url)` (hashes verified). Parse the rendered DOM with a format in `tools/listing_formats.py` (fixture test) like any listing.
