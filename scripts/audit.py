#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a retagged sidecar TSV.")
    parser.add_argument("input", help="Input TSV from scripts/retag.py")
    parser.add_argument("--output", help="Optional report path")
    return parser.parse_args()


def format_counter(title: str, counter: Counter[str], limit: int | None = None) -> list[str]:
    lines = [title]
    items = counter.most_common(limit)
    if not items:
        lines.append("  (none)")
        return lines
    for key, value in items:
        lines.append(f"  {value}\t{key}")
    return lines


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)

    total_rows = 0
    review_rows = 0
    category_counts: Counter[str] = Counter()
    subtype_counts: Counter[str] = Counter()
    rule_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    review_signatures: Counter[str] = Counter()

    with input_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            total_rows += 1
            source_counts[row["source_file"]] += 1
            category_counts[row["br_cat"] or "UNRESOLVED"] += 1
            subtype_counts[row["br_subtype"] or "UNSPECIFIED"] += 1
            rule_counts[row["rule_id"]] += 1
            if row["needs_review"].strip().lower() == "true":
                review_rows += 1
                signature = "\t".join([row["lemma"], row["ud_upos"], row["ud_deprel"], row["rule_id"]])
                review_signatures[signature] += 1

    auto_rows = total_rows - review_rows
    lines = [
        f"Input: {input_path}",
        f"Rows: {total_rows}",
        f"Auto rows: {auto_rows}",
        f"Review rows: {review_rows}",
        "",
    ]
    lines.extend(format_counter("By source file:", source_counts))
    lines.append("")
    lines.extend(format_counter("By category:", category_counts))
    lines.append("")
    lines.extend(format_counter("By subtype:", subtype_counts))
    lines.append("")
    lines.extend(format_counter("By rule:", rule_counts))
    lines.append("")
    lines.extend(format_counter("Top review signatures (lemma, UPOS, DEPREL, rule_id):", review_signatures, limit=20))
    report = "\n".join(lines) + "\n"

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
