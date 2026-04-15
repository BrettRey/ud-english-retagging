#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Sequence

import numpy as np
from scipy.spatial.distance import cdist

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from retag import effective_form, effective_lemma, has_ref_dependency, parse_conllu, parse_misc_fields


STABILIZED_OVERT_CORPORA = {
    "ewt",
    "gum",
    "atis",
    "partut",
    "gentle",
    "ctetex",
    "littleprince",
    "pronouns",
    "pud",
}
HIGH_RISK_LEMMAS = {"one", "that", "if", "for", "there", "other", "to"}
NOMINAL_UPOS = {"NOUN", "PROPN", "PRON", "NUM", "DET", "ADJ"}
CLAUSAL_DEPREL_PREFIXES = ("ccomp", "xcomp", "csubj", "advcl", "acl", "parataxis")
NP_COMPLEMENT_DEPREL_PREFIXES = ("obj", "iobj", "obl", "nmod")

RULE_FAMILY_PREFIXES = {
    "relative_subordinator": [
        "TOKEN_FEAT_PronType=",
        "HAS_REF_DEP=",
        "HEAD_DEPREL=acl:relcl",
        "GRANDPARENT_DEPREL=acl:relcl",
    ],
    "clausal_preposition": [
        "HAS_DEP_CLAUSE=",
        "HAS_NP_COMPLEMENT=",
        "HAS_NO_COMPLEMENT=",
    ],
    "infinitival_to": [
        "TOKEN_FEAT_VerbForm=Inf",
    ],
    "one_cleanup": [
        "PREV_UPOS=",
        "PREV_IS_",
        "NEXT_OF=",
        "TOKEN_FEAT_PronType=",
    ],
    "generic": [],
}


@dataclass(frozen=True)
class SentenceRecord:
    source_file: str
    sent_id: str
    tokens: list[dict[str, str]]
    tokens_by_id: dict[str, dict[str, str]]
    id_to_index: dict[str, int]
    children_by_head: dict[str, list[str]]


@dataclass(frozen=True)
class TokenItem:
    item_id: str
    corpus: str
    source_file: str
    sent_id: str
    token_id: str
    form: str
    lemma: str
    label_coarse: str
    label_subtype: str
    rule_id: str
    rule_family: str
    needs_review: bool
    full_features: dict[str, float]
    ablated_features: dict[str, float]


@dataclass(frozen=True)
class SliceDataset:
    unit_level: str
    corpus: str
    item_ids: list[str]
    corpora: np.ndarray
    lemmas: list[str]
    labels_coarse: np.ndarray
    labels_subtype: np.ndarray
    rule_families: list[str]
    X_full: np.ndarray
    X_ablated: np.ndarray


@dataclass
class MatrixAccumulator:
    labels: list[str]
    sum_matrix: np.ndarray
    sumsq_matrix: np.ndarray
    count: int = 0
    tie_sum: float = 0.0

    @classmethod
    def create(cls, labels: list[str]) -> "MatrixAccumulator":
        size = len(labels)
        return cls(labels=labels, sum_matrix=np.zeros((size, size)), sumsq_matrix=np.zeros((size, size)))

    def add(self, matrix: np.ndarray, mean_ties: float) -> None:
        self.sum_matrix += matrix
        self.sumsq_matrix += np.square(matrix)
        self.tie_sum += mean_ties
        self.count += 1

    def mean(self) -> np.ndarray:
        if self.count == 0:
            return np.zeros_like(self.sum_matrix)
        return self.sum_matrix / self.count

    def stddev(self) -> np.ndarray:
        if self.count == 0:
            return np.zeros_like(self.sum_matrix)
        mean = self.mean()
        variance = (self.sumsq_matrix / self.count) - np.square(mean)
        variance = np.maximum(variance, 0.0)
        return np.sqrt(variance)

    def mean_ties(self) -> float:
        return 0.0 if self.count == 0 else self.tie_sum / self.count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build category-consistency heatmap TSVs from retagged sidecars.")
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Sidecar TSV files or directories. Defaults to stabilized overt-form corpora under data_derived/.",
    )
    parser.add_argument("--data-raw", default="data_raw", help="Root directory containing raw CoNLL-U corpora.")
    parser.add_argument("--data-derived", default="data_derived", help="Root directory containing sidecar TSV files.")
    parser.add_argument("--output-dir", required=True, help="Directory for analysis TSV outputs.")
    parser.add_argument("--bootstrap", type=int, default=200, help="Number of balanced bootstrap repetitions.")
    parser.add_argument("--k-values", default="5,15,50", help="Comma-separated neighborhood sizes.")
    parser.add_argument("--metrics", default="cosine,jaccard", help="Comma-separated metrics.")
    parser.add_argument("--unit-levels", default="token,lexeme", help="Comma-separated unit levels.")
    parser.add_argument("--category-levels", default="coarse,subtype", help="Comma-separated category levels.")
    parser.add_argument("--random-seed", type=int, default=13, help="Random seed.")
    parser.add_argument("--min-lexeme-count", type=int, default=5, help="Minimum token count for a lexeme centroid.")
    parser.add_argument(
        "--min-balanced-size",
        type=int,
        default=30,
        help="Minimum category size required to participate in a balanced bootstrap matrix.",
    )
    parser.add_argument(
        "--raw-max-items",
        type=int,
        default=5000,
        help="Maximum number of source items used for descriptive raw matrices.",
    )
    parser.add_argument(
        "--high-risk-lemmas",
        default="one,that,if,for,there,other,to",
        help="Comma-separated lemmas for the nearest-neighbor exemplar dump.",
    )
    parser.add_argument(
        "--include-lines",
        action="store_true",
        help="Include LinES in the default input discovery set.",
    )
    return parser.parse_args()


