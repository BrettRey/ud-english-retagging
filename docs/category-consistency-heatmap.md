# Category Consistency Heatmap

## Goal

Measure whether tokens assigned to a category occupy a coherent structural neighborhood, while minimizing distortion from:

- unequal category size
- very high-frequency lexemes
- corpus/register mixture
- circular reuse of features that directly drove the annotation

This is a diagnostic for **distributional coherence given a feature set**, not a direct proof of category validity. A clean diagonal can simply show that the rule system encoded a distinction deterministically; a diffuse row can simply show that a category is structurally broad by design. In particular, a diffuse row for `preposition` is much less alarming than a diffuse row for something narrow like `determinative[demonstrative]`.

The **ablated chance-corrected matrix** is the primary analytical artifact. The full-feature matrix is descriptive only.

## What The Heatmap Can And Cannot Show

It can help identify:

- internally diffuse categories
- off-diagonal overlaps worth inspecting
- outlier lexemes
- possible subtype splits
- rule families whose outputs remain coherent even after trigger features are removed

It cannot, by itself, show:

- that a category is theoretically correct
- that a diffuse category is theoretically wrong
- that a rule system has been validated

Those require separate manual or gold-standard evaluation.

## Core Design

Build a nearest-neighbor heatmap from structurally defined context vectors.

For each source item:

1. derive a context vector from local syntactic and morphological properties
2. find its `k` nearest neighbors
3. record the neighbor categories
4. convert those neighbor counts to per-item category proportions
5. average those per-item proportions within the source category

Plot:

- rows = source category
- columns = neighbor category
- value = mean neighbor proportion

Use both:

- `br_cat x br_cat`
- `br_cat:br_subtype x br_cat:br_subtype`

The subtype view is the main view for this project. Broad categories like `preposition`, `pronoun`, and `determinative` are heterogeneous enough that the coarse heatmap is mainly a screening tool.

Column ordering must match row ordering. For subtype matrices, sort by:

1. `br_cat`
2. `br_subtype` alphabetically within `br_cat`

## Anti-Circularity Protocol

This is the main methodological safeguard.

The retagging rules already use many structural features such as:

- `ud_deprel`
- head category
- complement type
- `PronType`
- `Poss`
- `Reflex`

So a full-feature heatmap is not enough. It may only show that the rules are deterministic.

Run two analyses for every matrix:

1. **Full-feature heatmap**
   Useful as a descriptive summary of the current output layer.

2. **Ablated heatmap**
   For each category, subtype, or rule family under inspection, remove the features that directly licensed that output and rerun the analysis.

The ablated run is the actual coherence test.

Examples:

- when testing `subordinator[relative]`, remove direct `PronType=Rel` and explicit relative-clause trigger features
- when testing clausal `preposition` vs `subordinator`, remove complement-type features
- when testing `verb[auxiliary_infinitival]`, remove direct `VerbForm=Inf` and the literal `PART to` cue
- when testing `one`-related outputs, remove the local modifier cues that explicitly license the prop-word rules

The specific ablation map should be stored alongside the analysis code, keyed by rule family.

Here, a **rule family** means a small grouping of related rows in `rules/cgel_retagging.csv` that operationalize the same category distinction or lexical cleanup, such as:

- relative-subordinator rules
- clausal-preposition rules
- infinitival-`to` rules
- `one`-cleanup rules

## Unit Of Comparison

Do not rely on raw token counts alone.

Use three views:

1. **Token-level**
   Useful for the full empirical distribution, but most exposed to frequency skew.

2. **Lexeme-level**
   Average token vectors by `(lemma, br_cat, br_subtype)` first, then compare lexeme centroids.
   This controls for very frequent items such as `the`, `that`, `to`, and `one`.

3. **Corpus-stratified**
   Compute the same heatmaps:
   - within each corpus
   - on the pooled data

This separates category incoherence from genre/register effects.

## Lexeme Centroid Threshold

Lexeme centroids require a minimum token floor.

Default:

- include a lexeme centroid only if `n >= 5`

Below that threshold:

- keep the item in token-level analysis
- report it separately in a sparse-lexeme table

This avoids pretending that items such as `yonder`, `une`, or `whosoever` have stable centroid geometry when they do not.

## Feature Encoding

Use binary one-hot structural features as the default representation.

That means:

- each categorical structural property becomes a binary feature
- each yes/no structural property becomes a binary feature

