# STATUS.md

**Status:** EWT, GUM, ATIS, GENTLE, CTeTex, pronouns, and PUD stabilized; GUMReddit frozen as partial coverage
**Created:** 2026-04-14
**Last updated:** 2026-04-14

## Current State

The project now has a working CGEL-aligned sidecar pipeline across all EWT splits, all GUM splits, all ATIS splits, `en_gentle-ud-test`, `en_ctetex-ud-test`, `pronouns`, `PUD`, and a frozen partial-coverage GUMReddit layer.

Implemented:

- `rules/cgel_retagging.csv` — active CSV rule table for the current scope
- `scripts/retag.py` — standard-library CoNLL-U reader that writes sidecar TSV
- `scripts/audit.py` — audit report generator for the sidecar output
- `tests/test_pipeline.py` — lightweight regression tests for retagging and audit behavior
- `data_derived/en_ewt-ud-dev.cgel.tsv`
- `data_derived/en_ewt-ud-test.cgel.tsv`
- `data_derived/en_ewt-ud-train.cgel.tsv`
- `data_derived/en_gum-ud-dev.cgel.tsv`
- `data_derived/en_gum-ud-test.cgel.tsv`
- `data_derived/en_gum-ud-train.cgel.tsv`
- `data_derived/en_gumreddit-ud-dev.cgel.tsv`
- `data_derived/en_gumreddit-ud-test.cgel.tsv`
- `data_derived/en_gumreddit-ud-train.cgel.tsv`
- `data_derived/en_pronouns-ud-test.cgel.tsv`
- `data_derived/en_pud-ud-test.cgel.tsv`
- `data_derived/en_atis-ud-dev.cgel.tsv`
- `data_derived/en_atis-ud-test.cgel.tsv`
- `data_derived/en_atis-ud-train.cgel.tsv`
- `data_derived/en_gentle-ud-test.cgel.tsv`
- `data_derived/en_ctetex-ud-test.cgel.tsv`
- `audit/en_ewt-ud-dev.cgel.txt`
- `audit/en_ewt-ud-test.cgel.txt`
- `audit/en_ewt-ud-train.cgel.txt`
- `audit/en_gum-ud-dev.cgel.txt`
- `audit/en_gum-ud-test.cgel.txt`
- `audit/en_gum-ud-train.cgel.txt`
- `audit/en_gumreddit-ud-dev.cgel.txt`
- `audit/en_gumreddit-ud-test.cgel.txt`
- `audit/en_gumreddit-ud-train.cgel.txt`
- `audit/en_pronouns-ud-test.cgel.txt`
- `audit/en_pud-ud-test.cgel.txt`
- `audit/en_atis-ud-dev.cgel.txt`
- `audit/en_atis-ud-test.cgel.txt`
- `audit/en_atis-ud-train.cgel.txt`
- `audit/en_gentle-ud-test.cgel.txt`
- `audit/en_ctetex-ud-test.cgel.txt`

Current covered mismatch classes:

- pronoun vs determinative
- marker-like uses of `both`, `either`, and `neither` retained as determinatives even when UD tags them `CCONJ` or `ADV`
- numeratives following the current paper-level analysis:
  word-form cardinals as determinatives, magnitude factors as determinatives, fused-head numeral uses as determinatives, ordinals as adjectives, and fractionals such as `half` as nouns
