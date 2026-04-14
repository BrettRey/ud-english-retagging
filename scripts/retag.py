#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List


BASE_TARGET_UPOS = {"DET", "PRON"}
OUTPUT_FIELDS = [
    "source_file",
    "sent_id",
    "token_id",
    "form",
    "lemma",
    "ud_upos",
    "ud_xpos",
    "ud_feats",
    "ud_head",
    "ud_deprel",
    "ud_deps",
    "ud_misc",
    "br_cat",
    "br_subtype",
    "br_status",
    "needs_review",
    "rule_id",
    "rule_notes",
]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    priority: int
    form_pattern: str
    lemma_pattern: str
    upos_pattern: str
    deprel_pattern: str
    feats_pattern: str
    head_lemma_pattern: str
    head_upos_pattern: str
    head_feats_pattern: str
    br_cat: str
    br_subtype: str
    needs_review: bool
    notes: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retag UD tokens into a CGEL-aligned sidecar TSV.")
    parser.add_argument("inputs", nargs="+", help="CoNLL-U files or directories containing .conllu files")
    parser.add_argument("--rules", required=True, help="CSV rule table")
    parser.add_argument("--output", required=True, help="Output TSV path")
    parser.add_argument(
        "--include-text",
        action="store_true",
        help="Include sentence_text in the TSV for manual review workflows",
    )
    return parser.parse_args()


def iter_input_files(inputs: List[str]) -> Iterator[Path]:
    files: List[Path] = []
    for raw in inputs:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(p for p in path.glob("*.conllu") if p.is_file()))
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(f"Input path not found: {raw}")
    seen = set()
    for path in files:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        yield path


def parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def load_rules(path: Path) -> List[Rule]:
    rules: List[Rule] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rules.append(
                Rule(
                    rule_id=row["rule_id"],
                    priority=int(row["priority"]),
                    form_pattern=row.get("form_pattern", "*"),
                    lemma_pattern=row["lemma_pattern"],
                    upos_pattern=row["ud_upos_pattern"],
                    deprel_pattern=row["ud_deprel_pattern"],
                    feats_pattern=row.get("ud_feats_pattern", "*"),
                    head_lemma_pattern=row.get("ud_head_lemma_pattern", "*"),
                    head_upos_pattern=row.get("ud_head_upos_pattern", "*"),
                    head_feats_pattern=row.get("ud_head_feats_pattern", "*"),
                    br_cat=row["br_cat"],
                    br_subtype=row["br_subtype"],
                    needs_review=parse_bool(row["needs_review"]),
                    notes=row["notes"],
                )
            )
    return sorted(rules, key=lambda rule: rule.priority, reverse=True)


def pattern_matches(pattern: str, value: str) -> bool:
    normalized_value = value.casefold()
    for option in pattern.casefold().split("|"):
        option = option.strip()
        if not option or option == "*":
            return True
        if option.startswith("*") and option.endswith("*") and len(option) > 2:
            if option.strip("*") in normalized_value:
                return True
        if option.endswith("*") and normalized_value.startswith(option[:-1]):
            return True
        if option.startswith("*") and normalized_value.endswith(option[1:]):
            return True
        if option == normalized_value:
            return True
    return False


def parse_misc_fields(raw_misc: str) -> Dict[str, str]:
    if not raw_misc or raw_misc == "_":
        return {}
    fields: Dict[str, str] = {}
    for field in raw_misc.split("|"):
        if "=" not in field:
            continue
        key, value = field.split("=", 1)
        fields[key] = value
    return fields


def normalized_hint(value: str) -> str:
    if not value or value in {"_", "*LOWER*"}:
        return ""
    return value


def effective_form(token: Dict[str, str]) -> str:
    form = token.get("form", "")
    if form and form != "_":
        return form
    misc_fields = parse_misc_fields(token.get("misc", ""))
    corrected_form = normalized_hint(misc_fields.get("CorrectForm", ""))
    if corrected_form:
        return corrected_form
    lemma_hint = normalized_hint(misc_fields.get("Lem", ""))
    if lemma_hint:
        return lemma_hint
    return form