Do not use TF-IDF as the default for this project. These are not document bags; they are structured categorical observations.

## Recommended Feature Set

Use structural features only, not raw lexical content except in heavily abstracted form.

### Include

- UD relation of the token: `ud_deprel`
- UD relation of the head
- head UPOS
- grandparent UPOS
- previous UPOS
- next UPOS
- whether token has a dependent clause
- whether token has an NP complement
- whether token has no complement
- whether token is preceded by a determiner
- whether token is preceded by an adjective
- whether token is followed by `of`
- whether token is sentence-initial
- whether token is immediately post-comma
- coarse feature flags:
  - `PronType`
  - `Poss`
  - `Reflex`
  - `NumType`
  - `VerbForm`
  - `Foreign`

### Head lemma abstraction

Do not hard-code an ad hoc list of head lemmas.

Instead:

- derive the retained head-lemma inventory from the pooled stabilized overt-form corpora
- keep only head lemmas that occur as heads of target tokens at or above a fixed frequency threshold
- collapse all others to `HEAD_LEMMA_OTHER`

Default threshold:

- keep lemmas occurring as heads of target tokens in at least `1%` of pooled target-token contexts, capped at the top `10` lemmas

Everything else should collapse to a coarse head class or be omitted.

## Exclude

Do not include:

- `br_cat` or `br_subtype` themselves
- rule IDs
- literal rule-trigger feature bundles serialized from the current retagger
- raw word identity of the target token
- broad topical lexical context
- sentence text embeddings

These would make the result circular or genre-driven.

## Distance Metrics

Use more than one metric.

Required:

- cosine on binary one-hot vectors
- Jaccard on binary one-hot vectors

If the category picture changes radically across metrics, treat the result as unstable.

## Neighborhood Size

Results are `k`-sensitive, so do not report a single `k`.

Required values:

- `k = 5`
- `k = 15`
- `k = 50`

Report:

- the matrix for each `k`
- a stability summary across `k`

A pattern should not be treated as robust unless it survives at least two of the three `k` values.

## Normalization

To avoid category-size bias:

1. compute neighbor proportions per source item, not raw neighbor counts
2. average those proportions within the source category
3. balance the number of source items per category by bootstrap resampling

Recommended procedure:

- sample the same number of source items per category
- repeat `200` times by default
- average the resulting matrices
- compute a bootstrap standard deviation matrix

Balanced sample size:

- set `n` to the minimum category size in the matrix
- if that minimum is below `30`, move that category or subtype to a sparse-category table instead of forcing a degenerate balanced bootstrap

## Chance Correction

Produce three matrices:

1. **Raw row-normalized neighbor share**
2. **Balanced row-normalized neighbor share**
3. **Balanced chance-corrected score**

Default chance correction:

- observed minus expected share

Optional secondary score:

- log-odds ratio with additive smoothing `alpha = 0.5`

Observed-minus-expected is the main reporting measure because it is easier to interpret directly.

## Null Baseline

Every reported analysis must include a null baseline.

Required null:

- shuffle category labels within corpus
- preserve category counts within each corpus
- rerun the same nearest-neighbor pipeline

The null baseline must be computed with the same:

- feature set
- ablation state
- `k`
- distance metric
- token-vs-lexeme setting

This gives the baseline diagonal and off-diagonal structure expected from:

- category prevalence
- corpus composition
- the chosen `k`
- the chosen distance metric

Do not call a diagonal "strong" unless it is visibly above the shuffled baseline.

## Diagnostics

Every heatmap should be accompanied by:

- the number of source items per row
- bootstrap uncertainty
- a shuffled-label baseline
- a table of top off-diagonal cells
- nearest-neighbor exemplars for suspicious cells

Without exemplars, the heatmap is too easy to overinterpret.

## High-Risk Item Inspection

These items must be inspected separately rather than trusted blindly in the pooled heatmap:

- `one`
- `that`
- `if`
- `for`
- `there`
- `other`
- `to`

Inspection procedure:

1. break the item down by `br_subtype`
2. compute its nearest neighbors separately at each `k`
3. show the top `10` nearest-neighbor exemplars per subtype
4. compare full-feature and ablated runs
5. record whether the item's behavior is stable across corpora

## Actionability Threshold

The artifact should not be purely descriptive.

A category or subtype should be flagged for rule review if, in the **ablated chance-corrected matrix**:

