# Handoff: Synthetic Insight Architecture

## Current validated state

1. **Generalized core is green.**
   - `pytest tests -q` -> **52 passed**
   - `python -m simulation.run_blinded_test` -> **all 3 domains pass 5/5**

2. **Current blinded-eval readings (multi-domain)**
   - Social / Civic: 5/5 PASS (precision 0.500, recall 1.000)
   - Code / Engineering: 5/5 PASS (precision 0.750, recall 1.000)
   - Product / Community: 5/5 PASS (precision 1.000, recall 1.000)
   - **Phase 1 gate (>= 3 domains pass): MET**

3. **Pandas-specific spine has been removed.**
   - No pandas-specific logic remains in `src\`, `tests\`, or the default simulation path.
   - The default blinded harness is now wired to all three domain corpora via a registry.

4. **Skill-factory bundles committed (3/3, each 9/9 files)**
   - production-incident-triage-and-dependency-failure-prioritization (code domain)
   - housing-instability-and-repeated-crisis-service-use (social domain)
   - creator-trust-erosion-and-community-health-decay (product domain)

5. **Spec components wired**
   - VerificationHarness and IntegrationEngine are now wired into `SIAEngine._run_creative_pipeline()`.
   - Candidate insights are verified and integrated automatically per cycle.

4. **Design source of truth**
   - `Cognitive_Insight_Architecture_Specification.docx`
   - The spec defines **13 core components** plus **4 closure mechanisms** (17 total design elements).
   - The repo currently exposes two active paths:
     - `SIAEngine` cognitive simulator
     - `AnalysisPipeline` generalized LLM-native analysis path

## Documentation created in this handoff slice

- `PRD.md` — quantified PRD aligned to the source specification
- `PRD.docx` — Word version of the same PRD content
- `recall.md` — expanded with a comprehensive multi-phase testing plan and release gates
- `LLM_HANDOFF.md` — this handoff

## What changed before this handoff

1. Generalized the active analysis/evaluation path.
2. Removed pandas-specific adapter, runners, scenarios, and cache files.
3. Added `.github\skills\problem-intelligence-factory\` with bundle scaffolding.
4. Established a generalized social-systems blinded corpus.
5. Defined quantified success bars for:
   - generalization across domains
   - live-grounded real-world readiness
   - skill-factory adoption and reuse

## Highest-priority next work

1. **Validate live-grounded runs**
   - enable grounding by default with graceful fallback
   - prove precision uplift >= 0.05
   - prove cluster grounding coverage >= 80%

2. **Prove fresh-session bundle reuse**
   - at least 1 bundle executed end-to-end by a fresh LLM session

3. **Reduce remaining spec-code drift**
   - ImmersionEngine and SocialLedger exist but are not yet wired into `SIAEngine`

## Main risks

| Risk | Severity | Why it matters |
|---|---|---|
| Single-domain validation | High | Current generalized proof is still narrow |
| Grounding disabled by default | High | Real-world readiness is not yet proven |
| Unwired spec components | Medium | Architectural fidelity claims exceed runtime integration |
| Skill-factory reuse unproven | Medium | Bundle system exists, but adoption is not yet demonstrated |
| Mock-heavy validation | Medium | Real LLM/runtime failures are still underexercised |

## Files to read first

| File | Why |
|---|---|
| `recall.md` | Continuity, testing gates, and current state |
| `PRD.md` | Quantified product/design requirements |
| `src\services\analysis_pipeline.py` | Core generalized analysis path |
| `simulation\run_blinded_test.py` | Default evaluation harness |
| `simulation\scenarios\generalized_blinded.py` | Current scenario corpus |
| `.github\skills\problem-intelligence-factory\SKILL.md` | Bundle-generation design |
| `configs\default.yaml` | Pressure, scarcity, and model config |
| `Cognitive_Insight_Architecture_Specification.docx` | Formal architectural source of truth |

## Commands to rerun first

```powershell
Set-Location 'C:\Users\ranandag\Documents\workvsc\SyntheticInsightArchitecture'
pytest tests -q
python -m simulation.run_blinded_test
```

## Decision rule for the next LLM

Do not treat the current generalized pass as final proof of the product vision. The architecture is now aligned, but release confidence must come from:

1. multi-domain blinded validation
2. grounded real-world validation
3. skill-factory reuse in fresh sessions
4. incremental wiring of the remaining spec components