def iter_sidecar_files(inputs: Sequence[str], data_derived_root: Path, include_lines: bool) -> Iterator[Path]:
    if inputs:
        seen: set[Path] = set()
        for raw in inputs:
            path = Path(raw)
            if path.is_dir():
                candidates = sorted(p for p in path.glob("*.tsv") if p.is_file())
            elif path.is_file():
                candidates = [path]
            else:
                raise FileNotFoundError(f"Input path not found: {raw}")
            for candidate in candidates:
                resolved = candidate.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                yield candidate
        return
    for candidate in sorted(p for p in data_derived_root.glob("*.cgel.tsv") if p.is_file()):
        corpus = corpus_from_source_file(candidate.name.replace(".cgel.tsv", ".conllu"))
        if corpus not in STABILIZED_OVERT_CORPORA and not (include_lines and corpus == "lines"):
            continue
        yield candidate


def corpus_from_source_file(source_file: str) -> str:
    stem = source_file.removesuffix(".cgel.tsv").removesuffix(".conllu")
    if stem.startswith("en_"):
        return stem.split("-")[0][3:]
    return stem.split("-")[0]


def parse_feat_string(raw_feats: str) -> dict[str, str]:
    if not raw_feats or raw_feats == "_":
        return {}
    fields: dict[str, str] = {}
    for part in raw_feats.split("|"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[key] = value
    return fields


def rule_family_for_row(row: dict[str, str]) -> str:
    lemma = row["lemma"].casefold()
    rule_id = row["rule_id"]
    if row["br_cat"] == "subordinator" and row["br_subtype"] == "relative":
        return "relative_subordinator"
    if row["br_cat"] == "preposition" and row["br_subtype"] == "clausal":
        return "clausal_preposition"
    if rule_id == "verb-infinitival-to":
        return "infinitival_to"
    if "one" in lemma or "one" in rule_id:
        return "one_cleanup"
    return "generic"


def ablate_features(features: dict[str, float], rule_family: str) -> dict[str, float]:
    prefixes = RULE_FAMILY_PREFIXES.get(rule_family, [])
    if not prefixes:
        return dict(features)
    ablated: dict[str, float] = {}
    for name, value in features.items():
        if any(name.startswith(prefix) for prefix in prefixes):
            continue
        ablated[name] = value
    return ablated


def discover_raw_paths(data_raw_root: Path, source_files: set[str]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for corpus_dir in sorted(data_raw_root.iterdir()):
        if not corpus_dir.is_dir():
            continue
        for candidate in sorted(corpus_dir.glob("*.conllu")):
            if candidate.name in source_files:
                paths[candidate.name] = candidate
    missing = sorted(source_files - set(paths))
    if missing:
        raise FileNotFoundError(f"Missing raw corpora for: {', '.join(missing)}")
    return paths


def load_sidecar_rows(sidecar_paths: Sequence[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sidecar_paths:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                rows.append(row)
    rows.sort(key=lambda row: (row["source_file"], row["sent_id"], int(row["token_id"])))
    return rows


def load_sentence_index(raw_paths: dict[str, Path], needed_sent_ids: dict[str, set[str]]) -> dict[tuple[str, str], SentenceRecord]:
    index: dict[tuple[str, str], SentenceRecord] = {}
    for source_file, path in raw_paths.items():
        wanted = needed_sent_ids[source_file]
        for sentence in parse_conllu(path):
            metadata = sentence["metadata"]
            sent_id = metadata.get("sent_id", "")
            if sent_id not in wanted:
                continue
            tokens = sentence["tokens"]
            tokens_by_id = {token["id"]: token for token in tokens}
            id_to_index = {token["id"]: position for position, token in enumerate(tokens)}
            children_by_head: dict[str, list[str]] = defaultdict(list)
            for token in tokens:
                children_by_head[token["head"]].append(token["id"])
            index[(source_file, sent_id)] = SentenceRecord(
                source_file=source_file,
                sent_id=sent_id,
                tokens=tokens,
                tokens_by_id=tokens_by_id,
                id_to_index=id_to_index,
                children_by_head=dict(children_by_head),
            )
    return index


def derive_head_lemma_inventory(rows: Sequence[dict[str, str]], sentence_index: dict[tuple[str, str], SentenceRecord]) -> set[str]:
    counter: Counter[str] = Counter()
    total = 0
    for row in rows:
        sentence = sentence_index[(row["source_file"], row["sent_id"])]
        head_token = sentence.tokens_by_id.get(row["ud_head"])
        if not head_token:
            continue
        lemma = effective_lemma(head_token).casefold()
        if not lemma or lemma == "_":
            continue
        counter[lemma] += 1
        total += 1
    if total == 0:
        return set()
    threshold = max(1, int(np.ceil(total * 0.01)))
    retained = [lemma for lemma, count in counter.most_common() if count >= threshold][:10]
    return set(retained)


def child_has_clause(sentence: SentenceRecord, token_id: str) -> bool:
    for child_id in sentence.children_by_head.get(token_id, []):
        child = sentence.tokens_by_id[child_id]
        if child["deprel"].startswith(CLAUSAL_DEPREL_PREFIXES):
            return True
        if child["upos"] in {"VERB", "AUX"} and child["deprel"] not in {"cop", "aux", "aux:pass"}:
            return True
    return False


def child_has_np_complement(sentence: SentenceRecord, token_id: str) -> bool:
    for child_id in sentence.children_by_head.get(token_id, []):
        child = sentence.tokens_by_id[child_id]
        if child["upos"] in NOMINAL_UPOS and child["deprel"].startswith(NP_COMPLEMENT_DEPREL_PREFIXES):
            return True
    return False


def build_feature_dict(
    row: dict[str, str],
    sentence: SentenceRecord,
    head_lemma_inventory: set[str],
) -> dict[str, float]:
    token = sentence.tokens_by_id[row["token_id"]]
    token_index = sentence.id_to_index[row["token_id"]]
    prev_token = sentence.tokens[token_index - 1] if token_index > 0 else {}
    next_token = sentence.tokens[token_index + 1] if token_index + 1 < len(sentence.tokens) else {}
    head_token = sentence.tokens_by_id.get(token["head"], {})
    grandparent_token = sentence.tokens_by_id.get(head_token.get("head", ""), {})
    token_feats = parse_feat_string(token["feats"])
    token_misc = parse_misc_fields(token["misc"])
    features: dict[str, float] = {
        f"TOKEN_DEPREL={token['deprel']}": 1.0,
        f"HEAD_DEPREL={head_token.get('deprel', 'ROOT')}": 1.0,
        f"HEAD_UPOS={head_token.get('upos', 'ROOT')}": 1.0,
        f"GRANDPARENT_UPOS={grandparent_token.get('upos', 'ROOT')}": 1.0,
        f"GRANDPARENT_DEPREL={grandparent_token.get('deprel', 'ROOT')}": 1.0,
    }
    if prev_token:
        features[f"PREV_UPOS={prev_token['upos']}"] = 1.0
        if prev_token["upos"] == "DET":
            features["PREV_IS_DET=yes"] = 1.0
        if prev_token["upos"] == "ADJ":
            features["PREV_IS_ADJ=yes"] = 1.0
        if effective_form(prev_token) == ",":
            features["POST_COMMA=yes"] = 1.0
    if next_token:
        features[f"NEXT_UPOS={next_token['upos']}"] = 1.0
        if effective_lemma(next_token).casefold() == "of":
            features["NEXT_OF=yes"] = 1.0
    if token_index == 0:
        features["SENTENCE_INITIAL=yes"] = 1.0
    if child_has_clause(sentence, token["id"]):
        features["HAS_DEP_CLAUSE=yes"] = 1.0
    if child_has_np_complement(sentence, token["id"]):
        features["HAS_NP_COMPLEMENT=yes"] = 1.0
    if "HAS_DEP_CLAUSE=yes" not in features and "HAS_NP_COMPLEMENT=yes" not in features:
        features["HAS_NO_COMPLEMENT=yes"] = 1.0
    if has_ref_dependency(token["deps"]):
        features["HAS_REF_DEP=yes"] = 1.0
    for key in ("PronType", "Poss", "Reflex", "NumType", "VerbForm"):
        if key in token_feats:
            features[f"TOKEN_FEAT_{key}={token_feats[key]}"] = 1.0
    foreign_value = token_feats.get("Foreign") or token_misc.get("Foreign") or ("Yes" if token["xpos"] == "FGN" else "")
    if foreign_value:
        features[f"TOKEN_FEAT_Foreign={foreign_value}"] = 1.0
    head_lemma = effective_lemma(head_token).casefold() if head_token else ""
    if head_lemma:
        normalized_head = head_lemma if head_lemma in head_lemma_inventory else "HEAD_LEMMA_OTHER"
        features[f"HEAD_LEMMA={normalized_head}"] = 1.0
    return features


def build_token_items(
    rows: Sequence[dict[str, str]],
    sentence_index: dict[tuple[str, str], SentenceRecord],
    head_lemma_inventory: set[str],
) -> list[TokenItem]:
    items: list[TokenItem] = []
    for row in rows:
        sentence = sentence_index[(row["source_file"], row["sent_id"])]
        token = sentence.tokens_by_id[row["token_id"]]
        item_id = f"{row['source_file']}::{row['sent_id']}::{row['token_id']}"
        corpus = corpus_from_source_file(row["source_file"])
        lemma = effective_lemma(token).casefold() or row["lemma"].casefold()
        form = effective_form(token)
        label_coarse = row["br_cat"]
        label_subtype = f"{row['br_cat']}[{row['br_subtype']}]"
        rule_family = rule_family_for_row(row)
        full_features = build_feature_dict(row, sentence, head_lemma_inventory)
        items.append(
            TokenItem(
                item_id=item_id,
                corpus=corpus,
                source_file=row["source_file"],
                sent_id=row["sent_id"],
                token_id=row["token_id"],
                form=form,
                lemma=lemma,
                label_coarse=label_coarse,
                label_subtype=label_subtype,
                rule_id=row["rule_id"],
                rule_family=rule_family,
                needs_review=row["needs_review"].strip().lower() == "true",
                full_features=full_features,
                ablated_features=ablate_features(full_features, rule_family),
            )
        )
    return items


def vectorize_items(items: Sequence[TokenItem]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    feature_names = sorted({feature for item in items for feature in item.full_features})
    feature_index = {feature: index for index, feature in enumerate(feature_names)}
    full_matrix = np.zeros((len(items), len(feature_names)), dtype=np.float32)
    ablated_matrix = np.zeros((len(items), len(feature_names)), dtype=np.float32)
    for row_index, item in enumerate(items):
        for feature_name, value in item.full_features.items():
            full_matrix[row_index, feature_index[feature_name]] = value
        for feature_name, value in item.ablated_features.items():
            ablated_matrix[row_index, feature_index[feature_name]] = value
    return full_matrix, ablated_matrix, feature_names


def build_token_slice(
    corpus_name: str,
    items: Sequence[TokenItem],
    X_full: np.ndarray,
    X_ablated: np.ndarray,
    indices: Sequence[int],
) -> SliceDataset:
    return SliceDataset(
        unit_level="token",
        corpus=corpus_name,
        item_ids=[items[index].item_id for index in indices],
        corpora=np.array([items[index].corpus for index in indices], dtype=object),
        lemmas=[items[index].lemma for index in indices],
        labels_coarse=np.array([items[index].label_coarse for index in indices], dtype=object),
        labels_subtype=np.array([items[index].label_subtype for index in indices], dtype=object),
        rule_families=[items[index].rule_family for index in indices],
        X_full=X_full[np.array(indices)],
        X_ablated=X_ablated[np.array(indices)],
    )


def build_lexeme_slice(
    corpus_name: str,
    token_slice: SliceDataset,
    min_lexeme_count: int,
) -> tuple[SliceDataset, list[dict[str, object]]]:
    sparse_rows: list[dict[str, object]] = []
    groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for index, (lemma, label_coarse, label_subtype) in enumerate(
        zip(token_slice.lemmas, token_slice.labels_coarse, token_slice.labels_subtype, strict=True)
    ):
        groups[(lemma, label_coarse, label_subtype)].append(index)
    item_ids: list[str] = []
    corpora: list[str] = []
    lemmas: list[str] = []
    labels_coarse: list[str] = []
    labels_subtype: list[str] = []
    rule_families: list[str] = []
    centroid_rows_full: list[np.ndarray] = []
    centroid_rows_ablated: list[np.ndarray] = []
    for (lemma, label_coarse, label_subtype), indices in sorted(groups.items()):
        if len(indices) < min_lexeme_count:
            sparse_rows.append(
                {
                    "unit_level": "lexeme",
                    "corpus": corpus_name,
                    "lemma": lemma,
                    "label_coarse": label_coarse,
                    "label_subtype": label_subtype,
                    "count": len(indices),
                }
            )
            continue
        centroid_rows_full.append(token_slice.X_full[np.array(indices)].mean(axis=0))
        centroid_rows_ablated.append(token_slice.X_ablated[np.array(indices)].mean(axis=0))
        families = Counter(token_slice.rule_families[index] for index in indices)
        rule_family = families.most_common(1)[0][0]
        item_ids.append(f"{corpus_name}::{lemma}::{label_subtype}")
        corpora.append(corpus_name)
        lemmas.append(lemma)
        labels_coarse.append(label_coarse)
        labels_subtype.append(label_subtype)
        rule_families.append(rule_family)
    if centroid_rows_full:
        X_full = np.vstack(centroid_rows_full).astype(np.float32)
        X_ablated = np.vstack(centroid_rows_ablated).astype(np.float32)
    else:
        shape = (0, token_slice.X_full.shape[1])
        X_full = np.zeros(shape, dtype=np.float32)
        X_ablated = np.zeros(shape, dtype=np.float32)
    return (
        SliceDataset(
            unit_level="lexeme",
            corpus=corpus_name,
            item_ids=item_ids,
            corpora=np.array(corpora, dtype=object),
            lemmas=lemmas,
            labels_coarse=np.array(labels_coarse, dtype=object),
            labels_subtype=np.array(labels_subtype, dtype=object),
            rule_families=rule_families,
            X_full=X_full,
            X_ablated=X_ablated,
        ),
        sparse_rows,
    )


def sample_indices(indices: Sequence[int], n: int, rng: random.Random) -> list[int]:
    if len(indices) <= n:
        return list(indices)
    return rng.sample(list(indices), n)


def stable_order(distances: np.ndarray) -> np.ndarray:
    return np.lexsort((np.arange(distances.shape[0]), distances))


def compute_pairwise_distance_matrix(X: np.ndarray, metric: str) -> np.ndarray:
    if metric == "jaccard":
        query_matrix = np.asarray(X > 0, dtype=bool)
    elif metric == "cosine":
        query_matrix = np.asarray(X, dtype=np.float64)
    else:
        raise ValueError(f"Unsupported metric: {metric}")
    return cdist(query_matrix, query_matrix, metric=metric)


def compute_cross_distance_matrix(query: np.ndarray, reference: np.ndarray, metric: str) -> np.ndarray:
    if metric == "jaccard":
        query_matrix = np.asarray(query > 0, dtype=bool)
        reference_matrix = np.asarray(reference > 0, dtype=bool)
    elif metric == "cosine":
        query_matrix = np.asarray(query, dtype=np.float64)
        reference_matrix = np.asarray(reference, dtype=np.float64)
    else:
        raise ValueError(f"Unsupported metric: {metric}")
    return cdist(query_matrix, reference_matrix, metric=metric)


def neighbor_share_matrix_from_distances(
    distances: np.ndarray,
    labels: np.ndarray,
    label_order: list[str],
    k: int,
) -> tuple[np.ndarray, float]:
    if len(labels) <= 1:
        size = len(label_order)
        return np.zeros((size, size), dtype=np.float32), 0.0
    working = distances.copy()
    np.fill_diagonal(working, np.inf)
    label_to_index = {label: index for index, label in enumerate(label_order)}
    matrix = np.zeros((len(label_order), len(label_order)), dtype=np.float32)
    tie_counts: list[int] = []
    for source_index in range(working.shape[0]):
        order = stable_order(working[source_index])
        max_neighbors = min(k, max(0, len(order) - 1))
        neighbors = [neighbor for neighbor in order if neighbor != source_index][:max_neighbors]
        if len(neighbors) == 0:
            continue
        boundary_distance = working[source_index, neighbors[-1]]
        tie_counts.append(int(np.sum(np.isclose(working[source_index], boundary_distance))))
        counts = np.zeros(len(label_order), dtype=np.float32)
        for neighbor in neighbors:
            counts[label_to_index[labels[neighbor]]] += 1.0
        counts /= len(neighbors)
        matrix[label_to_index[labels[source_index]]] += counts
    row_counts = Counter(labels.tolist())
    for label, count in row_counts.items():
        matrix[label_to_index[label]] /= count
    mean_ties = float(np.mean(tie_counts)) if tie_counts else 0.0
    return matrix, mean_ties


def chance_corrected_matrix(matrix: np.ndarray, labels: np.ndarray, label_order: list[str]) -> np.ndarray:
    counts = Counter(labels.tolist())
    expected = np.array([counts[label] / len(labels) for label in label_order], dtype=np.float32)
    return matrix - expected[np.newaxis, :]


def shuffled_labels(labels: np.ndarray, corpora: np.ndarray, rng: random.Random) -> np.ndarray:
    shuffled = labels.copy()
    for corpus in sorted(set(corpora.tolist())):
        corpus_indices = [index for index, value in enumerate(corpora.tolist()) if value == corpus]
        values = shuffled[corpus_indices].tolist()
        rng.shuffle(values)
        shuffled[corpus_indices] = np.array(values, dtype=object)
    return shuffled


def ci_excludes_zero(mean: float, stddev: float) -> bool:
    return not (mean - (1.96 * stddev) <= 0.0 <= mean + (1.96 * stddev))


def annotate_outlier_support(rows: list[dict[str, object]]) -> None:
    grouped: dict[tuple[str, str, str, str, str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row["unit_level"]),
            str(row["category_level"]),
            str(row["corpus"]),
            str(row["state"]),
            str(row["metric"]),
            str(row["source_label"]),
            str(row["neighbor_label"]),
            str(row["analysis_scope"]),
        )
        grouped[key].append(row)
    for bucket in grouped.values():
        supporting = 0
        for row in bucket:
            local_pass = (
                float(row["value"]) >= 0.15
                and ci_excludes_zero(float(row["value"]), float(row["stddev"]))
                and float(row["value"]) > float(row["null_value"])
            )
            row["passes_local_threshold"] = str(local_pass).lower()
            supporting += int(local_pass)
        robust = supporting >= 2
        for row in bucket:
            row["k_support_count"] = supporting
            row["passes_threshold"] = str(robust).lower()


def write_tsv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def emit_matrix_rows(
    accumulator_map: dict[tuple[str, str, str, str, str], MatrixAccumulator],
    unit_level: str,
    category_level: str,
    corpus_name: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (matrix_kind, state, metric, k_value, matrix_type), accumulator in sorted(accumulator_map.items()):
        mean_matrix = accumulator.mean()
        for source_index, source_label in enumerate(accumulator.labels):
            for neighbor_index, neighbor_label in enumerate(accumulator.labels):
                rows.append(
                    {
                        "unit_level": unit_level,
                        "category_level": category_level,
                        "corpus": corpus_name,
                        "matrix_kind": matrix_kind,
                        "state": state,
                        "metric": metric,
                        "k": k_value,
                        "source_label": source_label,
                        "neighbor_label": neighbor_label,
                        "value": f"{mean_matrix[source_index, neighbor_index]:.6f}",
                        "mean_boundary_ties": f"{accumulator.mean_ties():.6f}",
                        "bootstrap_repetitions": accumulator.count,
                        "matrix_type": matrix_type,
                    }
                )
    return rows


def emit_stddev_rows(
    accumulator_map: dict[tuple[str, str, str, str, str], MatrixAccumulator],
    unit_level: str,
    category_level: str,
    corpus_name: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (matrix_kind, state, metric, k_value, matrix_type), accumulator in sorted(accumulator_map.items()):
        std_matrix = accumulator.stddev()
        for source_index, source_label in enumerate(accumulator.labels):
            for neighbor_index, neighbor_label in enumerate(accumulator.labels):
                rows.append(
                    {
                        "unit_level": unit_level,
                        "category_level": category_level,
                        "corpus": corpus_name,
                        "matrix_kind": matrix_kind,
                        "state": state,
                        "metric": metric,
                        "k": k_value,
                        "source_label": source_label,
                        "neighbor_label": neighbor_label,
                        "value": f"{std_matrix[source_index, neighbor_index]:.6f}",
                        "bootstrap_repetitions": accumulator.count,
                        "matrix_type": matrix_type,
                    }
                )
    return rows


def main() -> None:
    args = parse_args()
    rng = random.Random(args.random_seed)
    k_values = sorted(int(raw) for raw in args.k_values.split(",") if raw.strip())
    metrics = [raw.strip() for raw in args.metrics.split(",") if raw.strip()]
    unit_levels = [raw.strip() for raw in args.unit_levels.split(",") if raw.strip()]
    category_levels = [raw.strip() for raw in args.category_levels.split(",") if raw.strip()]
    high_risk_lemmas = {raw.strip().casefold() for raw in args.high_risk_lemmas.split(",") if raw.strip()}

    data_derived_root = Path(args.data_derived)
    sidecar_paths = list(iter_sidecar_files(args.inputs, data_derived_root, args.include_lines))
    if not sidecar_paths:
        raise FileNotFoundError("No sidecar TSVs selected.")

    sidecar_rows = load_sidecar_rows(sidecar_paths)
    needed_sent_ids: dict[str, set[str]] = defaultdict(set)
    needed_source_files: set[str] = set()
    for row in sidecar_rows:
        needed_sent_ids[row["source_file"]].add(row["sent_id"])
        needed_source_files.add(row["source_file"])
    raw_paths = discover_raw_paths(Path(args.data_raw), needed_source_files)
    sentence_index = load_sentence_index(raw_paths, needed_sent_ids)
    head_lemma_inventory = derive_head_lemma_inventory(sidecar_rows, sentence_index)
    token_items = build_token_items(sidecar_rows, sentence_index, head_lemma_inventory)
    X_full, X_ablated, _ = vectorize_items(token_items)

    all_indices = list(range(len(token_items)))
    token_slices: dict[str, SliceDataset] = {
        "pooled": build_token_slice("pooled", token_items, X_full, X_ablated, all_indices)
    }
    for corpus in sorted({item.corpus for item in token_items}):
        indices = [index for index, item in enumerate(token_items) if item.corpus == corpus]
        token_slices[corpus] = build_token_slice(corpus, token_items, X_full, X_ablated, indices)

    sparse_lexeme_rows: list[dict[str, object]] = []
    slice_datasets: dict[tuple[str, str], SliceDataset] = {}
    for corpus_name, token_slice in token_slices.items():
        slice_datasets[("token", corpus_name)] = token_slice
        lexeme_slice, sparse_rows = build_lexeme_slice(corpus_name, token_slice, args.min_lexeme_count)
        slice_datasets[("lexeme", corpus_name)] = lexeme_slice
        sparse_lexeme_rows.extend(sparse_rows)

    raw_matrix_rows: list[dict[str, object]] = []
    balanced_matrix_rows: list[dict[str, object]] = []
    chance_matrix_rows: list[dict[str, object]] = []
    stddev_rows: list[dict[str, object]] = []
    null_rows: list[dict[str, object]] = []
    sparse_category_rows: list[dict[str, object]] = []
    tie_summary_rows: list[dict[str, object]] = []
    outlier_rows: list[dict[str, object]] = []

    for unit_level in unit_levels:
        for corpus_name in sorted(name for current_unit, name in slice_datasets if current_unit == unit_level):
            dataset = slice_datasets[(unit_level, corpus_name)]
            if len(dataset.item_ids) == 0:
                continue
            for category_level in category_levels:
                labels = dataset.labels_coarse if category_level == "coarse" else dataset.labels_subtype
                counts = Counter(labels.tolist())
                active_labels = sorted(label for label, count in counts.items() if count >= args.min_balanced_size)
                for label, count in sorted(counts.items()):
                    if count < args.min_balanced_size:
                        sparse_category_rows.append(
                            {
                                "unit_level": unit_level,
                                "category_level": category_level,
                                "corpus": corpus_name,
                                "label": label,
                                "count": count,
                            }
                        )
                if len(active_labels) < 2:
                    continue
                active_indices = [index for index, label in enumerate(labels.tolist()) if label in active_labels]
                balanced_n = min(counts[label] for label in active_labels)
                sample_groups = {label: [index for index in active_indices if labels[index] == label] for label in active_labels}
                raw_indices = active_indices
                if len(raw_indices) > args.raw_max_items:
                    raw_indices = sample_indices(raw_indices, args.raw_max_items, rng)
                raw_labels = labels[np.array(raw_indices)]
                for state, matrix_source in (("full", dataset.X_full), ("ablated", dataset.X_ablated)):
                    for metric in metrics:
                        raw_distances = compute_pairwise_distance_matrix(matrix_source[np.array(raw_indices)], metric)
                        raw_accumulators: dict[tuple[str, str, str, str, str], MatrixAccumulator] = {}
                        for k_value in k_values:
                            raw_matrix, raw_ties = neighbor_share_matrix_from_distances(
                                raw_distances, raw_labels, active_labels, k_value
                            )
                            raw_chance = chance_corrected_matrix(raw_matrix, raw_labels, active_labels)
                            raw_accumulators[("raw", state, metric, str(k_value), "raw")] = MatrixAccumulator.create(active_labels)
                            raw_accumulators[("raw", state, metric, str(k_value), "raw")].add(raw_matrix, raw_ties)
                            raw_accumulators[("raw", state, metric, str(k_value), "chance")] = MatrixAccumulator.create(active_labels)
                            raw_accumulators[("raw", state, metric, str(k_value), "chance")].add(raw_chance, raw_ties)
                        raw_matrix_rows.extend(emit_matrix_rows(raw_accumulators, unit_level, category_level, corpus_name))
                        tie_summary_rows.extend(
                            {
                                "unit_level": unit_level,
                                "category_level": category_level,
                                "corpus": corpus_name,
                                "state": state,
                                "metric": metric,
                                "k": k_value,
                                "matrix_kind": matrix_kind,
                                "mean_boundary_ties": f"{accumulator.mean_ties():.6f}",
                            }
                            for (matrix_kind, state, metric, k_value, matrix_type), accumulator in sorted(raw_accumulators.items())
                            if matrix_type == "raw"
                        )

                balanced_accumulators: dict[tuple[str, str, str, str, str], MatrixAccumulator] = {}
                null_accumulators: dict[tuple[str, str, str, str, str], MatrixAccumulator] = {}
                for bootstrap_index in range(args.bootstrap):
                    sampled_indices: list[int] = []
                    for label in active_labels:
                        sampled_indices.extend(sample_indices(sample_groups[label], balanced_n, rng))
                    sampled_indices.sort()
                    sampled_labels = labels[np.array(sampled_indices)]
                    sampled_corpora = dataset.corpora[np.array(sampled_indices)]
                    shuffled = shuffled_labels(sampled_labels, sampled_corpora, rng)
                    for state, matrix_source in (("full", dataset.X_full), ("ablated", dataset.X_ablated)):
                        for metric in metrics:
                            sampled_matrix = matrix_source[np.array(sampled_indices)]
                            sampled_distances = compute_pairwise_distance_matrix(sampled_matrix, metric)
                            for k_value in k_values:
                                observed_matrix, mean_ties = neighbor_share_matrix_from_distances(
                                    sampled_distances, sampled_labels, active_labels, k_value
                                )
                                shuffled_matrix, null_ties = neighbor_share_matrix_from_distances(
                                    sampled_distances, shuffled, active_labels, k_value
                                )
                                observed_chance = chance_corrected_matrix(observed_matrix, sampled_labels, active_labels)
                                shuffled_chance = chance_corrected_matrix(shuffled_matrix, shuffled, active_labels)
                                for matrix_kind, matrix_type, matrix, ties, target in (
                                    ("balanced", "raw", observed_matrix, mean_ties, balanced_accumulators),
                                    ("chance", "chance", observed_chance, mean_ties, balanced_accumulators),
                                    ("null", "raw", shuffled_matrix, null_ties, null_accumulators),
                                    ("null", "chance", shuffled_chance, null_ties, null_accumulators),
                                ):
                                    key = (matrix_kind, state, metric, str(k_value), matrix_type)
                                    if key not in target:
                                        target[key] = MatrixAccumulator.create(active_labels)
                                    target[key].add(matrix, ties)

                balanced_matrix_rows.extend(emit_matrix_rows(balanced_accumulators, unit_level, category_level, corpus_name))
                chance_rows = [
                    row for row in emit_matrix_rows(balanced_accumulators, unit_level, category_level, corpus_name)
                    if row["matrix_kind"] == "chance"
                ]
                chance_matrix_rows.extend(chance_rows)
                null_rows.extend(emit_matrix_rows(null_accumulators, unit_level, category_level, corpus_name))
                stddev_rows.extend(emit_stddev_rows(balanced_accumulators, unit_level, category_level, corpus_name))
                tie_summary_rows.extend(
                    {
                        "unit_level": unit_level,
                        "category_level": category_level,
                        "corpus": corpus_name,
                        "state": state,
                        "metric": metric,
                        "k": k_value,
                        "matrix_kind": matrix_kind,
                        "mean_boundary_ties": f"{accumulator.mean_ties():.6f}",
                    }
                    for (matrix_kind, state, metric, k_value, matrix_type), accumulator in sorted(balanced_accumulators.items())
                    if matrix_type == "raw"
                )
                for (matrix_kind, state, metric, k_value, matrix_type), accumulator in sorted(balanced_accumulators.items()):
                    if matrix_kind != "chance" or state != "ablated" or matrix_type != "chance":
                        continue
                    null_key = ("null", state, metric, k_value, matrix_type)
                    null_accumulator = null_accumulators[null_key]
                    mean_matrix = accumulator.mean()
                    std_matrix = accumulator.stddev()
                    null_mean = null_accumulator.mean()
                    for source_index, source_label in enumerate(accumulator.labels):
                        for neighbor_index, neighbor_label in enumerate(accumulator.labels):
                            if source_label == neighbor_label:
                                continue
                            value = float(mean_matrix[source_index, neighbor_index])
                            std_value = float(std_matrix[source_index, neighbor_index])
                            null_value = float(null_mean[source_index, neighbor_index])
                            outlier_rows.append(
                                {
                                    "unit_level": unit_level,
                                    "category_level": category_level,
                                    "corpus": corpus_name,
                                    "state": state,
                                    "metric": metric,
                                    "k": k_value,
                                    "source_label": source_label,
                                    "neighbor_label": neighbor_label,
                                    "value": f"{value:.6f}",
                                    "stddev": f"{std_value:.6f}",
                                    "null_value": f"{null_value:.6f}",
                                    "analysis_scope": "ablated_chance_corrected",
                                }
                            )

    high_risk_breakdown_rows: list[dict[str, object]] = []
    for item in token_items:
        if item.lemma not in high_risk_lemmas:
            continue
        high_risk_breakdown_rows.append(
            {
                "corpus": item.corpus,
                "lemma": item.lemma,
                "label_coarse": item.label_coarse,
                "label_subtype": item.label_subtype,
                "rule_family": item.rule_family,
                "rule_id": item.rule_id,
                "needs_review": str(item.needs_review).lower(),
            }
        )

    exemplar_rows: list[dict[str, object]] = []
    pooled_token_slice = token_slices["pooled"]
    for state, matrix_source in (("full", pooled_token_slice.X_full), ("ablated", pooled_token_slice.X_ablated)):
        for metric in metrics:
            for lemma in sorted(high_risk_lemmas):
                source_indices = [index for index, value in enumerate(pooled_token_slice.lemmas) if value == lemma]
                if not source_indices:
                    continue
                source_indices = source_indices[:10]
                if metric == "jaccard":
                    query_matrix = np.asarray(matrix_source > 0, dtype=bool)
                else:
                    query_matrix = matrix_source
                distances = compute_cross_distance_matrix(query_matrix[np.array(source_indices)], query_matrix, metric)
                for row_index, source_index in enumerate(source_indices):
                    source_id = pooled_token_slice.item_ids[source_index]
                    order = np.lexsort((np.arange(distances.shape[1]), distances[row_index]))
                    order = [neighbor for neighbor in order if neighbor != source_index][: max(k_values)]
                    for rank, neighbor in enumerate(order, start=1):
                        exemplar_rows.append(
                            {
                                "state": state,
                                "metric": metric,
                                "source_lemma": lemma,
                                "source_id": source_id,
                                "source_label_subtype": pooled_token_slice.labels_subtype[source_index],
                                "neighbor_rank": rank,
                                "neighbor_id": pooled_token_slice.item_ids[neighbor],
                                "neighbor_lemma": pooled_token_slice.lemmas[neighbor],
                                "neighbor_label_subtype": pooled_token_slice.labels_subtype[neighbor],
                                "applies_to_k": ",".join(str(k_value) for k_value in k_values if rank <= k_value),
                                "distance": f"{distances[row_index, neighbor]:.6f}",
                            }
                        )

    annotate_outlier_support(outlier_rows)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ablation_rows = [
        {
            "rule_family": family,
            "removed_feature_prefixes": "|".join(prefixes),
        }
        for family, prefixes in sorted(RULE_FAMILY_PREFIXES.items())
    ]
    write_tsv(output_dir / "ablation_map.tsv", ["rule_family", "removed_feature_prefixes"], ablation_rows)
    write_tsv(
        output_dir / "heatmap_coarse_pooled_full.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "mean_boundary_ties",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [
            row
            for row in raw_matrix_rows + balanced_matrix_rows
            if row["category_level"] == "coarse" and row["state"] == "full" and row["corpus"] == "pooled"
        ],
    )
    write_tsv(
        output_dir / "heatmap_coarse_pooled_ablated.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "mean_boundary_ties",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [
            row
            for row in raw_matrix_rows + balanced_matrix_rows
            if row["category_level"] == "coarse" and row["state"] == "ablated" and row["corpus"] == "pooled"
        ],
    )
    write_tsv(
        output_dir / "heatmap_subtype_pooled_full.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "mean_boundary_ties",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [row for row in raw_matrix_rows + balanced_matrix_rows if row["category_level"] == "subtype" and row["state"] == "full" and row["corpus"] == "pooled"],
    )
    write_tsv(
        output_dir / "heatmap_subtype_pooled_ablated.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "mean_boundary_ties",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [row for row in raw_matrix_rows + balanced_matrix_rows if row["category_level"] == "subtype" and row["state"] == "ablated" and row["corpus"] == "pooled"],
    )
    write_tsv(
        output_dir / "heatmap_subtype_by_corpus_full.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "mean_boundary_ties",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [row for row in raw_matrix_rows + balanced_matrix_rows if row["category_level"] == "subtype" and row["state"] == "full" and row["corpus"] != "pooled"],
    )
    write_tsv(
        output_dir / "heatmap_subtype_by_corpus_ablated.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "mean_boundary_ties",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [row for row in raw_matrix_rows + balanced_matrix_rows if row["category_level"] == "subtype" and row["state"] == "ablated" and row["corpus"] != "pooled"],
    )
    write_tsv(
        output_dir / "heatmap_subtype_chance_corrected_full.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "mean_boundary_ties",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [row for row in chance_matrix_rows if row["state"] == "full" and row["category_level"] == "subtype"],
    )
    write_tsv(
        output_dir / "heatmap_subtype_chance_corrected_ablated.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "mean_boundary_ties",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [row for row in chance_matrix_rows if row["state"] == "ablated" and row["category_level"] == "subtype"],
    )
    write_tsv(
        output_dir / "heatmap_subtype_bootstrap_stddev_full.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [row for row in stddev_rows if row["state"] == "full" and row["category_level"] == "subtype"],
    )
    write_tsv(
        output_dir / "heatmap_subtype_bootstrap_stddev_ablated.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [row for row in stddev_rows if row["state"] == "ablated" and row["category_level"] == "subtype"],
    )
    write_tsv(
        output_dir / "heatmap_subtype_null_baseline_full.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "mean_boundary_ties",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [row for row in null_rows if row["state"] == "full" and row["category_level"] == "subtype"],
    )
    write_tsv(
        output_dir / "heatmap_subtype_null_baseline_ablated.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "matrix_kind",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "mean_boundary_ties",
            "bootstrap_repetitions",
            "matrix_type",
        ],
        [row for row in null_rows if row["state"] == "ablated" and row["category_level"] == "subtype"],
    )
    write_tsv(
        output_dir / "off_diagonal_outliers.tsv",
        [
            "unit_level",
            "category_level",
            "corpus",
            "state",
            "metric",
            "k",
            "source_label",
            "neighbor_label",
            "value",
            "stddev",
            "null_value",
            "analysis_scope",
            "passes_local_threshold",
            "k_support_count",
            "passes_threshold",
        ],
        outlier_rows,
    )
    write_tsv(
        output_dir / "nearest_neighbor_exemplars.tsv",
        [
            "state",
            "metric",
            "source_lemma",
            "source_id",
            "source_label_subtype",
            "neighbor_rank",
            "neighbor_id",
            "neighbor_lemma",
            "neighbor_label_subtype",
            "applies_to_k",
            "distance",
        ],
        exemplar_rows,
    )
    write_tsv(
        output_dir / "high_risk_lexeme_breakdown.tsv",
        ["corpus", "lemma", "label_coarse", "label_subtype", "rule_family", "rule_id", "needs_review"],
        high_risk_breakdown_rows,
    )
    write_tsv(
        output_dir / "sparse_category_table.tsv",
        ["unit_level", "category_level", "corpus", "label", "count"],
        sparse_category_rows,
    )
    write_tsv(
        output_dir / "sparse_lexeme_table.tsv",
        ["unit_level", "corpus", "lemma", "label_coarse", "label_subtype", "count"],
        sparse_lexeme_rows,
    )
    write_tsv(
        output_dir / "tie_summary.tsv",
        ["unit_level", "category_level", "corpus", "state", "metric", "k", "matrix_kind", "mean_boundary_ties"],
        tie_summary_rows,
    )


if __name__ == "__main__":
    main()
