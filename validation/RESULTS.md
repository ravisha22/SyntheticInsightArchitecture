# SIA Validation Results

> Validation run date: 2026-04-19
> System version: commit 257c377+ (post-documentation updates)
> Adapter: MockAdapter (deterministic keyword rules, no real LLM)

## 1. Hindcast: 2008 Financial Crisis

### Methodology

**Objective:** Can the system identify the root causes of the 2008 crisis using ONLY signals that were publicly available before January 2007?

**Signal selection discipline:**
- 15 signals sourced from real 2005-2006 publications (MBA delinquency reports, Case-Shiller data, FBI fraud warnings, dealer balance sheet reviews, ABX market data, IMF commentary)
- Signal language uses period-accurate terminology ("subprime delinquency moves higher", "home-price gauges flatten") — not retrospective language ("crisis", "crash", "meltdown")
- Sources named after real organisations that published this data at the time
- No signal references events after December 2006

**Observed outcomes** (what actually happened, used ONLY for scoring):
1. Housing instability — bubble burst, 30%+ price drops, millions of foreclosures
2. Economic fragility — household debt burden + wage stagnation made rate resets unsurvivable
3. Security boundary weakness — CDO ratings fraudulent, counterparty risk opaque, leverage exceeded safe limits

### Results

| Condition | Result | Detail |
|-----------|--------|--------|
| A — Root cause identification | **PASS** | 3/3 observed outcomes matched. Precision 1.000, recall 1.000. |
| B — Decoy metadata invariance | **PASS** | Zero target drift when misleading seed hypothesis injected. |
| C — Tag-shuffle control | **FAIL** | Shuffled run scores same as real run (3 hits, 1.000 precision). |
| D — Non-convergent rejection | **PASS** | Botany corpus correctly scores 0 hits against financial outcomes. |
| Baseline comparison | **PASS** | Pipeline beats keyword-frequency and label-cooccurrence baselines. |

**Pipeline identified (in priority order):**
1. Shared weakness in security boundary — existential — 6 signals (bank leverage, CDOs, ABX, ratings, SIVs, conduits)
2. Shared weakness in housing instability — existential — 5 signals (prices, inventory, speculation, ownership rate, warnings)
3. Shared weakness in economic fragility — major — 4 signals (subprime originations, NINJA loans, delinquencies, rate resets)

### Condition C failure analysis

**Why it fails:** The 2008 hindcast corpus is domain-homogeneous — all 15 signals come from the financial/mortgage sector. When labels are shuffled among signals that ALL contain financial keywords (Housing, Security, Income, Debt, Mortgage), the shuffled labels are still financial labels — just on different financial signals. The MockAdapter classifies primarily from title+body keywords, not labels, so shuffling within a single domain doesn't degrade results.

**What this means:** The system's classification is driven by signal content (body text), not label metadata. For domain-homogeneous corpora, this makes Condition C structurally unfalsifiable without artificially weakening the signal bodies.

**Comparison with other corpora:** The social/civic, product/community, and Middle East corpora pass Condition C because they contain cross-domain signals (housing + healthcare + security + trust) where shuffling labels across domain boundaries genuinely degrades clustering.

**Assessment:** Condition C failure is a property of the corpus, not the system. The system correctly identifies all 3 historical root causes. The honest interpretation: for domain-homogeneous data, signal content is sufficient for clustering, and labels provide marginal value.

---

## 2. A/B Test: Pipeline vs Raw LLM Prompt

### Methodology

**Objective:** Does the multi-stage SIA pipeline produce better analysis than a single-prompt LLM on the same signals?

**Setup:**
- **Pipeline path:** 15 pre-2007 signals → MockAdapter (analyze each → cluster → prioritize under scarcity) → score against observed outcomes
- **Raw LLM path:** Same 15 signals in a single prompt → GPT-5.4 asked to identify root causes, rank by severity, propose interventions → score against same observed outcomes