- an off-diagonal observed-minus-expected value is at least `0.15`
- the same off-diagonal pattern appears at at least two of the three `k` values
- the bootstrap interval does not cross `0`
- the pattern is not reproduced by the shuffled-label baseline

If all four hold, the item goes to explicit review.

If fewer than four hold, keep it as a diagnostic note rather than changing rules immediately.

The `0.15` cutoff is a first-pass placeholder. Recalibrate it after the first full run against the validation subset instead of treating it as a permanent threshold.

## Validation Hook

Internal coherence and gold agreement are different axes.

Where available, compare the heatmap diagnostics against a manually checked subset.

Recommended first validation set:

- the reviewed LinES residue
- plus a stratified random sample from stabilized overt-form corpora

The validation question is not "does the heatmap prove the category", but:

- do the outliers it identifies align with real human-review trouble spots?

## Interpretation Rules

- strong diagonal above null baseline: structurally cohesive category under the chosen feature set
- diffuse row: internally heterogeneous category, broad category, or failed abstraction
- strong off-diagonal cell: possible overlap, unresolved split, or rule leakage

But:

- a diffuse row does not by itself show the category is wrong
- a strong diagonal can simply show that the rule system encoded the distinction cleanly

Treat the heatmap as a way to find:

- outlier lexemes
- possible subtype splits
- suspicious rule interactions
- corpora where a category behaves differently

## Recommended First Pass For This Repo

Run the analysis on the stabilized overt-form corpora only:

- EWT
- GUM
- ATIS
- ParTUT
- GENTLE
- CTeTex
- littleprince
- pronouns
- PUD

Exclude:

- GUMReddit
- LinES from the main pooled stability pass

Then run LinES separately as a diagnostic corpus because it still contains a residual review queue.

Required first-pass settings:

- subtype level first: `br_cat:br_subtype`
- token-level and lexeme-centroid versions
- balanced bootstrap resampling
- full-feature and ablated versions
- pooled and per-corpus outputs
- `k` in `{5, 15, 50}`
- cosine and Jaccard

For the current data, the most useful questions are:

- whether `preposition[intransitive]` is internally coherent after ablation
- whether `subordinator` splits cleanly from clausal `preposition`
- whether determinative subtypes cluster distinctly
- whether the residual `one` cases in LinES form recoverable subgroups

## Compute Considerations

The full grid is expensive:

- pooled and per-corpus
- token and lexeme-centroid
- full and ablated
- `k` in `{5, 15, 50}`
- cosine and Jaccard
- `200` bootstrap repetitions

To keep this tractable:

1. cache the distance matrix once per `(feature set, ablation state, metric, token-vs-lexeme setting, corpus slice)` combination
2. derive the different `k` neighborhoods from that cached matrix
3. reuse the same cached feature matrices across bootstrap runs

If the standard library proves too slow, the allowed numerical dependency should be:

- `numpy`
- `scipy.spatial`

## Tie Handling

Sparse binary vectors, especially under Jaccard, can generate many tied distances.

Tie policy:

1. sort neighbors first by distance
2. break exact ties by stable token or centroid identifier
3. record the tie count at the `k` boundary

If boundary ties are frequent for a given configuration, report that instability explicitly and prefer the cosine result for interpretation.

## Minimal Output Set

An implementation should emit:

- `ablation_map.tsv`
- `heatmap_coarse_pooled_full.tsv`
- `heatmap_coarse_pooled_ablated.tsv`
- `heatmap_subtype_pooled_full.tsv`
- `heatmap_subtype_pooled_ablated.tsv`
- `heatmap_subtype_by_corpus_full.tsv`
- `heatmap_subtype_by_corpus_ablated.tsv`
- `heatmap_subtype_chance_corrected_full.tsv`
- `heatmap_subtype_chance_corrected_ablated.tsv`
- `heatmap_subtype_bootstrap_stddev_full.tsv`
- `heatmap_subtype_bootstrap_stddev_ablated.tsv`
- `heatmap_subtype_null_baseline_full.tsv`
- `heatmap_subtype_null_baseline_ablated.tsv`
- `off_diagonal_outliers.tsv`
- `nearest_neighbor_exemplars.tsv`
- `high_risk_lexeme_breakdown.tsv`
- `sparse_category_table.tsv`
- `sparse_lexeme_table.tsv`

PNG or SVG plots can come after the TSV layer.
