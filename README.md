# Spare Parts Master Data — Deduplication Pipeline

A data PM case study built for SPARETECH. The problem: a 4,203-record Material Master where the same physical part is identified differently across 7 plants, creating SKU duplicates that inflate inventory counts, trigger false reorder signals, and distort procurement spend. The output is an interactive HTML report that runs in any browser with no server.

**[Live report → `report.html`](report.html)**

---

## The Problem

| Category | Count |
|---|---|
| Total records | 4,203 |
| SKU duplicate records | 1,111 (471 clusters) |
| Placeholder article numbers | 591 |
| Clean unique records | 2,473 |

SKU duplicates are records with **different material numbers that map to the same physical part** — caused by inconsistent manufacturer name formatting, article number formatting differences, and no cross-plant deduplication at point of entry. They are distinct from multi-plant stock (same material number at multiple plants), which is expected and must not be collapsed.

---

## Matching Pipeline

Three deterministic rules, applied in sequence by `process_data.py`:

1. **Manufacturer canonicalization** — a hand-built lookup table (`MFR_LOOKUP`) maps all known name variants to a single canonical form (`"Balluf"` → `"Balluff"`, `"Siemens AG"` → `"Siemens"`, etc.)
2. **Article number normalization** — strip whitespace, uppercase, remove spaces/hyphens/dots/underscores. Known placeholder values (`"9999"`, `"N/A"`, `""`) return `null` and are never matched.
3. **Tier 1 exact matching** — records sharing the same `(canonical_manufacturer, normalized_article)` pair are grouped. Groups where all members share the same Material Number are classified `multi_plant` (normal). Groups with differing Material Numbers are classified `sku_duplicate` (the problem).

Each matched record gets 7 derived fields: `canonical_manufacturer`, `normalized_article`, `article_is_placeholder`, `is_duplicate`, `duplicate_type`, `duplicate_group_id`, `match_rationale`.

### Planned tiers (Phases 2–3)

| Tier | Method | Confidence | Action |
|---|---|---|---|
| Tier 1: Exact | Canonical manufacturer + normalized article | 100 (deterministic) | Auto-confirmed |
| Tier 2: Fuzzy | GTIN lookup, type-code match, high-similarity article | 70–99 (scored) | Auto-confirmed above threshold |
| Tier 3: Semantic | Description similarity, partial article overlap | 40–69 (scored) | Human review queue |

---

## Files

| File | Role |
|---|---|
| `MM.csv` | Source data — 4,203 records, 41 columns |
| `DEMO_MM.csv` | 100-row sample used during development |
| `process_data.py` | Normalization + Tier 1 matching → `processed.json` |
| `build_report.py` | Injects `processed.json` into the HTML shell → `report.html` |
| `processed.json` | Intermediate output — original fields + 7 derived fields per record |
| `report.html` | Final deliverable — self-contained, open directly in a browser |

---

## Running the Pipeline

```bash
python process_data.py   # reads MM.csv → writes processed.json
python build_report.py   # reads processed.json → writes report.html
```

Requires Python 3.10+. No dependencies beyond the standard library.

---

## The Report

`report.html` is a single self-contained file with two tabs:

- **Case Study** — written document covering the problem, strategy, matching tier definitions, 4-phase execution plan, and assumptions/open questions
- **Prototype** — interactive table of all 4,203 records with filter buttons (All / SKU Duplicates / Multi-Plant / Placeholders / Clean), column sorting, and a row detail panel showing all original fields alongside the 7 derived normalization outputs

No server, no database, no build step — open the file directly in any browser.
