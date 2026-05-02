# SIA Research Foundation

## 1. Research Question

**Primary hypothesis (H1):**
A structured persona-ensemble prioritisation layer, theoretically motivated by cross-cultural value research (Schwartz, WVS), produces signal prioritisation that is:
- (a) more auditable than single-prompt LLM baselines (measured by intermediate-step reproducibility under reseed),
- (b) more divergence-aware — surfaces genuine tensions that single-prompt approaches flatten (measured by correlation with known contested issues in retrospective datasets),
- (c) less sensitive to designer bias than hand-crafted weighting systems (measured by inter-encoder agreement: ICC >= 0.7 across 3 independent weight-matrix encodings),

when tested against retrospective expert consensus, deliberative assembly outcomes, or longitudinal event salience.

**Secondary hypothesis (H2):**
The same prioritisation engine, with only its domain profile changed (no structural code changes), produces valid prioritisation across structurally different domains (world affairs, code triage, community health, product decisions).

**Null hypothesis (H0):**
A single well-prompted LLM produces prioritisation statistically indistinguishable from the persona-ensemble approach (Kendall τ > 0.85, n >= 50 signals, p < 0.05), making the ensemble layer unnecessary overhead.

**Pre-registration requirement:**
All hypothesis tests, effect sizes, sample sizes, and primary endpoints must be specified before experiments run. H0 rejection requires pre-registered statistical criteria, not post-hoc comparison.

**Target construct (explicit choice):**
SIA's prioritisation is **descriptive-pluralistic** — it models how a diverse human collective WOULD prioritise, not what SHOULD be prioritised. The ensemble is a simulation of collective judgment, not a normative ethical framework. Where descriptive and normative findings diverge, both are reported.

**What would falsify H1:**
If 3 independently designed persona weight matrices (produced from the same Schwartz/WVS source material by different encoders) produce priority rankings with ICC < 0.7, the system is measuring the designer, not the world. This ablation MUST run before any other experiment.

**What would falsify H2:**
If the engine requires domain-specific structural changes (not just config) to work on a second domain.

**What would reject H0:**
If the persona-ensemble approach fails to beat a single well-prompted LLM by Kendall τ margin > 0.15 on the pre-registered primary endpoint, H0 stands and the ensemble is overhead.

---

## 2. Theoretical Foundations

### 2.1 Schwartz Theory of Basic Human Values (empirically validated across 80+ countries)

Shalom Schwartz identified 10 universal value types, organised in a circular motivational structure where adjacent values are compatible and opposing values conflict:

| Value type | Core motivation | Adjacent to | Opposes |
|---|---|---|---|
| **Self-Direction** | Independent thought, creativity, freedom | Stimulation, Universalism | Conformity, Tradition, Security |
| **Stimulation** | Excitement, novelty, challenge | Self-Direction, Hedonism | Security, Conformity |
| **Hedonism** | Pleasure, sensuous gratification | Stimulation, Achievement | Conformity, Tradition |
| **Achievement** | Personal success, competence | Hedonism, Power | Benevolence, Universalism |
| **Power** | Social status, dominance, control | Achievement, Security | Universalism, Benevolence |
| **Security** | Safety, stability, order | Power, Conformity | Self-Direction, Stimulation |
| **Conformity** | Restraint, obedience, politeness | Security, Tradition | Self-Direction, Stimulation, Hedonism |
| **Tradition** | Respect for customs, religion, heritage | Conformity, Benevolence | Hedonism, Stimulation, Self-Direction |
| **Benevolence** | Welfare of close others, loyalty | Tradition, Universalism | Power, Achievement |
| **Universalism** | Understanding, tolerance, justice for all | Benevolence, Self-Direction | Power, Achievement |

**Why this matters for SIA:** These 10 values are not invented categories — they're empirically derived from cross-cultural studies of 70,000+ respondents. A persona's value profile determines HOW they prioritise signals. A Security-dominant persona treats stability threats as existential. A Universalism-dominant persona treats justice violations the same way.

### 2.2 Inglehart-Welzel Cultural Map (World Values Survey)

The WVS maps societies along two empirical axes:

1. **Traditional vs Secular-Rational values**
   - Traditional: religion, deference to authority, national pride, obedience
   - Secular-Rational: rationality, tolerance, less emphasis on authority/religion