def effective_lemma(token: Dict[str, str]) -> str:
    lemma = token.get("lemma", "")
    if lemma and lemma != "_":
        return lemma
    misc_fields = parse_misc_fields(token.get("misc", ""))
    lemma_hint = normalized_hint(misc_fields.get("Lem", ""))
    if lemma_hint:
        return lemma_hint
    if misc_fields.get("Lem") == "*LOWER*":
        form = token.get("form", "")
        if form and form != "_":
            return form.casefold()
    corrected_form = normalized_hint(misc_fields.get("CorrectForm", ""))
    if corrected_form:
        return corrected_form
    form = token.get("form", "")
    if form and form != "_":
        return form
    return lemma


def has_ref_dependency(deps: str) -> bool:
    if not deps or deps == "_":
        return False
    for dependency in deps.split("|"):
        if ":" not in dependency:
            continue
        _, relation = dependency.split(":", 1)
        if relation.split(":", 1)[0] == "ref":
            return True
    return False


def build_head_match_context(head_token: Dict[str, str], grandparent_token: Dict[str, str]) -> str:
    head_feats = head_token.get("feats", "")
    head_deprel = head_token.get("deprel", "")
    context = head_feats
    if head_deprel:
        context = f"{context};HeadDeprel={head_deprel}" if context else f"HeadDeprel={head_deprel}"
    grandparent_deprel = grandparent_token.get("deprel", "")
    if grandparent_deprel:
        context = (
            f"{context};GrandparentDeprel={grandparent_deprel}"
            if context
            else f"GrandparentDeprel={grandparent_deprel}"
        )
    return context


def build_token_match_context(token: Dict[str, str], next_token: Dict[str, str]) -> str:
    misc_fields = parse_misc_fields(token.get("misc", ""))
    parts: List[str] = []
    token_feats = token.get("feats", "")
    if token_feats and token_feats != "_":
        parts.append(token_feats)
    xpos = token.get("xpos", "")
    if xpos and xpos != "_":
        parts.append(f"XPOS={xpos}")
    length = normalized_hint(misc_fields.get("Len", ""))
    if length:
        parts.append(f"Len={length}")
    if has_ref_dependency(token.get("deps", "")):
        parts.append("HasRef=yes")
    lemma_hint = normalized_hint(misc_fields.get("Lem", ""))
    if lemma_hint:
        parts.append(f"Lem={lemma_hint}")
    corrected_form = normalized_hint(misc_fields.get("CorrectForm", ""))
    if corrected_form:
        parts.append(f"CorrectForm={corrected_form}")
    mseg = normalized_hint(misc_fields.get("MSeg", ""))
    if mseg:
        parts.append(f"MSeg={mseg}")
    deps = token.get("deps", "")
    if deps and deps != "_":
        parts.append(f"Deps={deps}")
    next_lemma = effective_lemma(next_token)
    if next_lemma and next_lemma != "_":
        parts.append(f"NextLemma={next_lemma}")
    return ";".join(parts)


def apply_rules(
    token: Dict[str, str],
    sentence_tokens: Dict[str, Dict[str, str]],
    rules: Iterable[Rule],
) -> Rule | None:
    form = effective_form(token)
    lemma = effective_lemma(token)
    upos = token["upos"]
    deprel = token["deprel"]
    next_token = sentence_tokens.get(str(int(token["id"]) + 1), {})
    feats = build_token_match_context(token, next_token)
    head_token = sentence_tokens.get(token["head"], {})
    grandparent_token = sentence_tokens.get(head_token.get("head", ""), {})
    head_lemma = effective_lemma(head_token)
    head_upos = head_token.get("upos", "")
    head_feats = build_head_match_context(head_token, grandparent_token)
    for rule in rules:
        if (
            pattern_matches(rule.form_pattern, form)
            and pattern_matches(rule.lemma_pattern, lemma)
            and pattern_matches(rule.upos_pattern, upos)
            and pattern_matches(rule.deprel_pattern, deprel)
            and pattern_matches(rule.feats_pattern, feats)
            and pattern_matches(rule.head_lemma_pattern, head_lemma)
            and pattern_matches(rule.head_upos_pattern, head_upos)
            and pattern_matches(rule.head_feats_pattern, head_feats)
        ):
            return rule
    return None


