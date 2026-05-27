# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Pipeline

This is a two-step data pipeline that produces a self-contained HTML report. Always run in order:

```bash
python process_data.py   # reads MM.csv → writes processed.json
python build_report.py   # reads processed.json + template.html → writes report.html
```

To regenerate the report after any change to `template.html` or `process_data.py`, re-run both steps. `report.html` is the final deliverable — open it directly in a browser, no server needed.

## Architecture

| File | Role |
|---|---|
| `MM.csv` | Source data — 4,203 spare parts records, 41 columns |
| `DEMO_MM.csv` | 100-row sample used during development |
| `process_data.py` | All matching logic: normalization + duplicate detection → `processed.json` |
| `template.html` | Two-tab HTML shell with embedded mock data (9 rows). JS renders the table from `const DATA`. |
| `build_report.py` | Replaces the `// DATA_START … // DATA_END` block in `template.html` with real JSON from `processed.json` |
| `processed.json` | Intermediate output — original fields + 7 derived fields per record |
| `report.html` | Generated final output — never edit directly |

## Matching Logic (`process_data.py`)

Three deterministic rules, applied in sequence:

1. **Rule 1 — Manufacturer canonicalization**: `MFR_LOOKUP` dict maps all known name variants to a canonical name. Add new mappings here when new variants are discovered.
2. **Rule 2 — Article normalization**: `.strip().upper()` then `re.sub(r"[\s\-_\.]", "", ...)`. Values in `PLACEHOLDER_ARTICLES` (e.g. `"9999"`) return `None` and are never matched.
3. **Rule 3 — Tier 1 grouping**: Records sharing `(canonical_manufacturer, normalized_article)` are grouped. Groups where all members share the same `Material Number` are classified `"multi_plant"` (normal). Groups with differing `Material Number` values are classified `"sku_duplicate"` (the problem).

The 7 fields added to each record: `canonical_manufacturer`, `normalized_article`, `article_is_placeholder`, `is_duplicate`, `duplicate_type`, `duplicate_group_id`, `match_rationale`.

## Data Injection Pattern

`build_report.py` uses a regex to replace the data block in `template.html`:

```
// DATA_START
const DATA = [...];
// DATA_END
```

If you restructure `template.html`, keep these exact comment markers or update the regex in `build_report.py → inject_data()`.

## Two-Tab UI (`template.html`)

- **Tab 1 "Case Study"** — static written document, always shown first. Stats are hardcoded prose; they do not auto-compute from `DATA`.
- **Tab 2 "Prototype"** — interactive table. Stats strip, filter buttons, and filter button labels all compute live from the `DATA` array via `computeStats()` and `renderStats()`.
- Tab switching: `showTab('casestudy')` / `showTab('prototype')` — wires to `id="tab-*"` panels and `id="btn-*"` nav buttons.
- Sticky header: `thead tr.grp-row th` sticks at `top:0`, `thead tr.col-row th` sticks at `top:27px` inside `.table-scroll` which has `overflow-y:auto; max-height:calc(100vh - 340px)`.