- clear coordinators retagged as coordinators (`and`, `but`, `or`, `nor`, `plus`, slash as `cc`, and `yet` when UD tags it as `CCONJ/cc`)
- UD coordinator-like `as well as` retagged as `coordinator[additive]`
- UD coordinator-like `rather than` retagged as `coordinator[rather_than]`
- `along with` retagged as `preposition`, with NP uses treated as `complex_with` and clause-introducing uses treated as `clausal`
- most `SCONJ` items retagged as prepositions with clausal complements
- relative and declarative/content `that` retagged as subordinators
- `whether` retagged as subordinator
- clear complement-clause `if`, including coordinated complement-clause uses, retagged as subordinator via a head-dependency heuristic
- infinitival `for` retagged as subordinator
- infinitival `to` retagged as a verb (`auxiliary_infinitival`)
- `ADV` items in the current intransitive-preposition set retagged as prepositions
- dependent possessive `DET` items like `my`, `your`, `their`, and `its` retained as `pronoun[possessive]`
- contracted `n't` retagged as `morpheme[negative_enclitic]`
- `so/SCONJ` retagged as `preposition[clausal]` for the current purpose/result uses covered by UD `SCONJ`
- clause-marking `rather than` retagged as `preposition[clausal]`
- `whatever` retagged as `determinative` across headed and fused-head uses
- `whichever` retagged as `determinative`
- compound indefinite items like `someone`, `something`, `nothing`, `anyone`, and `everyone` retagged as `determinative`
- `other` retagged as `adjective`
- `such` retagged as `adjective`
- DET-tagged `quite` retagged as `adverb[degree]`
- dialectal determiner `them` retagged as `determinative`
- expressive `wtf` retagged as a headless determinative
- `et` in `et al.` retagged as `coordinator[additive]`
- low-frequency GUM extensions normalized into existing categories: `whosoever`, `oneself`, singular `s/he`, marginal determinative `yonder`, and foreign `Une`
- non-determiner `yonder` retagged as `preposition[intransitive]`
- non-existential `there` retagged as `preposition[intransitive]`, with existential `there` remaining a pronoun
- tokenized `self` in `self-` compounds retagged as `noun[self_compound_initial]`
- bare `one/PRON` can be recovered as generic pronoun even when UD omits `PronType=Prs`
- `one/PRON` followed by `of` is treated as a fused-head cardinal determinative
- relative `that` can still be recovered as `subordinator[relative]` when UD omits `PronType=Rel` but enhanced dependencies mark `ref`
- relative `that` and `which` can also be recovered structurally from relative-clause attachment even when features are missing or the pronoun is attached inside an `xcomp`
- `where/PRON` is treated as `preposition[intransitive]`
- `when/PRON` is treated as `preposition[intransitive]`
- delexicalized fallback rules for corpora like GUMReddit: structurally recoverable articles, demonstratives, quantificational determinatives, personal pronouns, possessives, reflexives, indefinites, and expletives can be auto-tagged even when FORM/LEMMA are anonymized
- selected delexicalized wh-items can now be recovered from MISC hints when the signal is narrow enough: segmented `what-ever`, relative `that`, relative `which`, and short relative `who`/`whom` patterns
- delexicalized MISC hints only backfill lexical identity when raw FORM/LEMMA are missing, so typo metadata in ordinary corpora does not destabilize the EWT/GUM layer

The `data_raw/` symlink layer has also been corrected so the local corpus mirrors now resolve to the actual `../../corpora/ud-english/` tree.

Current EWT results:

- `dev`: 6,007 rows, 6,007 auto, 0 review
- `test`: 5,893 rows, 5,893 auto, 0 review
- `train`: 51,768 rows, 51,768 auto, 0 review

The remaining review burden in EWT is now zero.

Current GUM results:

- `dev`: 7,233 rows, 7,233 auto, 0 review
- `test`: 7,037 rows, 7,037 auto, 0 review
- `train`: 43,739 rows, 43,738 auto, 1 review

The remaining review burden is now limited to one GUM-train token:

- `Mat` in a foreign quoted name (`Mat Fereder`)

Current GUMReddit results:

- `dev`: 398 rows, 391 auto, 7 review
- `test`: 415 rows, 409 auto, 6 review
- `train`: 2,799 rows, 2,760 auto, 39 review

GUMReddit remains only partially covered because the corpus is delexicalized: FORM and LEMMA are `_`, so the lexeme-driven rules cannot distinguish many remaining closed-class items directly. The current structural fallback layer plus narrow MISC-hint recovery cuts the review burden sharply, but GUMReddit is still not comparable to the overt-form corpora and is now treated as frozen partial coverage unless undelexicalized text becomes available.