2. **Survival vs Self-Expression values**
   - Survival: economic/physical security, intolerance of outsiders, low trust
   - Self-Expression: environmental protection, gender equality, political participation, tolerance

Societies cluster into cultural zones: Protestant Europe, Catholic Europe, Confucian, South Asian, African-Islamic, Latin American, English-speaking, Orthodox.

**Why this matters:** Persona archetypes should align with these empirically observed clusters, not invented cultural categories. A "South Asian aspirational pragmatist" is real — it maps to the South Asian cluster (moderate traditional, high survival-to-self-expression transition).

### 2.3 Maslow's Hierarchy (as a prioritisation ordering, not a rigid pyramid)

Maslow's contribution to SIA is not the pyramid itself (which has been criticised for its rigidity and Western bias) but the insight that **prioritisation changes with unmet needs:**

- When physiological/safety needs are unmet, EVERYTHING else is deprioritised
- When basic needs are met, social, esteem, and self-actualisation concerns rise
- This ordering varies by culture (collectivist societies may prioritise belonging over individual safety)

**For SIA:** A persona's position on the needs spectrum affects not just WHAT they prioritise but WHETHER they even perceive a signal as relevant. A food-insecure farmer doesn't deprioritise a tech regulation story — they literally don't see it.

### 2.4 Multi-Criteria Decision Analysis (MCDA) — what exists vs what SIA adds

Existing frameworks (AHP, MAUT, ELECTRE, PROMETHEE) do stakeholder-weighted prioritisation. SIA is not the first to propose this.

**What SIA adds (or must add to be novel):**
1. **Empirically grounded persona weights** from cross-cultural value surveys (not designer intuition)
2. **Divergence as a first-class output** — existing MCDA produces a single ranking; SIA surfaces WHERE reasonable people disagree
3. **LLM-powered signal classification** — existing MCDA requires manual attribute scoring; SIA automates extraction
4. **Cyclic feedback** — existing MCDA is one-shot; SIA learns from outcomes
5. **Domain generality** — existing MCDA is designed per-problem; SIA uses the same engine across domains

---

## 3. Persona Archetype Design (Theoretically Motivated)

### 3.1 Derivation method

**Status: theoretically motivated, empirically testable — NOT empirically grounded.**

These are provisional synthetic stakeholders, not demographic truths. Each archetype is motivated by Schwartz value theory and WVS cultural patterns, but the specific weight vectors require:
1. Independent multi-encoder validation (3+ encoders, ICC >= 0.7)
2. Comparison against survey-derived cluster centroids where available
3. Sensitivity analysis showing outputs are robust to reasonable weight perturbation

**Future empirical grounding path:** Fit latent classes on Schwartz PVQ + WVS individual-level microdata, choose k by stability/BIC, define archetypes from cluster centroids. Until this is done, the archetypes are normative seeds, not empirical facts.

Instead of inventing categories, archetypes are constructed from separate factor layers:
1. **Value profile** (from Schwartz circumplex position)
2. **Resource/security profile** (from Maslow-adjacent material position — modeled as attention_capacity + material_precarity, not a rigid hierarchy)
3. **Institutional position** (relationship to power structures)
4. **Domain knowledge** (what expertise shapes perception)
5. **Identity/context modifiers** (lived experience that changes salience)

**Choice of Schwartz over alternatives:**
Schwartz's 10-value model is chosen for tractability and cross-cultural validation breadth (80+ countries, 70,000+ respondents). Alternatives considered:
- Haidt's Moral Foundations (more politically discriminating but less cross-culturally validated)
- Hofstede's cultural dimensions (society-level, not individual-level — ecological fallacy risk)
- Big Five personality traits (dispositional, not value-oriented)

The engine architecture is framework-agnostic: swapping Schwartz for Moral Foundations changes the weight matrix, not the engine. Comparative experiments using at least two value frameworks are planned for Phase 4.

**Operational encoding procedure (required before implementation):**
1. For each archetype, take the dominant Schwartz values already listed in §3.2.
2. Convert those values into structural-dimension loadings using the pre-registered Schwartz-to-dimension mapping table below. This table is derived from published Schwartz value definitions plus the dimension definitions in §4.1; it is the canonical seed mapping for Phase 1.
3. Apply dominance coefficients by value order: 3 values -> `[0.5, 0.3, 0.2]`, 2 values -> `[0.6, 0.4]`, 1 value -> `[1.0]`.
4. Compute the archetype's unnormalised dimension vector as the weighted average of its dominant value loadings:

   ```
   raw_persona_weight[a, dim] = sum(
     dominance_coeff[a, v] * schwartz_dimension_loading[v, dim]
     for v in dominant_values[a]
   )
   ```

