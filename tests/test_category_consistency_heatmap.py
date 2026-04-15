from __future__ import annotations

import random
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = REPO_ROOT / "rules" / "cgel_retagging.csv"
RETAG_SCRIPT = REPO_ROOT / "scripts" / "retag.py"
HEATMAP_SCRIPT = REPO_ROOT / "scripts" / "category_consistency_heatmap.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import category_consistency_heatmap as heatmap


MINI_CONLLU = """# sent_id = s1
# text = We want to leave.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\twant\twant\tVERB\tVBP\tMood=Ind|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\t_
3\tto\tto\tPART\tTO\t_\t4\tmark\t4:mark\t_
4\tleave\tleave\tVERB\tVB\tVerbForm=Inf\t2\txcomp\t2:xcomp\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s2
# text = Ask whether Kim left.
1\tAsk\task\tVERB\tVB\tMood=Imp|VerbForm=Fin\t0\troot\t0:root\t_
2\twhether\twhether\tSCONJ\tIN\t_\t4\tmark\t4:mark\t_
3\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t4\tnsubj\t4:nsubj\t_
4\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t1\tccomp\t1:ccomp\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s3
# text = Kim and Pat left.
1\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t4\tnsubj\t4:nsubj\t_
2\tand\tand\tCCONJ\tCC\t_\t3\tcc\t3:cc\t_
3\tPat\tPat\tPROPN\tNNP\tNumber=Sing\t1\tconj\t1:conj\t_
4\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_
"""


class CategoryConsistencyHeatmapTest(unittest.TestCase):
    def test_ablate_features_removes_rule_family_prefixes(self) -> None:
        features = {
            "PREV_UPOS=DET": 1.0,
            "PREV_IS_DET=yes": 1.0,
            "NEXT_OF=yes": 1.0,
            "TOKEN_FEAT_PronType=Ind": 1.0,
            "HEAD_UPOS=VERB": 1.0,
        }
        ablated = heatmap.ablate_features(features, "one_cleanup")
        self.assertEqual({"HEAD_UPOS=VERB": 1.0}, ablated)

    def test_shuffled_labels_preserve_per_corpus_counts(self) -> None:
        labels = np.array(["A", "A", "B", "B", "A", "B"], dtype=object)
        corpora = np.array(["x", "x", "x", "y", "y", "y"], dtype=object)
        shuffled = heatmap.shuffled_labels(labels, corpora, random.Random(7))
        for corpus in {"x", "y"}:
            original = Counter(labels[corpora == corpus].tolist())
            resampled = Counter(shuffled[corpora == corpus].tolist())
            self.assertEqual(original, resampled)

    def test_neighbor_share_matrix_excludes_self_neighbors(self) -> None:
        distances = np.array(
            [
                [0.0, 0.1, 0.2],
                [0.1, 0.0, 0.3],
                [0.2, 0.3, 0.0],
            ],
            dtype=np.float64,
        )
        labels = np.array(["A", "B", "B"], dtype=object)
        matrix, _ = heatmap.neighbor_share_matrix_from_distances(distances, labels, ["A", "B"], k=5)
        self.assertAlmostEqual(matrix[0, 1], 1.0)
        self.assertAlmostEqual(matrix[0, 0], 0.0)

    def test_heatmap_script_smoke_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_root = Path(tmp_dir)
            raw_root = temp_root / "data_raw" / "sample"
            raw_root.mkdir(parents=True)
            raw_path = raw_root / "sample.conllu"
            raw_path.write_text(MINI_CONLLU, encoding="utf-8")
            sidecar_path = temp_root / "sample.cgel.tsv"
            output_dir = temp_root / "heatmap"

            subprocess.run(
                [
                    sys.executable,
                    str(RETAG_SCRIPT),
                    str(raw_path),
                    "--rules",
                    str(RULES_PATH),
                    "--output",
                    str(sidecar_path),
                ],
                check=True,
                cwd=REPO_ROOT,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(HEATMAP_SCRIPT),
                    str(sidecar_path),
                    "--data-raw",
                    str(temp_root / "data_raw"),
                    "--output-dir",
                    str(output_dir),
                    "--bootstrap",
                    "1",
                    "--k-values",
                    "1",
                    "--metrics",
                    "cosine",
                    "--unit-levels",
                    "token",
                    "--category-levels",
                    "subtype",
                    "--min-balanced-size",
                    "1",
                    "--min-lexeme-count",
                    "1",
                    "--raw-max-items",
                    "20",
                ],
                check=True,
                cwd=REPO_ROOT,
            )

            expected_outputs = {
                "ablation_map.tsv",
                "heatmap_subtype_pooled_full.tsv",
                "heatmap_subtype_chance_corrected_ablated.tsv",
                "nearest_neighbor_exemplars.tsv",
                "off_diagonal_outliers.tsv",
            }
            self.assertTrue(expected_outputs.issubset({path.name for path in output_dir.iterdir()}))


if __name__ == "__main__":
    unittest.main()
