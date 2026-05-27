"""
process_data.py — Step 1 of the Spare Parts MVP
================================================
Reads DEMO_MM.csv, applies 3 deterministic normalization rules,
and outputs processed.json with new columns added to each row.

New columns added:
  canonical_manufacturer  — normalized OEM name (Rule 1)
  normalized_article      — cleaned article number (Rule 2)
  article_is_placeholder  — True if article is a known dummy value
  is_duplicate            — True if this record is in a matched cluster
  duplicate_group_id      — e.g. "DUP-001" (null if not a duplicate)
  match_rationale         — human-readable explanation of why it matched

Run:
  python process_data.py
"""

import csv
import json
import re
from collections import defaultdict

# ---------------------------------------------------------------------------
# RULE 1 — Manufacturer Name Canonical Lookup Table
# Maps all known variants → a single canonical name.
# Source: manually identified from DEMO_MM.csv analysis.
# ---------------------------------------------------------------------------
MFR_LOOKUP = {
    # Siemens
    "siemens":                          "Siemens",
    "siemens ag":                       "Siemens",
    "simens":                           "Siemens",        # typo in data

    # Balluff
    "balluff":                          "Balluff",
    "balluff gmbh":                     "Balluff",
    "balluf":                           "Balluff",        # typo in data

    # Turck
    "turck":                            "Turck",
    "hans turck gmbh & co. kg":        "Turck",
    "hans turck gmbh & co kg":         "Turck",

    # WAGO
    "wago":                             "WAGO",
    "wago kontakttechnik":              "WAGO",

    # ifm
    "ifm":                              "ifm",
    "ifm electronic":                   "ifm",

    # Rittal
    "rittal":                           "Rittal",
    "rittal gmbh & co. kg":            "Rittal",
    "rittal gmbh & co kg":             "Rittal",

    # MURR
    "murr":                             "MURR",
    "murrelektronik":                   "MURR",

    # SKF
    "skf":                              "SKF",

    # Bosch Rexroth
    "bosch rexroth ag":                 "Bosch Rexroth",
    "bosch rexroth":                    "Bosch Rexroth",

    # Festo
    "festo":                            "Festo",

    # Phoenix Contact
    "phoenix contact":                  "Phoenix Contact",

    # Harting
    "harting":                          "Harting",

    # Norelem
    "norelem":                          "Norelem",

    # SMC
    "smc":                              "SMC",

    # SEW-EURODRIVE
    "sew-eurodrive gmbh & co. kg":     "SEW-EURODRIVE",
    "sew-eurodrive":                    "SEW-EURODRIVE",

    # Pepperl+Fuchs
    "pepperl+fuchs":                    "Pepperl+Fuchs",
    "pepperl + fuchs":                  "Pepperl+Fuchs",

    # Weidmueller
    "weidmueller":                      "Weidmueller",

    # Blickle
    "blickle":                          "Blickle",

    # igus
    "igus":                             "igus",

    # IGUS (caps variant)
    "igus":                             "igus",

    # TUENKERS
    "tuenkers":                         "TUENKERS",

    # RUBIX
    "rubix":                            "RUBIX",

    # Dummy / unknown — keep as-is (will be flagged separately)
    "dummy":                            "UNKNOWN",
}

# Known placeholder article numbers — do NOT match on these
PLACEHOLDER_ARTICLES = {"9999", "0000", "DUMMY", "N/A", "NA", ""}


def canonicalize_manufacturer(raw_name: str) -> str:
    """
    Rule 1: Resolve a raw manufacturer name to its canonical form.
    Falls back to the original (stripped) name if not in the lookup table.
    """
    if not raw_name or not raw_name.strip():
        return "UNKNOWN"
    key = raw_name.strip().lower()
    return MFR_LOOKUP.get(key, raw_name.strip())


def normalize_article(raw_article: str) -> str | None:
    """
    Rule 2: Normalize an article number for comparison.
    - Strip leading/trailing whitespace
    - Uppercase
    - Remove spaces, hyphens, underscores, dots (common formatting variants)
    Returns None if the result is a known placeholder.
    """
    if not raw_article or not raw_article.strip():
        return None
    # Strip and uppercase
    normalized = raw_article.strip().upper()
    # Remove common separator characters
    normalized = re.sub(r"[\s\-_\.]", "", normalized)
    # Check for placeholder
    if normalized in PLACEHOLDER_ARTICLES:
        return None
    return normalized