The GUMReddit row count rose slightly in `test` and `train` because the hint-backed matching now also recovers a few non-`DET`/`PRON` items whose lexical identity is visible only in metadata, such as `n't`, infinitival `to`, and a handful of typo-corrected subordinators or possessives.

Anonymous fallback behavior has been eliminated from the current EWT outputs and from all but one token in GUM. GUMReddit still has a real residual review queue due to corpus delexicalization. Sidecar TSV omits sentence text by default; `--include-text` is available for manual review workflows.

Current `pronouns` results:

- `test`: 590 rows, 590 auto, 0 review

Current `PUD` results:

- `test`: 4,548 rows, 4,548 auto, 0 review

Current `ATIS` results:

- `dev`: 1,195 rows, 1,195 auto, 0 review
- `test`: 1,107 rows, 1,107 auto, 0 review
- `train`: 8,244 rows, 8,244 auto, 0 review

Current `GENTLE` results:

- `test`: 3,685 rows, 3,685 auto, 0 review

Current `CTeTex` results:

- `test`: 1,601 rows, 1,601 auto, 0 review

## Next Steps

- [x] Symlink UD English corpora to `data_raw/` (16 corpora linked from `corpora/ud-english/`)
- [x] Review and finalize the execution plan in `docs/plan-evaluation.md`
- [x] Create the initial rule table
- [x] Rename the active rule table to `rules/cgel_retagging.csv`
- [x] Implement `scripts/retag.py`
- [x] Implement `scripts/audit.py`
- [x] Add lightweight regression tests in `tests/test_pipeline.py`
- [x] Run EWT `dev` / `test` / `train`
- [x] Retag relative `that` as `subordinator`
- [x] Retag `SCONJ` items as `preposition` with clausal complements
- [x] Retag infinitival `for` as `subordinator`
- [x] Retag infinitival `to` as `verb[auxiliary_infinitival]`
- [x] Expand the `ADV -> preposition[intransitive]` layer to the broader EWT set
- [x] Retag the clear coordinator inventory as `coordinator`
- [x] Retag UD coordinator-like `yet` as `coordinator[adversative]`
- [x] Retag UD coordinator-like `as well as` as `coordinator[additive]`
- [x] Retag UD coordinator-like `rather than` as `coordinator[rather_than]`
- [x] Retag `along with` as `preposition`
- [x] Surface marginal coordinator candidates as explicit review items where token-local rules can identify them
- [x] Align numeratives with the current paper-level analysis
- [x] Represent contracted `n't` as `morpheme[negative_enclitic]` in the sidecar layer
- [x] Retag `so/SCONJ` as `preposition[clausal]`
- [x] Resolve `along with` as a preposition pattern rather than a coordinator review item
- [x] Retag `whatever` as `determinative`
- [x] Retag DET-tagged `quite` as `adverb[degree]`
- [x] Retag dialectal determiner `them` as `determinative`
- [x] Retag expressive `wtf` as a headless determinative
- [x] Retag `et` in `et al.` as `coordinator[additive]`
- [x] Retag clause-marking `rather than` as `preposition[clausal]`
- [x] Extend the stabilized rule table to GUM
- [x] Extend the rule table to partially cover delexicalized GUMReddit via structural fallback rules
- [x] Freeze GUMReddit as partial coverage rather than forcing deeper lexical guesses
- [x] Extend the stabilized rule table to `pronouns`
- [x] Extend the stabilized rule table to `PUD`
- [x] Extend the stabilized rule table to `ATIS`
- [x] Extend the stabilized rule table to `GENTLE`
- [x] Extend the stabilized rule table to `CTeTex`
- [x] Retag `other` as `adjective`
- [ ] Adjudicate the remaining GUM-train residue (`Mat` in the quoted foreign string `Mat Fereder`)
- [ ] Extend the stabilized rule table to the next overt-form corpus
