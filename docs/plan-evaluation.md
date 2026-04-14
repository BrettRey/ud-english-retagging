# Plan Evaluation: UD English Retagging

**Date:** 2026-04-14
**Method:** Discovery-driven planning (assumption testing against EWT data and the local runtime)

**Execution note:** the original MVP plan below was written around pronoun/determinative retagging only. The executed rule table was later broadened to cover the additional agreed CGEL/UD mismatch classes and now lives at `rules/cgel_retagging.csv`, with sidecar outputs named `*.cgel.tsv` and audits named `*.cgel.txt`.

## Assumptions Tested

### A1. UD mistaggs today/tomorrow as ADV

**Wrong for EWT.** UD already tags these as NOUN.

| Lemma | NOUN count | ADV count |
|-------|-----------|-----------|
| today | 70 | 0 |
| tomorrow | 29 | 0 |
| yesterday | 25 | 0 |
| tonight | 11 | 0 |

The real CGEL-UD mismatch in this neighbourhood is location/direction words that CGEL treats as prepositions:

| Lemma | ADV | ADP | PRON | NOUN | ADJ |
|-------|-----|-----|------|------|-----|
| there | 203 | — | 361 | — | — |
| here | 178 | — | — | — | — |
| away | 69 | 9 | — | — | — |
| home | 33 | — | — | 65 | — |
| outside | 17 | 17 | — | 4 | 12 |
| inside | 14 | 9 | — | 4 | 3 |

These are harder and messier than the pronoun/determinative split. Recommended: defer to Phase 2.

### A2. The inventory file provides the rule set

**Partial.** The `inventory_annotations.csv` from the reciprocals project has 138 entries (75 determinative, 59 pronoun, 4 noun), organized around personhood and anchor-set membership, not UD tag mapping. It's a useful seed but needs adaptation: the UD retagging needs to key on (lemma, UPOS, DEPREL), not on personhood profile.

### A3. Five-component pipeline is needed

**Overengineered.** The target space is 72 unique DET/PRON lemma-UPOS pairs. The overwhelming majority are unambiguous:

| Token | UPOS | Count | CGEL category |
|-------|------|-------|---------------|
| the | DET | 9,025 | determinative |
| a | DET | 4,062 | determinative |
| I | PRON | 3,470 | pronoun |
| you | PRON | 1,907 | pronoun |
| it | PRON | 1,814 | pronoun |
| this | DET | 599 | determinative |
| this | PRON | 318 | pronoun |

"Candidate extraction" as a separate script is just a UPOS filter. "Patch writer" is unnecessary (sidecar format, not modifying CoNLL-U). "Review queue" is a column in the output, not a separate component.

### A4. Sidecar TSV is the right output format

**Confirmed.** The EWT MISC column already carries complex constructional annotations (`Cxn=Interrogative-Polar-Indirect`, `CxnElt=...`, `TemporalNPAdjunct=Yes`, etc.). Appending BR_CAT fields would create unwieldy pipe-separated strings. Sidecar keeps the annotation layer cleanly separate and independently versionable.

### A5. Fused heads need special handling

**Confirmed.** `what` appears in both UD categories with different syntactic functions:

| UPOS | DEPREL | Count | CGEL analysis |
|------|--------|-------|---------------|
| DET | det | 51 | determinative (in determiner function) |
| PRON | obj | 143 | pronoun or fused head |
| PRON | nsubj | 60 | pronoun or fused head |
| PRON | obl | 51 | pronoun or fused head |
| PRON | root | 42 | pronoun (interrogative) |

Context-dependent: `what` as PRON/obj could be a direct interrogative pronoun (*what happened?*) or a fused relative head (*I know what you want*). These need DEPREL-based rules, not just UPOS mapping.

### A6. conllu library available

**Wrong in this environment.** `conllu` is not installed in the current workspace runtime. The first executable slice should therefore use a small standard-library CoNLL-U reader rather than assuming an external parser dependency.

## Proposed Revisions

### 1. Narrow Phase 1 to pronoun vs determinative

The original four targets overlap heavily:

- Target 1 (pronouns vs determinatives) — the core problem
- Target 3 (fused heads) — a subcase of the same problem
- Target 4 (interrogative determinatives vs pronouns) — another subcase

These are one problem: CGEL draws the pronoun/determinative boundary differently from UD's DET/PRON. Treat them as a single target with a single rule set.

Target 2 (temporal nouns as ADV) is wrong for EWT and the broader location/direction word problem is a different, harder project. Defer to Phase 2.

### 2. Simplify the operational pipeline to two scripts

Replace the five-component pipeline with:

- **`retag.py`** — reads CoNLL-U files, applies rules, writes sidecar TSV. Uncertain cases get a `needs_review` flag in the output, not a separate queue.
- **`audit.py`** — reads sidecar TSV, produces counts, consistency checks, and exception lists.

The candidate extractor, review queue, and patch writer are absorbed or eliminated. A one-time helper to materialize a local rule seed is acceptable, but it is not part of the operational annotation pipeline.

### 3. Rules as data, but adapted to actual UD keys

Put the mapping table in `rules/cgel_retagging.csv`, not hardcoded in Python. YAML would add an unnecessary dependency for the MVP. Structure:

- **Lookup layer:** (lemma, UPOS) → BR_CAT for unambiguous cases (covers ~90% of tokens)
- **Context layer:** (lemma, UPOS, DEPREL) → BR_CAT for ambiguous cases (fused heads, etc.)
- **Uncertain cases:** flag for manual review

Seed from the inventory file, adapted to UD-specific keys. The upstream inventory is useful for anchors and theory decisions, but it is not a drop-in retagging table because some inventory labels are not literal UD lemmas.

### 4. EWT dev only for proof of concept

Use `en_ewt-ud-dev.conllu` for the first executable pass. It is large enough to expose the main ambiguities without forcing full-corpus runtime or cross-corpus scope on day one. Extend to EWT test/train next, then GUM, then the rest.

### 5. Sidecar format

Output in `data_derived/` as TSV:

```text
source_file	sent_id	token_id	form	lemma	ud_upos	ud_deprel	br_cat	br_subtype	br_status	needs_review	rule_id
en_ewt-ud-dev.conllu	weblog-...-0001	14	the	the	DET	det	determinative		auto	false	determiner-lexemes
en_ewt-ud-dev.conllu	weblog-...-0001	11	us	we	PRON	obj	pronoun	personal	auto	false	pronoun-personal
```

Joinable on `sent_id` + `token_id`. Only rows for retagged tokens (not the full sentence).

## Finalized Plan

### Final decisions after review

1. **Pilot on EWT dev only.** Do not widen scope until the EWT dev pass produces a stable rule table and a manageable review set.
2. **Use zero-extra-dependency Python for the MVP.** The first pass should run in the current environment without installing `conllu` or adding a YAML parser requirement.
3. **Keep sidecar TSV as the primary annotation artifact.** Do not patch CoNLL-U in the MVP.
4. **Use a CSV rule table with lexical sets plus optional context constraints.** This keeps the first pass inspectable and easy to revise.
5. **Treat unresolved theory-sensitive cases as explicit review items.** The system should record uncertainty, not hide it.

### Immediate execution order

1. Create `rules/cgel_retagging.csv`.
2. Implement `scripts/retag.py`.
3. Implement `scripts/audit.py`.
4. Run `retag.py` on `../../corpora/ud-english/ewt/en_ewt-ud-dev.conllu`.
5. Run `audit.py` on the resulting TSV.
6. Update local project status from the actual pilot output, not from expectations.
