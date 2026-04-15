# CLAUDE.md — UD English Retagging

## Role: Developer / Corpus Engineer

## Project Overview

**Goal:** Build a parallel annotation layer for UD English corpora that retags selected CGEL/UD mismatch classes according to CGEL-aligned categories. This is a corpus engineering project, not a paper.

**Approach:** Deterministic rule-based retagging with manual adjudication of residual cases. Parallel layer (not overwriting UD tags). The current stabilized layer covers EWT `dev`/`test`/`train`, GUM `dev`/`test`/`train`, ATIS `dev`/`test`/`train`, `en_gentle-ud-test`, `en_ctetex-ud-test`, `en_littleprince-ud-test`, `en_pronouns-ud-test`, and `en_pud-ud-test` using sidecar TSV output and a CSV rule table. GUMReddit is frozen at partial coverage through a structural fallback layer plus narrow MISC-hint recovery because its surface FORM/LEMMA columns are delexicalized.

## Annotation Layer

Primary output goes in sidecar TSV. A MISC-column export can come later if needed. `sentence_text` is optional via `--include-text` for review-oriented runs. Schema:

```
BR_CAT=determinative       # CGEL-aligned category
BR_SUBTYPE=interrogative_wh # subcategory
BR_STATUS=auto|reviewed     # provenance
```

Keep original UPOS, XPOS, DEPREL intact.

## Target Categories

Priority retags in the current EWT/GUM-stabilized layer:

1. **Pronouns vs determinatives** — including headed vs fused-head contrasts where needed
2. **Marker-like uses of `both`, `either`, and `neither`** — still determinatives despite UD `CCONJ`/`ADV` tags
3. **Numeratives** — cardinals as determinatives, ordinal adjectives, and fractional nouns
4. **Clear coordinators, including UD coordinator-like `yet` as `coordinator[adversative]`**
5. **UD coordinator-like `as well as` as `coordinator[additive]`**
6. **UD coordinator-like `rather than` as `coordinator[rather_than]`**
7. **`along with` as `preposition`, including clause-introducing uses**
8. **`SCONJ` items as prepositions with clausal complements**
9. **Relative and declarative `that`, `whether`, complement `if` including coordinated complement uses, and infinitival `for` as subordinators**
10. **Infinitival `to` as `verb[auxiliary_infinitival]`**
11. **`ADV` items in the current intransitive-preposition set as intransitive prepositions, including the appendix-backed tranche `out`, `in`, `over`, `ago`, `before`, `once`, `forward`, `ahead`, `apart`, `hence`, and `forth`**
12. **Contracted `n't` as `morpheme[negative_enclitic]`**
13. **`so/SCONJ` auto-tagged as `preposition[clausal]`; compound indefinite items like `someone` and `nothing`, plus `whatever`, `whichever`, `other`, `such`, DET-tagged `quite`, dialectal determiner `them`, expressive `wtf`, `et al.`, and clause-marking `rather than` are normalized**
14. **Low-frequency extensions already seen in GUM and later corpora are normalized into existing categories: `whosoever`, `oneself`, singular `s/he`, marginal determinative `yonder` plus prepositional `yonder`, foreign `une`, non-existential `there`, tokenized `self` in `self-` compounds, bare generic `one`, partitive `one of`, relative `that`/`which` recoverable from clause structure, and `where`/`when` as intransitive prepositions**
15. **Dependent possessive `DET` items remain pronouns.** When UD tags forms like `my`, `your`, `their`, or `its` as `DET`, the sidecar still maps them to `pronoun[possessive]`
16. **Delexicalized structural fallback for corpora like GUMReddit: articles, demonstratives, quantificational determinatives, personal pronouns, possessives, reflexives, indefinites, and expletives can still be recovered from features and dependencies even when lexical identity is hidden**
17. **Narrow delexicalized MISC-hint recovery for GUMReddit:** segmented `what-ever`, relative `that`, relative `which`, short relative `who`/`whom`, and typo-corrected single-token items can be recovered when raw FORM/LEMMA are `_`; hints must not override overt lexical forms in ordinary corpora

**Deferred / partial:** the original temporal-noun assumption does not hold in EWT. The `ADV -> preposition` layer now includes a broader appendix-backed corpus subset in current use, but it is still a lexically enumerated rule layer rather than a general structural analysis of every preposition use.

## Source Data

All 16 UD English corpora are symlinked in `data_raw/` from `corpora/ud-english/`. Format: CoNLL-U.

**Current covered target:**
- **ewt** — `en_ewt-ud-dev.conllu`, `en_ewt-ud-test.conllu`, `en_ewt-ud-train.conllu`
- **gum** — `en_gum-ud-dev.conllu`, `en_gum-ud-test.conllu`, `en_gum-ud-train.conllu`
- **atis** — `en_atis-ud-dev.conllu`, `en_atis-ud-test.conllu`, `en_atis-ud-train.conllu`
- **gentle** — `en_gentle-ud-test.conllu`
- **ctetex** — `en_ctetex-ud-test.conllu`
- **littleprince** — `en_littleprince-ud-test.conllu`
- **pronouns** — `en_pronouns-ud-test.conllu`
- **pud** — `en_pud-ud-test.conllu`
- **gumreddit** — `en_gumreddit-ud-dev.conllu`, `en_gumreddit-ud-test.conllu`, `en_gumreddit-ud-train.conllu` (frozen partial structural coverage only)

**Next targets after the EWT/GUM/ATIS/GENTLE/PUD/pronouns/littleprince pass:**
- additional corpora with overt lexical forms, preferably `partut`, `lines`, or `pcedt`

**Additional corpora:**
- **atis** — Air Travel Information System
- **childes** — child language (CHILDES)
- **ctetex** — CTeTex
- **esl** — English as a second language
- **eslspok** — ESL spoken
- **gentle** — GENTLE corpus
- **lines** — parallel corpus (English side)
- **littleprince** — The Little Prince
- **partut** — parallel treebank
- **pcedt** — Prague Czech-English Dependency Treebank
- **pronouns** — pronoun-focused dataset
- **pud** — Parallel Universal Dependencies
- **unidive** — UniDive project

## Pipeline Components

1. **Rule table** — `rules/cgel_retagging.csv`
2. **Retagger** — `scripts/retag.py` reads CoNLL-U and writes sidecar TSV
3. **Audit** — `scripts/audit.py` produces counts, review totals, and exception summaries

## Related Projects

- `tools/CGELbank/` — existing CGELBank annotation work
- `papers/Personhood_and_proforms/` — pro-form inventory and gender hierarchy
- `papers/English_kinship_terms/` — submitted to JoEL
- `.house-style/style-rules.yaml` — CGEL terminology conventions

## Build / Run

Python. MVP should run with the standard library only.

```bash
python scripts/retag.py ../../corpora/ud-english/ewt/en_ewt-ud-dev.conllu --rules rules/cgel_retagging.csv --output data_derived/en_ewt-ud-dev.cgel.tsv
python scripts/retag.py ../../corpora/ud-english/ewt/en_ewt-ud-dev.conllu --rules rules/cgel_retagging.csv --output data_derived/en_ewt-ud-dev.cgel.tsv --include-text
python scripts/audit.py data_derived/en_ewt-ud-dev.cgel.tsv --output audit/en_ewt-ud-dev.cgel.txt
python -m unittest discover -s tests
```
