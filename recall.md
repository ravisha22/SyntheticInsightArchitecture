# SIA Recall — Session State

> Compact continuity file. Update at meaningful milestones.

## Target To Preserve
- LLMs do the reasoning; Python/scripts enforce scarcity, behavior, orchestration, persistence, and evaluation.
- The system must be generalized. Pandas or any single repo is only a test corpus, not the design anchor.
- Inputs should include bug reports, feedback, incidents, support signals, audits, news, and industry trends.
- Prioritization should use contextual first-principles reasoning: blast radius, happy-path gain vs failure-path risk, severity, scope, and scarcity.
- The core loop is predict what should be fixed, then compare predictions to real outcomes.

## Current Read
- Repo contains two paths: a cognitive-insight simulator and an LLM-native issue-analysis pipeline.
- `pytest tests -q`: 52 passed.
- Blinded evaluation on the generalized `AnalysisPipeline`: A pass, B pass, C pass, D pass, baseline pass.
- The live pipeline now has a generalized signal baseline with canonical signal identity, DB-backed conflict guards, legacy issue-path separation, backward-compatible wrappers, and additive Stage 2.5 evidence grounding.
- Grounding is now wired into `AnalysisPipeline` before scarcity prioritization and can be enabled with an injected grounder or `SIA_GROUNDING_REPO`.
- Prioritization runs now persist structured prediction records, outcomes state, and evaluation summaries for later comparison.
- `simulation\run_blinded_test.py` is now the generalized deterministic evaluation entrypoint and is wired to `simulation\scenarios\generalized_blinded.py`.
- The pandas-specific mock adapter, pandas scenario corpora, and pandas-only runners have been removed from the repo.
- The generalized evaluation bar is met on the deterministic harness, and the remaining validation work is broadening corpora rather than removing legacy pandas paths.
- A new reusable skill package now exists at `.github\skills\problem-intelligence-factory\` to scaffold scenario-specific collection, filtering, prioritization, and intervention bundles for any domain.

## Drift To Correct
- Live grounding is still disabled by default in local runs unless `SIA_ENABLE_GROUNDING` is set.
- `ImmersionEngine`, `VerificationHarness`, `IntegrationEngine`, and `SocialLedger` exist but are not wired into `SIAEngine`.
- The new skill factory exists, but the repo still needs broader non-code scenario bundles and live-grounded validation corpora.

## Session Proof
- Reviewed full repo layout, formal spec, tests, simulations, cached corpora, and recorded outputs.
- Recovered prior SIA discussion from session history, including the shift to LLM-native reasoning and anti-overfitting guidance.
- Confirmed saved test artifacts in `simulation\output\`.
- Added this recall file and a persistent workflow memory rule.
- Started Phase 0 generalization: moved corpus-specific stop words into config, made web grounding repo-agnostic by default, and extracted the pandas-specific mock analysis path into `src\adapters\mock_pandas.py`.
- Completed the Phase 1 generalized signal slice in the live pipeline:
  - additive signal fields and schema support
  - generalized prompt inputs with backward compatibility
  - canonical identity normalization and source normalization
  - fail-fast guards for ambiguous or conflicting signal identity
  - DB-backed `signal_id` uniqueness and fingerprint persistence
  - fallback-path persistence so failed analyses still keep identity state
  - expanded regression coverage to 46 passing tests
- Completed the Phase 2 grounding slice and opened Phase 3 prediction persistence:
  - inserted additive grounding between clustering and prioritization
  - persisted cluster grounding query, evidence, supporting evidence, and original vs revised severity/confidence
  - persisted prioritization predictions and outcomes state
  - added `record_outcomes()` so the same run can later be compared against observed results
  - fixed generic mock prompt parsing so real prompt bodies drive severity/root-cause classification
  - hardened the pipeline so LLM output cannot override canonical signal identity
  - expanded regression coverage to 50 passing tests
- Completed the Phase 3 evaluation slice:
  - added `evaluation_json` persistence and `score_predictions()` on `AnalysisPipeline`
  - moved blinded evaluation onto generalized signals passed through the live pipeline
  - scored predictions against observed outcomes instead of goal-seed heuristics
  - made decoy, shuffle, non-convergent, and baseline checks operate on the same persisted predictions
  - fixed outcome-matching deduplication so scoring is not order-dependent
  - expanded regression coverage to 52 passing tests
  - reran blinded evaluation to all-pass on the deterministic harness
- Added a new cross-domain skill-factory package:
  - created `.github\skills\problem-intelligence-factory\SKILL.md`
  - documented 360-degree signal collection, reliability filtering, existential prioritization, and reusable bundle outputs
  - added reference files for workflows, signal taxonomy, output bundle structure, and acceptance criteria
  - added `scripts\init_bundle.py` to scaffold scenario-specific prompt bundles, deterministic scripts, and a generated scenario skill
  - smoke-tested the scaffolder on a housing-instability scenario bundle in the session workspace

## Action Plan
1. Remove pandas-specific logic from `src\` and keep pandas only as an optional evaluation corpus.
   **Done; pandas-specific adapter and corpora removed.**
2. Introduce a generalized signal schema for bug reports, incidents, feedback, support, audits, news, and trends. **Done for baseline pipeline path.**
3. Make LLM reasoning primary for analysis, clustering, commitment, and prioritization; keep Python as the constraint and persistence layer.
4. Wire evidence grounding into the live pipeline before final prioritization. **Done for the live pipeline path.**
5. Add prediction-vs-outcome evaluation and rerun blinded tests until real signal beats decoys, shuffles, and baselines. **Done on the deterministic generalized pipeline path.**
6. Replace the remaining pandas-shaped simulations, tests, and canaries with generalized or social-system scenario assets. **Done for the repo default path.**
7. Use the problem-intelligence factory to standardize future scenario bundles around 360-degree evidence gathering, filtering, prioritization, and predicted outcomes.

## Resume Here
- Immediate next focus: widen generalized scenario coverage and validate live-grounded runs beyond the deterministic mock.
- Success bar: the system reasons over arbitrary signals without repo-specific heuristics, bundles scenario intelligence from broad evidence, and maintains measurable prediction quality with live grounding enabled.
