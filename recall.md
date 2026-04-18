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
- `pytest tests -q`: 50 passed.
- Blinded evaluation: A fail, B fail, C fail, D pass, baseline fail.
- The live pipeline now has a generalized signal baseline with canonical signal identity, DB-backed conflict guards, legacy issue-path separation, backward-compatible wrappers, and additive Stage 2.5 evidence grounding.
- Grounding is now wired into `AnalysisPipeline` before scarcity prioritization and can be enabled with an injected grounder or `SIA_GROUNDING_REPO`.
- Prioritization runs now persist structured prediction records plus outcomes state for later comparison.
- `python -m simulation.run_llm_analysis` still gives the same 2/3 pandas canary result.
- The prototype is real and persistent, but the validation bar is not met.

## Drift To Correct
- `simulation\run_blinded_test.py` still evaluates the old `SIAEngine` / heuristic path instead of the grounded generalized `AnalysisPipeline`.
- Prediction records and empty outcomes are now persisted, but the compare-and-score loop is not yet driving blinded evaluation.
- The pandas harness remains a compatibility corpus, not a generalized validation corpus.
- `ImmersionEngine`, `VerificationHarness`, `IntegrationEngine`, and `SocialLedger` exist but are not wired into `SIAEngine`.
- Current blinded tests prove the system is still detecting topic gravity or heuristic overlap more than generalized architectural convergence.

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

## Action Plan
1. Remove pandas-specific logic from `src\` and keep pandas only as an optional evaluation corpus.
2. Introduce a generalized signal schema for bug reports, incidents, feedback, support, audits, news, and trends. **Done for baseline pipeline path.**
3. Make LLM reasoning primary for analysis, clustering, commitment, and prioritization; keep Python as the constraint and persistence layer.
4. Wire evidence grounding into the live pipeline before final prioritization. **Done for the live pipeline path.**
5. Add prediction-vs-outcome evaluation and rerun blinded tests until real signal beats decoys, shuffles, and baselines. **Started: persistence is in place; blinded eval still needs to move onto the grounded pipeline path.**

## Resume Here
- Immediate next focus: Phase 3 — move blinded evaluation onto the grounded generalized pipeline and score predictions against observed outcomes.
- Success bar: the system reasons over arbitrary signals without repo-specific heuristics and produces measurable prediction quality.
