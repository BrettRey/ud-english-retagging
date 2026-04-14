# UD English Retagging

Deterministic, CGEL-aligned retagging for selected UD English closed-class mismatch categories.

This project builds a parallel annotation layer over UD English CoNLL-U files. It does not overwrite UD tags. Instead, it emits a sidecar TSV with CGEL-aligned category assignments for cases where the project’s target analysis diverges from UD, including determinatives, pronouns, coordinators, subordinators, prepositions, infinitival `to`, negative `n't`, and related low-frequency lexical gaps.

## Scope

- rule table in `rules/cgel_retagging.csv`
- retagger in `scripts/retag.py`
- audit script in `scripts/audit.py`
- regression coverage in `tests/test_pipeline.py`
- project decisions and current corpus status in `DECISIONS.md`, `STATUS.md`, and `CLAUDE.md`

The public repository is code-first. UD corpora, local symlinks, generated sidecar TSVs, and audit outputs are not versioned here.

## License and Data

The code in this repository is released under the MIT License.

UD corpora and any local derived outputs remain governed by their own upstream licenses and are not relicensed by this repository. To reproduce the current outputs, place the UD English corpora locally and run the scripts against your own checkout.

## Usage

Retag a corpus file:

```bash
python scripts/retag.py path/to/en_ewt-ud-dev.conllu \
  --rules rules/cgel_retagging.csv \
  --output out/en_ewt-ud-dev.cgel.tsv
```

Include sentence text for review workflows:

```bash
python scripts/retag.py path/to/en_ewt-ud-dev.conllu \
  --rules rules/cgel_retagging.csv \
  --output out/en_ewt-ud-dev.cgel.tsv \
  --include-text
```

Audit the sidecar output:

```bash
python scripts/audit.py out/en_ewt-ud-dev.cgel.tsv --output out/en_ewt-ud-dev.cgel.txt
```

Run tests:

```bash
python -m unittest discover -s tests
```

## Current Coverage

The working rule table has been exercised on EWT, GUM, ATIS, GENTLE, CTeTex, PUD, `pronouns`, and a frozen partial-coverage GUMReddit layer. See `STATUS.md` for the live summary.