5. Normalise the resulting dimension weights so the sum of absolute values equals 1.0. In Phase 1 all persona dimension weights are non-negative salience weights, so this reduces to a simple sum-to-1 normalisation:

   ```
   persona_weight[a, dim] = raw_persona_weight[a, dim] / sum(abs(raw_persona_weight[a, *]))
   ```

6. Set meta-feature weights to uniform by default: `persona_meta_weight[a, meta] = 1/6`. Domain tuning is allowed later, but the six meta-feature weights must still sum to 1.0 for each archetype.
7. Require 3 independent encoders to create the full Schwartz-to-dimension table and resulting archetype matrix without seeing each other's work. Measure inter-encoder agreement with ICC(2,k); the encoding is not accepted unless ICC >= 0.7.
8. Store both the raw encoder tables and the consensus-normalised matrix in version control so the transformation is auditable end-to-end.

**Pre-registered Schwartz-to-dimension mapping table (seed matrix):**

| Schwartz value | Structural-dimension loadings |
|---|---|
| **Self-Direction** | individual_autonomy 0.9; knowledge_capability 0.8; institutional_trust 0.2 |
| **Stimulation** | individual_autonomy 0.8; knowledge_capability 0.6; economic_stability 0.2 |
| **Hedonism** | individual_autonomy 0.6; economic_stability 0.3; social_cohesion 0.1 |
| **Achievement** | economic_stability 0.7; knowledge_capability 0.7; institutional_trust 0.3; individual_autonomy 0.3 |
| **Power** | institutional_trust 0.7; economic_stability 0.6; physical_safety 0.4; social_cohesion 0.2 |
| **Security** | physical_safety 0.9; economic_stability 0.8; institutional_trust 0.6; social_cohesion 0.3 |
| **Conformity** | institutional_trust 0.8; social_cohesion 0.7; physical_safety 0.4; collective_welfare 0.3 |
| **Tradition** | social_cohesion 0.6; environmental_continuity 0.6; institutional_trust 0.5; collective_welfare 0.3 |
| **Benevolence** | collective_welfare 0.9; social_cohesion 0.8; physical_safety 0.4; institutional_trust 0.2 |
| **Universalism** | collective_welfare 0.9; environmental_continuity 0.8; institutional_trust 0.6; social_cohesion 0.5; individual_autonomy 0.4 |

**Worked example (A15: Parent of young children — Benevolence + Security + Conformity):**

```
raw_persona_weight[A15] =
  0.5 * Benevolence +
  0.3 * Security +
  0.2 * Conformity

= {
  physical_safety: 0.55,
  economic_stability: 0.24,
  institutional_trust: 0.44,
  social_cohesion: 0.63,
  collective_welfare: 0.51
}

persona_weight[A15] = raw / 2.37
= {
  physical_safety: 0.232,
  economic_stability: 0.101,
  institutional_trust: 0.186,
  social_cohesion: 0.266,
  collective_welfare: 0.215
}
```

This procedure replaces any intuitive hand-assignment of persona vectors. If later empirical latent-class fitting produces cluster centroids, those centroids supersede this seed matrix, but the same normalisation and audit rules still apply.

### 3.2 Proposed archetypes (36, not 100)

Grouped into 9 clusters of 4 archetypes each:

**Cluster 1: Survival-focused (basic needs at risk)**
- A1: Subsistence farmer, traditional, Global South — Security + Conformity dominant
- A2: Displaced refugee, stateless — Security + Benevolence dominant
- A3: Urban informal worker, precarious — Security + Self-Direction tension
- A4: Chronically ill / disabled, dependent on systems — Security + Benevolence dominant

**Cluster 2: Stability-seeking (basic needs met, building security)**
- A5: Factory/logistics worker, union-adjacent — Security + Conformity + Achievement
- A6: Retired pensioner, fixed income — Security + Tradition + Conformity
- A7: Small business owner, local — Security + Achievement + Self-Direction
- A8: Public school teacher, modest income — Benevolence + Universalism + Security