def parse_conllu(path: Path) -> Iterator[Dict[str, object]]:
    metadata: Dict[str, str] = {}
    tokens: List[Dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\n")
            if not line:
                if tokens or metadata:
                    yield {"metadata": metadata, "tokens": tokens}
                metadata = {}
                tokens = []
                continue
            if line.startswith("#"):
                content = line[1:].strip()
                if " = " in content:
                    key, value = content.split(" = ", 1)
                    metadata[key] = value
                continue
            columns = line.split("\t")
            if len(columns) != 10:
                raise ValueError(f"{path}:{line_number}: expected 10 columns, found {len(columns)}")
            token_id = columns[0]
            if "-" in token_id or "." in token_id:
                continue
            tokens.append(
                {
                    "id": columns[0],
                    "form": columns[1],
                    "lemma": columns[2],
                    "upos": columns[3],
                    "xpos": columns[4],
                    "feats": columns[5],
                    "head": columns[6],
                    "deprel": columns[7],
                    "deps": columns[8],
                    "misc": columns[9],
                }
            )
    if tokens or metadata:
        yield {"metadata": metadata, "tokens": tokens}


def build_output_fields(include_text: bool) -> List[str]:
    fields = OUTPUT_FIELDS.copy()
    if include_text:
        fields.insert(2, "sentence_text")
    return fields


def row_from_token(
    source_file: str,
    sent_id: str,
    sentence_text: str,
    token: Dict[str, str],
    rule: Rule | None,
    include_text: bool,
) -> Dict[str, str]:
    if rule is None:
        br_cat = ""
        br_subtype = ""
        br_status = "review"
        needs_review = "true"
        rule_id = "no-rule"
        notes = "No matching rule"
    else:
        br_cat = rule.br_cat
        br_subtype = rule.br_subtype
        br_status = "review" if rule.needs_review or not br_cat else "auto"
        needs_review = "true" if rule.needs_review or not br_cat else "false"
        rule_id = rule.rule_id
        notes = rule.notes
    row = {
        "source_file": source_file,
        "sent_id": sent_id,
        "token_id": token["id"],
        "form": token["form"],
        "lemma": token["lemma"],
        "ud_upos": token["upos"],
        "ud_xpos": token["xpos"],
        "ud_feats": token["feats"],
        "ud_head": token["head"],
        "ud_deprel": token["deprel"],
        "ud_deps": token["deps"],
        "ud_misc": token["misc"],
        "br_cat": br_cat,
        "br_subtype": br_subtype,
        "br_status": br_status,
        "needs_review": needs_review,
        "rule_id": rule_id,
        "rule_notes": notes,
    }
    if include_text:
        row["sentence_text"] = sentence_text
    return row


def main() -> None:
    args = parse_args()
    rules = load_rules(Path(args.rules))
    input_files = list(iter_input_files(args.inputs))
    output_path = Path(args.output)
    output_fields = build_output_fields(args.include_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields, delimiter="\t")
        writer.writeheader()
        for input_path in input_files:
            for sentence in parse_conllu(input_path):
                metadata = sentence["metadata"]
                sent_id = metadata.get("sent_id", "")
                sentence_text = metadata.get("text", "")
                sentence_tokens = {token["id"]: token for token in sentence["tokens"]}
                for token in sentence["tokens"]:
                    rule = apply_rules(token, sentence_tokens, rules)
                    if token["upos"] not in BASE_TARGET_UPOS and rule is None:
                        continue
                    writer.writerow(row_from_token(input_path.name, sent_id, sentence_text, token, rule, args.include_text))


if __name__ == "__main__":
    main()
