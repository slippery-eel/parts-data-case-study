"""
build_report.py — Step 3 of the Spare Parts MVP
================================================
Reads processed.json (from Step 1) and template.html (from Step 2),
injects the real data, and writes a self-contained report.html.

Run:
  python build_report.py

Output: report.html  — open in any browser, no server needed.
"""

import json
import re
import os

PROCESSED_JSON = "processed.json"
TEMPLATE_HTML  = "template.html"
OUTPUT_HTML    = "report.html"
SOURCE_CSV     = "MM.csv"


def load_data(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_template(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def inject_data(template: str, data: list[dict]) -> str:
    """
    Replaces everything between // DATA_START and // DATA_END
    with a fresh const DATA = <json>;  block.
    """
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    replacement = (
        "// DATA_START\n"
        f"const DATA = {data_json};\n"
        "// DATA_END"
    )
    pattern = r"// DATA_START[\s\S]*?// DATA_END"
    result, n = re.subn(pattern, replacement, template, count=1)
    if n == 0:
        raise ValueError(
            "Could not find DATA_START / DATA_END markers in template.html. "
            "Make sure template.html contains those comments."
        )
    return result


def update_source_tag(html: str, record_count: int) -> str:
    """Update the source tag in the header to reflect real record count."""
    return html.replace(
        "Source: MM.csv",
        f"Source: MM.csv &nbsp;·&nbsp; {record_count} records"
    )


def print_summary(data: list[dict]) -> None:
    total = len(data)
    sku_dups = [r for r in data if r.get("is_duplicate")]
    dup_groups = len(set(r["duplicate_group_id"] for r in sku_dups))
    mp = [r for r in data if r.get("duplicate_type") == "multi_plant"]
    mp_groups = len(set(r["duplicate_group_id"] for r in mp))
    flagged = [r for r in data if r.get("article_is_placeholder")]
    clean = [r for r in data if not r.get("is_duplicate")
             and r.get("duplicate_type") != "multi_plant"
             and not r.get("article_is_placeholder")]

    print(f"\n{'='*55}")
    print("  BUILD REPORT — Step 3")
    print(f"{'='*55}")
    print(f"  Records injected:       {total}")
    print(f"  SKU duplicate records:  {len(sku_dups)} ({dup_groups} clusters)")
    print(f"  Multi-plant records:    {len(mp)} ({mp_groups} groups)")
    print(f"  Flagged records:        {len(flagged)}")
    print(f"  Clean records:          {len(clean)}")
    print(f"{'='*55}\n")


def build(processed_path: str, template_path: str, output_path: str) -> None:
    # 1. Load inputs
    if not os.path.exists(processed_path):
        raise FileNotFoundError(
            f"{processed_path} not found. Run process_data.py first."
        )
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"{template_path} not found.")

    data     = load_data(processed_path)
    template = load_template(template_path)

    # 2. Inject real data
    report = inject_data(template, data)

    # 3. Update source tag with real record count
    report = update_source_tag(report, len(data))

    # 4. Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    size_kb = os.path.getsize(output_path) / 1024
    print_summary(data)
    print(f"  Output:  {output_path}  ({size_kb:.1f} KB)")
    print(f"  -> Open {output_path} in your browser.\n")


if __name__ == "__main__":
    build(PROCESSED_JSON, TEMPLATE_HTML, OUTPUT_HTML)
