# Spare Parts MVP — Build Plan

Self-contained web report that shows all 100 parts with original + normalized columns and Tier 1 duplicate matching. No server. Open `report.html` in any browser.

**Matching logic (confident heuristics only):**
- Rule 1: Manufacturer name canonicalization (lookup table)
- Rule 2: Article number normalization (strip spaces, case, hyphens)
- Rule 3: Tier 1 duplicate grouping (canonical_mfr + normalized_article)

---

## Steps

- [x] **Step 1 — `process_data.py`**: Read DEMO_MM.csv, apply all 3 rules, output `processed.json`. Review: run script, check terminal output + JSON file for correct duplicate clusters.

- [x] **Step 2 — `template.html`**: Visual shell with layout, stats strip, logic explainer panel, filter bar, and table column groups (original / normalized / match result). Review: open in browser with mock data.

- [x] **Step 3 — `build_report.py`**: Inject real data from `processed.json` into template, write self-contained `report.html`. Review: open `report.html` with live data, verify clusters are colored and stats are accurate.

- [x] **Step 4 — Polish**: Sortable columns, sticky header, switched to MM.csv (4,203 records). Review: walk through as first-time user.

---

## File Map

```
parts-data-case-study/
├── DEMO_MM.csv              ← source data (existing)
├── plan.md                  ← this file
├── process_data.py          ← Step 1
├── processed.json           ← Step 1 output
├── template.html            ← Step 2
├── build_report.py          ← Step 3
└── report.html              ← Step 3 output (final deliverable)
```

---

## Out of Scope (MVP)

- Fuzzy / semantic matching
- Supplier cross-reference
- Backend server or database
- Editing / confirming matches in UI
- Full MM.csv (100-row demo only)