**Cluster 3: Achievement-oriented (mobile, competitive)**
- A9: Corporate professional, upwardly mobile — Achievement + Power + Self-Direction
- A10: Tech entrepreneur, high-risk high-reward — Stimulation + Achievement + Self-Direction
- A11: Finance/investment professional — Power + Achievement + Security
- A12: Military/security professional — Security + Power + Conformity

**Cluster 4: Care-oriented (welfare of others drives priorities)**
- A13: Healthcare worker, frontline — Benevolence + Universalism + Security
- A14: Social worker / caseworker — Benevolence + Universalism
- A15: Parent of young children — Benevolence + Security + Conformity
- A16: Community organiser, volunteer-driven — Universalism + Benevolence + Self-Direction

**Cluster 5: Knowledge-oriented (truth and capability drive priorities)**
- A17: Research scientist / academic — Universalism + Self-Direction + Stimulation
- A18: Journalist / investigator — Self-Direction + Universalism + Stimulation
- A19: Senior engineer / technical architect — Self-Direction + Achievement + Security
- A20: Legal professional / judge — Universalism + Conformity + Security

**Cluster 6: Governance-oriented (order and institutions drive priorities)**
- A21: Elected politician / policymaker — Power + Achievement + Conformity
- A22: Public servant / regulator — Conformity + Security + Universalism
- A23: Diplomat / international organisation — Universalism + Conformity + Achievement
- A24: Religious leader / moral authority — Tradition + Benevolence + Conformity

**Cluster 7: Sovereignty/order-oriented (stability, identity, and authority drive priorities)**
- A25: Nationalist majoritarian voter — Security + Conformity + Power
- A26: Law-and-order conservative — Security + Conformity + Tradition
- A27: Anti-globalisation protectionist — Security + Self-Direction + Conformity
- A28: Status-preserving elite / establishment — Power + Security + Achievement

**Cluster 8: Expression-oriented (meaning, identity, and rights drive priorities)**
- A29: Artist / cultural producer — Self-Direction + Stimulation + Universalism
- A30: Student / young activist — Universalism + Stimulation + Self-Direction
- A31: Indigenous rights advocate — Tradition + Universalism + Self-Direction
- A32: LGBTQ+ rights advocate in restrictive context — Self-Direction + Universalism + Security

**Cluster 9: Ecosystem-oriented (long-term systems drive priorities)**
- A33: Environmental scientist / climate researcher — Universalism + Self-Direction
- A34: Farmer / land steward, sustainability-oriented — Universalism + Security + Tradition
- A35: Urban planner / infrastructure designer — Achievement + Universalism + Security
- A36: Elder / intergenerational steward — Tradition + Universalism + Benevolence

### 3.3 Why 36 and not 100

- Each archetype is theoretically motivated — maps to Schwartz profiles and WVS cultural positions
- Includes both "morally admirable" AND "morally uncomfortable" perspectives — nationalist, authoritarian, elite status-preserving. Their exclusion would be bias.
- 36 is computationally trivial for matrix scoring
- Can be expanded with empirical justification (survey-derived clusters)
- **These are provisional synthetic stakeholders pending empirical derivation from survey data**

---

## 4. Structural Dimensions (Signal Classification)

### 4.1 Core dimensions (derived from established frameworks)

Instead of inventing 8 dimensions, derive from the intersection of Schwartz values and Maslow needs:

| Dimension | Grounded in | What it captures |
|---|---|---|
| **Physical safety** | Maslow L1-L2, Schwartz Security | Bodily harm, survival threats, environmental danger |
| **Economic stability** | Maslow L2, Schwartz Security+Achievement | Livelihoods, prices, employment, debt, market function |
| **Institutional trust** | Schwartz Conformity+Universalism | Whether systems work, governance credibility, rule of law |
| **Social cohesion** | Schwartz Benevolence+Conformity | Community bonds, intergroup relations, solidarity |
| **Individual autonomy** | Schwartz Self-Direction+Stimulation | Freedom, agency, rights, privacy, self-determination |
| **Collective welfare** | Schwartz Universalism+Benevolence | Equity, access, inclusion, shared prosperity |
| **Knowledge & capability** | Schwartz Self-Direction+Achievement | Innovation, education, information quality, technical capacity |
| **Environmental continuity** | Schwartz Universalism+Tradition | Ecological stability, resource stewardship, intergenerational sustainability |

### 4.2 Meta-features (signal-level, not dimension-level)