**Scoring:** Both paths scored against the same 3 observed outcomes using the same `score_text_predictions()` function with `target_contains` keyword matching.

### Results

| Metric | Pipeline (MockAdapter) | Raw LLM (GPT-5.4) | Delta |
|--------|----------------------|-------------------|-------|
| Root causes identified | 3 | 4 | +1 (raw) |
| Hits (matched outcomes) | 3 | 3 | tie |
| Precision | **1.000** | 0.750 | **+0.250 (pipeline)** |
| Recall | 1.000 | 1.000 | tie |

**Pipeline identified:**
1. Security boundary weakness (existential, 6 signals)
2. Housing instability (existential, 5 signals)
3. Economic fragility (major, 4 signals)

**Raw LLM identified:**
1. Housing instability driven by speculative credit expansion (existential, 8 signals)
2. Security boundary weakness in structured credit and wholesale funding (existential, 6 signals)
3. Economic fragility of households exposed to rate resets (major, 6 signals)
4. Originate-to-distribute incentives degrading loan quality (major, 4 signals)

### Analysis

**Pipeline wins on precision** because it produces exactly the root causes supported by the clustered signals — no more, no less. The raw LLM identifies a valid 4th root cause ("originate-to-distribute incentives") that is analytically insightful but doesn't match any of the 3 pre-defined observed outcomes, reducing its precision to 0.750.

**Important nuance:** The raw LLM's 4th finding is genuinely valid — the originate-to-distribute model was a real driver of the crisis. The precision penalty reflects the scoring framework's limitation (only 3 outcomes defined), not analytical error by the LLM.

**What the pipeline adds:**
- Structured clustering prevents over-generation of root causes
- Scarcity-driven prioritization forces explicit ranking
- Deterministic scoring provides a quantitative gate

**What the raw LLM adds:**
- Richer analytical narrative and more detailed interventions
- Ability to identify root causes not pre-embedded in the scoring rubric
- More nuanced severity assessment

**Assessment:** The pipeline produces more precise output; the raw LLM produces richer analysis. The ideal system would use a real LLM as the adapter inside the pipeline structure — combining the pipeline's discipline with the LLM's reasoning depth.

---

## 3. Noise Injection Robustness

### Methodology

**Objective:** How does the system's precision degrade when irrelevant noise signals are injected alongside real signals?

**Setup:**
- Base corpus: Social/civic domain (9 real signals, 2 observed outcomes)
- Noise signals: Astronomy, botany, pottery, weather, chess, tidal, bird migration, soil science — zero keyword overlap with any root cause pattern
- Noise levels: 0%, 25%, 50%, 75%, 100% (relative to real signal count)

### Results

| Noise Level | Total Signals | Hits | Precision | Degradation |
|-------------|--------------|------|-----------|-------------|
| 0% | 9 | 2 | 0.500 | baseline |
| 25% | 11 | 2 | 0.500 | +0.000 |
| 50% | 13 | 2 | 0.500 | +0.000 |
| 75% | 15 | 2 | 0.500 | +0.000 |
| 100% | 17 | 2 | 0.500 | +0.000 |

**Graceful degradation gate (precision at 75% noise >= 50% of baseline): PASS**

### Analysis

The system shows **zero precision degradation** even at 100% noise injection. This is because:

1. The MockAdapter's keyword rules only cluster signals that match specific domain patterns
2. Noise signals (astronomy, botany, etc.) contain zero matching keywords
3. Noise signals therefore remain unclustered and never enter the prioritization stage
4. The pipeline's clustering step acts as a natural noise filter

**Limitation:** This test uses orthogonal noise (completely unrelated domains). A harder test would inject **adversarial noise** — signals that partially match root cause keywords but point to wrong conclusions. That test is not yet implemented.

**Assessment:** The system is robust to irrelevant noise. Adversarial noise testing remains as future work.

---

## 4. Cross-Domain Summary

### All blinded evaluation results