def describe_normalization_changes(raw_article: str, normalized: str | None) -> list[str]:
    """
    Returns a list of human-readable strings describing what changed
    during normalization. Used to build the match_rationale.
    """
    if normalized is None:
        return ["placeholder value — not matched"]
    changes = []
    stripped = raw_article.strip()
    if stripped != raw_article:
        changes.append("leading/trailing whitespace removed")
    if stripped.upper() != stripped:
        changes.append("uppercased")
    if " " in stripped:
        changes.append("internal spaces removed")
    if re.search(r"[\-_\.]", stripped):
        changes.append("separators (-, _, .) removed")
    return changes


def build_article_rationale(raw_article: str, normalized: str | None) -> str:
    """Produce a short rationale string for the article normalization."""
    changes = describe_normalization_changes(raw_article, normalized)
    if not changes:
        return "no change needed"
    return "; ".join(changes)


# ---------------------------------------------------------------------------
# RULE 3 — Tier 1 Duplicate Detection
# Group by (canonical_manufacturer, normalized_article).
# Only groups with 2+ members are flagged as duplicates.
# ---------------------------------------------------------------------------

def assign_duplicate_groups(records: list[dict]) -> list[dict]:
    """
    Groups records by (canonical_manufacturer, normalized_article).
    Assigns duplicate_group_id and is_duplicate to each record.
    Skips records where normalized_article is None (placeholder).
    """
    groups: dict[tuple, list[int]] = defaultdict(list)

    for idx, rec in enumerate(records):
        canon_mfr = rec["canonical_manufacturer"]
        norm_art = rec["normalized_article"]

        # Skip unknowns and placeholders
        if canon_mfr == "UNKNOWN" or norm_art is None:
            continue

        key = (canon_mfr, norm_art)
        groups[key].append(idx)

    # Assign group IDs only to clusters with 2+ members
    # Distinguish two cases:
    #   "sku_duplicate"  = different material numbers matched to same physical part (THE PROBLEM)
    #   "multi_plant"    = same material number stocked at multiple plants (normal, expected)
    group_counter = 1
    for key, indices in groups.items():
        if len(indices) < 2:
            continue

        canon_mfr, norm_art = key
        material_numbers = set(records[idx]["Material Number"] for idx in indices)

        # If all records share the same material number → this is multi-plant stock, not a duplicate
        if len(material_numbers) == 1:
            dup_type = "multi_plant"
            group_id = f"MP-{group_counter:03d}"
        else:
            dup_type = "sku_duplicate"
            group_id = f"DUP-{group_counter:03d}"

        for idx in indices:
            raw_mfr = records[idx]["Manufacturer Name"]
            raw_art = records[idx]["Manufacturer Article Number"]
            art_changes = build_article_rationale(raw_art, norm_art)
            mfr_changed = raw_mfr.strip() != canon_mfr

            rationale_parts = []
            if mfr_changed:
                rationale_parts.append(
                    f'manufacturer "{raw_mfr.strip()}" -> "{canon_mfr}" (name variant)'
                )
            if art_changes not in ("no change needed",):
                rationale_parts.append(f"article normalized: {art_changes}")
            if not rationale_parts:
                rationale_parts.append("exact match on canonical manufacturer + article")

            records[idx]["is_duplicate"] = (dup_type == "sku_duplicate")
            records[idx]["duplicate_type"] = dup_type
            records[idx]["duplicate_group_id"] = group_id
            records[idx]["match_rationale"] = "; ".join(rationale_parts)
        group_counter += 1

    return records


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_csv(path: str) -> list[dict]:
    """Load CSV, return list of dicts. Handles BOM and strips field names."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            # Strip whitespace from all keys and values
            clean = {k.strip(): v.strip() if isinstance(v, str) else v
                     for k, v in row.items() if k is not None}
            rows.append(clean)
    return rows


def process(csv_path: str, output_path: str) -> None:
    print(f"\n{'='*60}")
    print("  SPARE PARTS DATA PROCESSOR — Step 1")
    print(f"{'='*60}\n")

    records = load_csv(csv_path)
    print(f"Loaded {len(records)} records from {csv_path}\n")

    # Apply Rule 1 & 2 to each record
    for rec in records:
        raw_mfr = rec.get("Manufacturer Name", "")
        raw_art = rec.get("Manufacturer Article Number", "")

        canon_mfr = canonicalize_manufacturer(raw_mfr)
        norm_art = normalize_article(raw_art)

        rec["canonical_manufacturer"] = canon_mfr
        rec["normalized_article"] = norm_art
        rec["article_is_placeholder"] = norm_art is None
        rec["is_duplicate"] = False
        rec["duplicate_type"] = None
        rec["duplicate_group_id"] = None
        rec["match_rationale"] = None

    # Apply Rule 3 — group and flag duplicates
    records = assign_duplicate_groups(records)

    # --- Print summary to terminal ---
    total = len(records)
    sku_dup_records = [r for r in records if r["is_duplicate"]]
    multi_plant_records = [r for r in records if r["duplicate_type"] == "multi_plant"]
    sku_dup_groups = len(set(r["duplicate_group_id"] for r in sku_dup_records))
    multi_plant_groups = len(set(r["duplicate_group_id"] for r in multi_plant_records))
    placeholder_records = [r for r in records if r["article_is_placeholder"]]
    clean_records = [r for r in records
                     if not r["is_duplicate"] and r["duplicate_type"] != "multi_plant"
                     and not r["article_is_placeholder"]]

    print(f"RESULTS SUMMARY")
    print(f"  Total records:                    {total}")
    print(f"  Clean unique records:             {len(clean_records)}")
    print(f"  --- SKU DUPLICATES (the problem) ---")
    print(f"  SKU duplicate clusters:           {sku_dup_groups}")
    print(f"  Records in SKU duplicate groups:  {len(sku_dup_records)}")
    print(f"  --- MULTI-PLANT STOCK (normal) ---")
    print(f"  Multi-plant groups:               {multi_plant_groups}")
    print(f"  Records in multi-plant groups:    {len(multi_plant_records)}")
    print(f"  --- FLAGS ---")
    print(f"  Placeholder articles (no match):  {len(placeholder_records)}")
    print()

    # Print SKU duplicates (the real problem)
    if sku_dup_groups > 0:
        print("SKU DUPLICATE CLUSTERS (different material numbers = same physical part):")
        group_map: dict[str, list[dict]] = defaultdict(list)
        for rec in sku_dup_records:
            group_map[rec["duplicate_group_id"]].append(rec)

        for gid, members in sorted(group_map.items()):
            print(f"\n  {gid}:")
            for m in members:
                print(f"    [{m['Material Number']}]  Plant: {m['Plant']:<14}  "
                      f"Mfr: {m['Manufacturer Name']:<30}  "
                      f"Article: {m['Manufacturer Article Number']}")
            print(f"    -> Matched on: canonical_mfr='{members[0]['canonical_manufacturer']}'  "
                  f"normalized_article='{members[0]['normalized_article']}'")
            print(f"    -> Rationale: {members[0]['match_rationale']}")

    # Print multi-plant groups (informational)
    if multi_plant_groups > 0:
        print(f"\nMULTI-PLANT STOCK GROUPS (same material number, multiple plants -- normal):")
        mp_map: dict[str, list[dict]] = defaultdict(list)
        for rec in multi_plant_records:
            mp_map[rec["duplicate_group_id"]].append(rec)
        for gid, members in sorted(mp_map.items()):
            plants = ", ".join(m["Plant"] for m in members)
            print(f"  {gid}: [{members[0]['Material Number']}]  Plants: {plants}")

    if placeholder_records:
        print(f"\nPLACEHOLDER / SUSPECT RECORDS (article not matched):")
        for rec in placeholder_records:
            print(f"  [{rec['Material Number']}]  Mfr: {rec['Manufacturer Name']:<20}  "
                  f"Article: '{rec['Manufacturer Article Number']}'")

    # Write output JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"\nOutput written to: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    process("MM.csv", "processed.json")
