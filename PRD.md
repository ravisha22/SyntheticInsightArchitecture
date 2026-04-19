# Synthetic Insight Architecture (SIA) — Product Requirements Document

**Version:** 1.0  
**Last updated:** 2026-04-19  
**Source of truth:** `Cognitive_Insight_Architecture_Specification.docx`

## 1. Executive Summary

**Problem Statement**  
Current AI systems optimize answer quality but do not reliably replicate the human creative-insight process, and they remain vulnerable to corpus overfitting, missing grounding, and weak reuse across domains.

**Proposed Solution**  
Evolve SIA into a domain-general problem-intelligence system that combines the source-of-truth cognitive architecture with a generalized LLM-native analysis pipeline, explicit scarcity and persistence layers, live evidence grounding, and a reusable skill factory for scenario-specific bundles.

**Success Criteria**

| Success factor | KPI | Release bar |
|---|---|---|
| Generalization across domains | Blinded Conditions A-D + baseline | **5/5 pass on at least 3 distinct domain corpora** |
| Generalization across domains | Precision / recall on held-out corpora | **precision >= 0.60** and **recall >= 0.50** on at least 2 held-out corpora |
| Live-grounded real-world readiness | Grounded evidence coverage | **>= 80%** of clusters contain at least 1 external evidence item in grounded runs |
| Live-grounded real-world readiness | Grounding uplift | Grounded runs improve precision by **>= 0.05** versus ungrounded runs on the same corpus |
| Live-grounded real-world readiness | End-to-end latency | Full grounded pipeline completes in **<= 30 seconds** for 5 signals |
| Skill-factory adoption and reuse | Bundle generation completeness | **3 committed bundles**, each with **9/9 required files** |
| Skill-factory adoption and reuse | Reuse proof | At least **1 bundle** is executed end-to-end by a fresh LLM session |
| Regression safety | Repo test suite | `pytest tests -q` remains **>= 52 passing, 0 failing** |
| Architectural cleanliness | Core codebase generality | **0 domain-specific heuristics** in `src\` and `tests\` |

## 2. User Experience & Functionality

### User Personas

| Persona | Needs | Primary output |
|---|---|---|
| Research / design lead | Validate whether SIA matches the source cognitive model and has measurable fidelity gates | PRD, metrics, design decisions |
| Scenario analyst | Feed in complex domain signals and receive prioritized interventions | Ranked intervention list with predicted outcomes |
| Evaluation engineer | Prove the system is not overfit and can pass adversarial controls | Blinded-eval reports, gating metrics |
| Scenario-bundle builder | Rapidly scaffold reusable domain bundles | Skill bundle with prompts, scripts, and signal templates |

### User Stories

1. **As a system designer, I want SIA to reason over code, social, civic, product, and operational problems so that the architecture is not fit to a single corpus.**
2. **As a validation engineer, I want explicit quantitative gates for generalization, grounding, and reuse so that release decisions are binary instead of interpretive.**
3. **As an analyst, I want live grounding and provenance on clustered risks so that recommendations are tied to evidence rather than only internal pattern matching.**
4. **As a future LLM session, I want reusable scenario bundles and continuity artifacts so that the next round of work starts from the current design state instead of rediscovering it.**

### Acceptance Criteria

**Story 1**
- The default evaluation harness runs on generalized scenario modules rather than repo-specific corpora.
- `src\` and `tests\` contain no domain-fitted logic for a named corpus.
- At least 3 scenario corpora are supported by the same blinded-eval contract.

**Story 2**
- Every primary success factor has at least 2 quantified KPIs.
- Each KPI has a numeric threshold and an explicit pass/fail gate.
- Release readiness is blocked if any primary gate fails.

**Story 3**
- The analysis pipeline supports grounded and ungrounded runs from the same entrypoint.
- Grounded evidence, supporting evidence, and confidence changes are persisted.
- Grounded runs degrade safely when external evidence is unavailable.

**Story 4**
- A repo-root `PRD.md` and `PRD.docx` exist and match the same canonical content.
- `recall.md` contains the comprehensive testing plan and gates.
- A repo-root handoff document exists for the next LLM and lists the next execution steps.

### Non-Goals

- Building artificial consciousness, sentience, or AGI claims.
- Claiming full human-equivalent creativity beyond the fidelity bars defined in the source spec.
- Treating the current deterministic social-systems harness as proof of broad real-world readiness.
- Replacing the source specification; the PRD operationalizes it for implementation and evaluation.

## 3. AI System Requirements

### Tool Requirements

| Area | Required tools / components |
|---|---|
| Reasoning adapters | `MockAdapter`, Ollama-compatible real adapter path |
| Persistence | SQLite, JSONL artifacts, Markdown continuity docs |
| Evaluation | `simulation\run_blinded_test.py`, `score_predictions()`, baseline scorer |
| Grounding | `WebGrounding`, `SIA_ENABLE_GROUNDING`, `SIA_GROUNDING_REPO` |
| Scenario generation | `simulation\scenarios\*.py`, `.github\skills\problem-intelligence-factory\scripts\init_bundle.py` |
| Bundle reuse | `.github\skills\problem-intelligence-factory\SKILL.md`, generated bundle `skill\SKILL.md` |
| Validation storage | `issue_analyses`, `root_cause_clusters`, `prioritization_runs`, `evaluation_json` |

### Evaluation Strategy

| Phase | Scope | Gate |
|---|---|---|
| Phase 0 — Regression baseline | `pytest tests -q` and current blinded generalized harness | Must stay green before any new work |
| Phase 1 — Cross-domain generalization | Social/civic, code/engineering, product/community corpora | 5/5 blinded pass on at least 3 corpora |
| Phase 2 — Live-grounded readiness | Grounded versus ungrounded runs on the same corpora | Precision uplift >= 0.05 and coverage >= 80% |
| Phase 3 — Skill-factory proof | Generated bundles across multiple domains | 3 complete bundles and 1 external reuse pass |
| Phase 4 — Integrated release gate | Combined regression, blinded eval, grounded eval, bundle reuse | All primary success criteria green |

Full phase detail, test IDs, commands, and gates are documented in `recall.md`.

## 4. Technical Specifications

### Architecture Overview

SIA has two active execution paths built from the same design source:

1. **Cognitive simulator path** — `SIAEngine` and component layer logic for tension, failure, dream, urgency, scarcity, and commitment dynamics.
2. **LLM-native analysis path** — `AnalysisPipeline` for signal intake, clustering, optional grounding, scarcity prioritization, prediction persistence, and scored evaluation.

The source specification defines **13 core components** plus **4 closure mechanisms** (17 total design elements). The current repo operationalizes a generalized default path and preserves the broader cognitive design as the architectural target.

**Current system data flow**

1. Intake generalized signals (`signal_id`, `signal_type`, `source`, `title`, `body`, `tags`, `metadata`)
2. Analyze signals into severity, scope, blast radius, root category, and confidence
3. Cluster shared systemic weaknesses
4. Optionally ground clusters with external evidence
5. Prioritize under scarcity and persist predictions
6. Record observed outcomes and score predictions
7. Use bundle generation to scaffold reusable scenario-specific collection and intervention workflows

### Integration Points

| Integration point | Current state | Target state |
|---|---|---|
| `src\services\analysis_pipeline.py` | Implemented and generalized | Keep as the default scoring and persistence path |
| `src\engine.py` / component loop | Implemented with partial wiring | Wire at least 2 currently unwired spec components |
| SQLite persistence | Implemented | Remains the single durable operational store |
| JSONL / Markdown artifacts | Implemented | Continue as inspectable audit layer |
| Web grounding | Implemented but opt-in | Make default-on with graceful degradation |
| Scenario bundles | Implemented as scaffolding | Commit and validate multiple real bundles |

### Security & Privacy

- Do not hardcode credentials or tokens in repo files.
- Use environment variables for external grounding configuration.
- Persist evidence provenance and model outputs, but do not persist secrets in logs or artifacts.
- Treat external evidence as untrusted until it survives the verification and gating pipeline.
- Keep human-readable artifacts inspectable so bad recommendations can be audited and challenged.

## 5. Risks & Roadmap

### Phased Rollout

| Phase | Deliverable | Exit criteria |
|---|---|---|
| **MVP / Current baseline** | Generalized core, generalized blinded harness, skill-factory baseline | `pytest tests -q` green; generalized blinded 5/5 pass |
| **v1.1** | Multi-domain validation | 3 corpora pass 5/5 blinded conditions; precision >= 0.60 and recall >= 0.50 on at least 2 held-out corpora |
| **v1.2** | Grounded default path | Grounding coverage >= 80%, uplift >= 0.05, grounded latency <= 30s |
| **v1.3** | Skill-factory proof | 3 committed bundles, 9/9 files each, 1 external reuse pass |
| **v2.0** | Spec-aligned integrated system | At least 2 unwired components connected, live-grounded regression in CI, all primary success factors green |

### Technical Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Single-domain overconfidence | False proof of generalization | Require at least 3 corpora before GA claim |
| Grounding outages or slowdowns | Broken or misleading production behavior | Safe fallback path, evidence caching, explicit grounded-vs-ungrounded comparison |
| Spec-code drift | Source spec diverges from executable system | Track drift in `recall.md`, update PRD when architecture meaningfully changes |
| Skill factory remains unused | Reuse layer stays theoretical | Require at least 1 external-agent reuse before release bar is met |
| Mock-only validation | Real-world failure modes remain hidden | Add live-LLM and live-grounded validation gates |
