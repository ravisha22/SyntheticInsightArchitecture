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
- Repo-root documentation now includes `PRD.md`, validated `PRD.docx`, and `LLM_HANDOFF.md`, all aligned to `Cognitive_Insight_Architecture_Specification.docx`.

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
- Added the current documentation package:
  - created repo-root `PRD.md` as the quantified implementation PRD derived from the formal specification
  - generated and validated repo-root `PRD.docx`
  - appended the comprehensive gated testing plan to `recall.md`
  - created repo-root `LLM_HANDOFF.md` for the next LLM session

## Action Plan
1. Remove pandas-specific logic from `src\` and keep pandas only as an optional evaluation corpus.
   **Done; pandas-specific adapter and corpora removed.**
2. Introduce a generalized signal schema for bug reports, incidents, feedback, support, audits, news, and trends. **Done for baseline pipeline path.**
3. Make LLM reasoning primary for analysis, clustering, commitment, and prioritization; keep Python as the constraint and persistence layer.
4. Wire evidence grounding into the live pipeline before final prioritization. **Done for the live pipeline path.**
5. Add prediction-vs-outcome evaluation and rerun blinded tests until real signal beats decoys, shuffles, and baselines. **Done on the deterministic generalized pipeline path.**
6. Replace the remaining pandas-shaped simulations, tests, and canaries with generalized or social-system scenario assets. **Done for the repo default path.**
7. Use the problem-intelligence factory to standardize future scenario bundles around 360-degree evidence gathering, filtering, prioritization, and predicted outcomes.

## Comprehensive Model Test Plan

This plan is the release gate for the generalized SIA design. A release is not considered credible unless all phase gates below are satisfied.

### Primary success factors and hard bars

| Success factor | Metric | Gate |
|---|---|---|
| Generalization across domains | 5/5 blinded conditions | Must pass on **>= 3** distinct domain corpora |
| Generalization across domains | Precision / recall on held-out corpora | **precision >= 0.60**, **recall >= 0.50** on **>= 2** held-out corpora |
| Live-grounded real-world readiness | Cluster grounding coverage | **>= 80%** of clusters include grounded evidence |
| Live-grounded real-world readiness | Grounding uplift | Precision improves by **>= 0.05** on grounded versus ungrounded runs |
| Live-grounded real-world readiness | Grounded latency | Full grounded pipeline completes in **<= 30s** for 5 signals |
| Skill-factory adoption and reuse | Bundle completeness | **3** committed bundles, each with **9/9** required files |
| Skill-factory adoption and reuse | Reuse | **>= 1** bundle executed successfully by a fresh LLM session |
| Regression safety | Repo test suite | `pytest tests -q` remains **>= 52 pass, 0 fail** |

### Phase 0 — Regression baseline gate

| Check | Command | Pass criteria | Current state |
|---|---|---|---|
| Unit/integration regression | `pytest tests -q` | 0 failures | **52 passed** |
| Default blinded evaluation | `python -m simulation.run_blinded_test` | A/B/C/D/baseline all pass | **PASS** |
| Core path cleanliness | grep for domain-fitted logic in `src\` and `tests\` | 0 matches | **PASS** |

**Gate rule:** no later phase is meaningful if this phase fails.

### Phase 1 — Cross-domain generalization gate

**Objective:** prove the generalized pipeline works beyond the current social-systems corpus.

| Domain | Minimum corpus size | Expected observed outcomes | Gate |
|---|---|---|---|
| Social / civic | >= 8 signals | >= 2 | 5/5 blinded pass |
| Code / engineering | >= 8 signals | >= 2 | 5/5 blinded pass |
| Product / community | >= 8 signals | >= 2 | 5/5 blinded pass |

**Required checks per domain**

| Test ID | Check | Pass criteria |
|---|---|---|
| G-1 | Condition A | all observed-positive outcomes matched |
| G-2 | Condition B | zero target drift versus decoy run |
| G-3 | Condition C | shuffled run degrades relative to real run |
| G-4 | Condition D | non-convergent run scores 0 hits |
| G-5 | Baseline comparison | pipeline beats keyword/label heuristic |
| G-6 | Held-out precision | >= 0.60 |
| G-7 | Held-out recall | >= 0.50 |

### Phase 2 — Live-grounded readiness gate

**Objective:** prove the system stays reliable when external evidence is introduced.

| Test ID | Scenario | Pass criteria |
|---|---|---|
| LG-1 | Grounding enabled, valid source | >= 80% cluster evidence coverage |
| LG-2 | Grounding provider returns no evidence | pipeline completes without crash |
| LG-3 | Grounding provider errors or times out | pipeline completes and falls back safely |
| LG-4 | Grounded vs ungrounded comparison | precision uplift >= 0.05 |
| LG-5 | Grounded latency SLA | <= 30s for 5-signal run |
| LG-6 | Evidence persistence | `grounding_evidence`, `supporting_evidence`, `original_confidence`, `grounding_confidence_change` all persisted |

### Phase 3 — Skill-factory adoption and reuse gate

**Objective:** prove the skill factory is a real product surface rather than a dormant scaffold.

| Test ID | Check | Pass criteria |
|---|---|---|
| SF-1 | Code / engineering bundle generation | 9/9 files generated |
| SF-2 | Social / civic bundle generation | 9/9 files generated |
| SF-3 | Product / community bundle generation | 9/9 files generated |
| SF-4 | Collection prompt coverage | at least 5 signal families explicitly covered |
| SF-5 | Prioritization prompt quality | scarcity, cascade, and deferral reasoning present |
| SF-6 | Intervention prompt chain | root cause -> intervention -> predicted outcome -> failure mode present |
| SF-7 | Acceptance criteria review | all bundle checks pass |
| SF-8 | Fresh-session reuse | 1 new LLM session completes bundle-driven run successfully |

### Phase 4 — Spec-alignment and integrated release gate

**Objective:** reduce the gap between the formal architecture and the executable system.

| Test ID | Check | Pass criteria |
|---|---|---|
| SA-1 | VerificationHarness wiring | component callable from `SIAEngine` |
| SA-2 | IntegrationEngine wiring | component callable from `SIAEngine` |
| SA-3 | ImmersionEngine or SocialLedger wiring | at least 1 additional currently unwired component connected |
| SA-4 | Simulator smoke run | multi-cycle run completes without regression |
| SA-5 | Combined release run | regression + blinded eval + grounded eval all pass together |

### Commands and artifacts to use

```powershell
Set-Location 'C:\Users\ranandag\Documents\workvsc\SyntheticInsightArchitecture'
pytest tests -q
python -m simulation.run_blinded_test
```

Primary artifacts for future validation:

- `simulation\run_blinded_test.py`
- `simulation\scenarios\generalized_blinded.py`
- `PRD.md`
- `.github\skills\problem-intelligence-factory\SKILL.md`
- `LLM_HANDOFF.md`

## Resume Here
- Phase 1 cross-domain gate: **MET** — 3/3 domains pass 5/5 blinded conditions (social/civic, code/engineering, product/community).
- Phase 3 skill-factory bundles: 3 committed bundles, each 9/9 files. Fresh-session reuse still needs proof.
- Phase 2 live-grounded validation: not yet started (grounding still opt-in).
- Phase 4 spec-alignment: VerificationHarness and IntegrationEngine wiring in progress.
- Next focus: complete grounding validation and prove fresh-session bundle reuse.