| Feature | What it measures |
|---|---|
| **Urgency** | How soon does this demand response? |
| **Scale** | How many people/systems affected? |
| **Irreversibility** | Can this be undone if wrong? |
| **Cascade risk** | Does this trigger failures elsewhere? |
| **Evidence quality** | How well-sourced is this signal? |
| **Actionability** | Can something feasibly be done? |

---

## 5. The Prioritisation Engine (Formal Specification)

### 5.1 Signal classification

Given a raw signal (news story, bug report, complaint, etc.):

1. **LLM extracts** the signal's structural content: what dimensions does it touch, and in what direction (positive/negative/neutral)?
2. Output: a vector of 8 dimension scores plus 6 meta-feature scores with fixed ranges:
   - `signal_score[s, dim] ∈ [-1.0, +1.0]`
   - `signal_meta[s, meta] ∈ [0.0, 1.0]`
3. All signals receive one classification pass. After the first pass, compute `priority_score_single_pass` from the first-pass `priority_raw` values z-scored across the current batch/window. Only the top 20 signals by `priority_score_single_pass` receive 2 additional classification passes with different seeds/temperatures.
4. For those top-20 signals:
   - point estimate = mean across the 3 passes
   - extraction uncertainty = sample standard deviation across the 3 passes
5. Flag any top-20 signal with `final_uncertainty[s] > 0.3` as **UNRELIABLE EXTRACTION** and require manual review before using it in evaluation.

### 5.2 Domain expert layer

For each domain, a domain expert persona is specified:
- **World affairs**: economist — emphasises economic stability, institutional trust, cascade risk
- **Code triage**: senior engineer — emphasises knowledge/capability, physical safety (security), institutional trust (reliability)
- **Community health**: epidemiologist — emphasises physical safety, collective welfare, institutional trust

The expert provides a **dimensional prior** — a weighting over which dimensions are most relevant for this domain. This is multiplicative: it amplifies relevant dimensions without zeroing out others. Expert priors are normalised to mean 1.0 so they change emphasis but do not change the overall scale:

```
expert_prior_raw[d] = {
  "economic_stability": 1.5,
  "institutional_trust": 1.3,
  "physical_safety": 1.0,
  "social_cohesion": 0.8,
  ...
}

expert_prior[d] = expert_prior_raw[d] / mean(expert_prior_raw[*])
```

### 5.3 Persona-ensemble scoring

For each of the 36 archetypes, compute. Persona dimension weights must sum to 1.0 in absolute value; meta-feature weights must sum to 1.0.

```
raw_score[a, s] = sum(
  persona_weight[a, dim] * expert_prior[dim] * signal_score[s, dim]
  for dim in 8_dimensions
) + sum(
  persona_meta_weight[a, meta] * signal_meta[s, meta]
  for meta in 6_meta_features
)
```

This is a single matrix multiplication — no LLM calls.

### 5.4 Convergence and divergence

Group archetypes into their 9 clusters. Compute:

```
cluster_mean[c, s] = mean(raw_score[a, s] for a in cluster[c])
convergence[s] = mean(cluster_mean[c, s] for c in 9_clusters)
divergence[s] = stddev(cluster_mean[c, s] for c in 9_clusters)
```

### 5.5 Priority, contestedness, and uncertainty (3 outputs, never collapsed)

The system reports priority, contestedness, and uncertainty as **separate outputs**, not a single collapsed score.

```
impact[s] = 0.25*urgency + 0.20*scale + 0.20*irreversibility + 0.20*cascade_risk + 0.15*evidence_quality

# Central tendency (how much the ensemble cares, on average)
central_tendency[s] = mean(abs(raw_score[a, s]) for a in all_archetypes)

# Sign agreement (do archetypes agree on direction?)
sign_agreement[s] = proportion of archetypes with same sign as median

# Contestedness (how much archetypes disagree — using MAD for robustness)
contestedness[s] = median_absolute_deviation(cluster_mean[c, s] for c in clusters)

# Priority is central_tendency × impact × actionability
# Contestedness is reported alongside, never multiplied in
priority_raw[s] = central_tendency[s] * impact[s] * actionability[s]
contest_raw[s] = contestedness[s] * impact[s]

# Final score normalisation for ranking
priority_score[s] = zscore(priority_raw[s] across current batch/window)
contest_score[s] = zscore(contest_raw[s] across current batch/window)

# Polarity: is this a risk or an opportunity?
polarity[s] = sign(median(raw_score[a, s] for a in all_archetypes))
```