| Domain | A | B | C | D | Baseline | Precision | Recall | Verdict |
|--------|---|---|---|---|----------|-----------|--------|---------|
| Social / Civic | ✅ | ✅ | ✅ | ✅ | ✅ | 0.500 | 1.000 | **PASS** |
| Code / Engineering | ✅ | ✅ | ✅ | ✅ | ✅ | 0.750 | 1.000 | **PASS** |
| Product / Community | ✅ | ✅ | ✅ | ✅ | ✅ | 1.000 | 1.000 | **PASS** |
| Middle East Conflict | ✅ | ✅ | ✅ | ✅ | ✅ | 1.000 | 1.000 | **PASS** |
| Australia Economy | ✅ | ✅ | ✅ | ✅ | ✅ | 0.800 | 1.000 | **PASS** |
| Hindcast: 2008 Crisis | ✅ | ✅ | ❌ | ✅ | ✅ | 1.000 | 1.000 | **FAIL (C)** |

### Grounding validation

| Test | Result | Detail |
|------|--------|--------|
| LG-1 Coverage | ✅ | 100% of clusters grounded |
| LG-2 No-evidence | ✅ | Pipeline completes safely |
| LG-3 Error | ✅ | Pipeline catches and falls back |
| LG-4 Uplift | ✅ | +0.500 precision improvement |
| LG-5 Latency | ✅ | 0.55s (gate: ≤30s) |
| LG-6 Persistence | ✅ | All grounding columns populated |

---

## 5. Known Limitations and Honest Assessment

### What the MockAdapter proves
- The **pipeline contract** works: normalization, clustering, deduplication, grounding integration, scarcity prioritization, and prediction scoring all function correctly
- The **evaluation harness** catches cheating (Condition B), rejects unrelated domains (Condition D), and beats keyword baselines
- The **system architecture** generalizes across 6 domains spanning social, engineering, product, geopolitical, economic, and historical scenarios

### What the MockAdapter does NOT prove
- That the system produces **better analysis than a raw LLM prompt** — the A/B test shows the pipeline is more precise but the raw LLM is richer. The real test requires using a real LLM inside the pipeline
- That the system **discovers** root causes — with the MockAdapter, signals must contain keywords that match pre-defined rules. A real LLM adapter would reason over signal content without pre-embedded keywords
- That Condition C is **meaningful for domain-homogeneous corpora** — when all signals share the same vocabulary, label shuffling doesn't degrade results regardless of system quality

### What needs to happen next
1. **Real LLM adapter integration** — plug in OpenAI/Groq/Ollama via the `--adapter openai` flag and rerun all tests
2. **Adversarial noise injection** — inject signals that partially match root cause patterns but point to wrong conclusions
3. **Second hindcast** — use a different historical event (e.g., Sri Lanka 2022 collapse) to confirm the methodology generalises
4. **Temporal signal injection** — feed signals chronologically and measure how priorities shift as evidence accumulates

---

## 6. Evolution Log

| Date | Change | Impact |
|------|--------|--------|
| Pre-session | Pandas-specific evaluation only | System was overfit to one domain |
| Session start | Removed pandas spine entirely | Generalized pipeline, 52 tests passing |
| +1h | Added code/engineering and product/community corpora | Phase 1 gate MET (3 domains) |
| +2h | Wired VerificationHarness + IntegrationEngine | 2 spec components connected |
| +2h | Added MockGrounder, grounding validation | Phase 2 gate MET |
| +3h | Applied to Middle East conflict scenario | 4th domain, real-world geopolitical |
| +4h | Applied to Australia economy scenario | 5th domain, real-world economic |
| +5h | Added OpenAI-compatible API adapter | Any LLM provider via CLI flags |
| +6h | Built 2008 hindcast with pre-event signals | Historical validation, Condition C limitation found |
| +6h | A/B pipeline vs raw LLM prompt comparison | Pipeline +0.250 precision, raw LLM richer analysis |
| +6h | Noise injection robustness test | Zero degradation at 100% noise |