Uncertainty propagation is performed only for the top-20 signals that received triple classification. Let `signal_dim_uncertainty[s, dim]` and `signal_meta_uncertainty[s, meta]` be the cross-pass standard deviations.

```
effective_dim_weight[a, dim] = persona_weight[a, dim] * expert_prior[dim]

raw_uncertainty[a, s] = sqrt(
  sum(
    effective_dim_weight[a, dim]^2 * signal_dim_uncertainty[s, dim]^2
    for dim in 8_dimensions
  ) +
  sum(
    persona_meta_weight[a, meta]^2 * signal_meta_uncertainty[s, meta]^2
    for meta in 6_meta_features
  )
)

final_uncertainty[s] = sqrt(mean(raw_uncertainty[a, s]^2 for a in all_archetypes))
```

Report rank confidence intervals by drawing 1,000 Monte Carlo samples from the per-signal score distributions implied by `priority_raw ± final_uncertainty`, re-ranking each draw, and storing the 5th-95th percentile rank interval.

**Critical design decision:** `priority_score`, `contest_score`, and `final_uncertainty` are NEVER collapsed into a single number. High-priority AND high-contestedness signals are surfaced with explicit disagreement flags, and high-uncertainty signals are surfaced with explicit reliability flags.

### 5.6 Output categories

Each signal is classified into one of:

| Category | Condition | Meaning |
|---|---|---|
| **Convergent priority** | `zscore(central_tendency) >= 0.5`, `sign_agreement >= 0.75`, `zscore(impact) >= 0.5` | Everyone agrees this matters and agrees on direction |
| **Contested priority** | `zscore(central_tendency) >= 0.5`, `sign_agreement <= 0.55`, `zscore(impact) >= 0.5` | Everyone agrees this matters but disagrees on direction — MOST INTERESTING |
| **Niche concern** | `zscore(central_tendency) < 0.0`, `max(zscore(cluster_mean[c, s])) >= 1.0`, `zscore(impact) >= 0.5` | Matters intensely to some perspectives, invisible to others |
| **Background noise** | `zscore(central_tendency) < 0.0`, `zscore(impact) < 0.0` | Noise — not structurally important from any perspective |

**Interesting signal detection (Opus 4.7's insight):**
Flag signals where:
- **Unexpected convergence**: high sign_agreement on a signal that baseline models score as contested
- **Unexpected divergence**: low sign_agreement on a signal that baseline models score as obvious

These are computed by comparing against a random-weights ensemble baseline (§10.2). The deviation from random is the signal, not the absolute score.

---

## 6. Expert-Ensemble Coupling (Formal Specification)

**Mechanism: multiplicative dimensional prior with explicit disagreement surfacing.**

```
expert_score[s] = sum(expert_prior[dim] * signal_score[s, dim] for dim in dims)
expert_priority_ranking = rank_desc(expert_score)
ensemble_priority_ranking = rank_desc(priority_score)

expert_ensemble_agreement = kendall_tau(
  expert_priority_ranking,
  ensemble_priority_ranking
)

per_signal_gap[s] = abs(
  percentile_rank_desc(expert_score[s]) -
  percentile_rank_desc(priority_score[s])
)

flagged_disagreements = [
  s for s in signals
  if per_signal_gap[s] > 0.3
]
```

`expert_ensemble_agreement` is the portfolio-level coupling statistic; `per_signal_gap` is only for reporting and review. The disagreement threshold `0.3` is pre-registered and corresponds to expert/ensemble discordance of at least 30 percentile points (for example, top-30% vs bottom-30%).

---

## 7. Feedback Mechanism (Cyclic Enrichment)

### 7.1 What gets fed back

After each cycle, record:
- what was prioritised (top-N signals)
- what actually happened (outcome observation, manual or automated)
- which archetypes' scores best predicted the outcome

Outcome variables are domain-specific and must be operationalised before experiments begin:
- **World affairs:** `outcome_score[s] ∈ {0,1}` — 1 if the signal's predicted trend materialised within the pre-registered prediction horizon, 0 otherwise, measured by follow-up news analysis against a fixed rubric.
- **Code triage:** `outcome_score[s] ∈ {0.0, 0.5, 1.0}` — 0.5 for bug fixed within the sprint, plus 0.5 if the fix reduced related incidents/reopens in the next sprint, measured from issue-resolution and incident data.
- **Community health:** `outcome_score[s] ∈ {0,1}` — 1 if the intervention reduced the target service metric by the pre-registered threshold in the evaluation window, 0 otherwise, measured from service outcome data.

For each archetype and domain:

```
reward[a, domain] = pearson_r(
  archetype_priority_scores[a, signals_in_window],
  outcome_scores[signals_in_window]
)
```

Compute this over a rolling 30-day window. Do not update a domain unless the window contains at least 10 signals with observed outcomes.

### 7.2 Calibration update

For each domain, update archetype weights with a bounded multiplicative rule plus cluster projection:

```
w_raw[a] = w_old[a] * exp(η * reward[a, domain])
w_clipped[a] = clip(w_raw[a], 0.02, 0.05)

for each cluster c:
  cluster_sum[c] = sum(w_clipped[a] for a in cluster[c])
  target_cluster_weight = 1.0 / n_clusters
  for a in cluster[c]:
    w_final[a] = w_clipped[a] * (target_cluster_weight / cluster_sum[c])
```

Parameters:
- `η = 0.1` by default (tunable only by pre-registration)
- `n_clusters = 9` in the current archetype set
- update window = rolling 30 days
- minimum observations = 10 resolved signals per domain window

### 7.3 Anti-collapse safeguards

1. **Cluster equality:** each of the 9 clusters maintains equal total weight (`1/9` each after projection)
2. **Weight floor/cap:** no single archetype can dominate (0.02 to 0.05 range before cluster projection)
3. **Domain-local learning:** calibration in code triage does not affect world affairs weights
4. **Divergence preservation:** contested signals stay contested — they are not averaged away
5. **Counterfactual reporting:** show "what would change if we removed cluster X"
6. **No silent updates:** store `w_old`, `reward`, `w_clipped`, and `w_final` for every update window so calibration is fully auditable

---

## 8. Mood Indicator (Portfolio-Level)

### 8.1 Computation

For each active trend (signals accumulated over the window):
```
trend_direction = net_positive_evidence - net_negative_evidence
trend_effect = polarity_sign * direction_sign * abs(net_weight) * confidence
```

Portfolio mood score = 7-day exponential moving average of daily trend_effect sums.

### 8.2 Labels (with hysteresis — must persist 2+ days to flip)

| Mood | Condition | Symbol |
|---|---|---|
| **Constructive** | EMA >= 0.25 for 2+ days | 🟢 |
| **Cautious** | -0.25 < EMA < 0.25 | 🟡 |
| **Concerning** | EMA <= -0.25 for 2+ days | 🔴 |
| **Transitional** | >40% of active trends are reversing or contested | 🔵 |

---

## 9. Domain Profiles

### 9.1 World Affairs

```yaml
domain: world_affairs
expert_persona: economist
expert_prior:
  economic_stability: 1.5
  institutional_trust: 1.3
  physical_safety: 1.2
  collective_welfare: 1.1
  social_cohesion: 1.0
  environmental_continuity: 0.9
  individual_autonomy: 0.8
  knowledge_capability: 0.7
signal_sources:
  - type: rss
    feeds: [bbc_world, aljazeera, abc_au]
benchmark: retrospective_expert_consensus
```

### 9.2 Code Repository Triage

```yaml
domain: code_repo
expert_persona: senior_engineer
expert_prior:
  knowledge_capability: 1.5
  physical_safety: 1.4  # security
  institutional_trust: 1.3  # reliability
  collective_welfare: 1.0  # user impact
  economic_stability: 0.9
  individual_autonomy: 0.8
  social_cohesion: 0.7
  environmental_continuity: 0.5
signal_sources:
  - type: github_issues
    repo: target/repo
benchmark: bug_resolution_impact
```

### 9.3 Community Health

```yaml
domain: community_health
expert_persona: epidemiologist
expert_prior:
  physical_safety: 1.5
  collective_welfare: 1.4
  institutional_trust: 1.2
  economic_stability: 1.1
  social_cohesion: 1.0
  individual_autonomy: 0.9
  knowledge_capability: 0.8
  environmental_continuity: 0.7
signal_sources:
  - type: case_reports
  - type: surveys
benchmark: service_outcome_data
```

---

## 10. Benchmarking and Validation Strategy

### 10.1 Designer-bias ablation (MUST run first)

Have 3 independent reviewers each design their own set of 36 persona weight vectors using the procedure in §3.1. Run the same signal set through all 3. Measure:
- Pairwise Kendall τ between the 3 ranked outputs
- ICC(2,k) across the 3 weight matrices
- If ICC < 0.7: system is designer-dependent -> must use empirical weights instead

### 10.2 Baseline comparisons (5 baselines, not 1)

| Baseline | What it tests |
|---|---|
| **B1: Single well-prompted LLM** | "You are a thoughtful economist. Prioritise these." Does the ensemble beat a good prompt? |
| **B2: Chain-of-thought single LLM** | Same prompt with explicit reasoning steps. Does structured prompting match the ensemble? |
| **B3: Self-consistency / majority vote** | Run the single prompt N times, take majority. Does sampling diversity match persona diversity? |
| **B4: Random-weights ensemble** | Same 36 archetypes, random weight vectors. Does the STRUCTURE of the weights matter, or does any averaging help? This is the critical null. |
| **B5: Plain MCDA with manual weights** | Traditional multi-criteria analysis with expert-assigned weights. Does the persona layer add value over manual weighting? |

**If the persona ensemble fails to beat B4 (random weights):** the structure is decorative and the weights are irrelevant — any averaging helps equally. This would redirect the project toward understanding WHY averaging helps rather than claiming persona structure matters.

### 10.3 Retrospective hindcast

Use historical events with known outcomes:
- 2008 financial crisis (pre-2007 signals)
- COVID-19 supply chain collapse (pre-March 2020 signals)
- Sri Lanka 2022 collapse

For each: did the ensemble rank the signals that turned out to matter higher than the single-prompt baseline?

### 10.4 Longitudinal tracking

For the daily world affairs application:
- Track which priorities persisted vs which were noise
- After 3 months: compare system's structural trends against retrospective analysis
- Measure prediction calibration

---

## 11. Ethical Considerations and Stereotype Risk

### 11.1 Persona archetypes are not demographic truths

Each archetype is a synthetic stakeholder constructed from value theory, not a claim about how any real demographic group thinks. "Subsistence farmer, Global South" is a value-profile approximation, not a statement about all Global South farmers.

### 11.2 Risks

1. **Stereotype encoding**: persona weight vectors could encode harmful stereotypes (e.g., assuming all refugees prioritise safety above all else). Mitigated by: (a) weight derivation from survey data, not intuition, (b) audit for harmful patterns, (c) sensitivity analysis removing identity labels.

2. **Representation without consent**: simulating the perspectives of marginalised groups without their input. Mitigated by: (a) using published survey data from those populations, (b) stating explicitly that simulation is not representation, (c) inviting community review where possible.

3. **Normalising uncomfortable perspectives**: including nationalist/authoritarian archetypes could be misread as endorsement. Mitigated by: (a) explicit framing as descriptive, not normative, (b) every output states "this is what a diverse human collective WOULD prioritise, not what SHOULD be prioritised."

### 11.3 Required audits

1. Run the engine with and without identity labels on personas — if outputs change significantly, the labels are doing work that the value profiles should be doing alone
2. Check for dimensions where a single demographic cluster dominates — if "physical safety" is only scored high by the survival-focused cluster, the dimension may be encoding poverty, not a universal value
3. Report counterfactual outputs: "if we removed cluster 7 (sovereignty/order), these priorities would change by X"

---

## 12. What This Document Is NOT

This is not a product spec. This is a research design.

- The code is the instrument for testing the hypothesis
- The news dashboard is experiment #1
- The persona ensemble is the independent variable
- The benchmark comparison is the dependent variable
- The feedback loop is the learning mechanism

If the hypothesis is falsified (single-prompt LLM performs equivalently), that is a valid research outcome — it means the ensemble layer doesn't add value and the project pivots.

---

## 13. Next Steps

1. Encode the 36 persona archetypes with Schwartz-derived weight vectors using the procedure in §3.1 → `configs/persona_ensemble.yaml`
2. Build the domain-agnostic scoring engine → `src/core/`
3. Run designer-bias ablation as first experiment
4. Apply to world affairs pipeline as experiment #1
5. Apply to code triage as experiment #2
6. Publish findings regardless of outcome
