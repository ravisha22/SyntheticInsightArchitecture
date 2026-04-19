# Handoff: Synthetic Insight Architecture

## Current validated state

1. **Generalized core is green.**
   - `pytest tests -q` -> **53 passed**
   - `python -m simulation.run_blinded_test` -> **5/5 domains pass 5/5 conditions**

2. **Current blinded-eval readings (multi-domain)**
   - Social / Civic: 5/5 PASS (precision 0.500, recall 1.000)
   - Code / Engineering: 5/5 PASS (precision 0.750, recall 1.000)
   - Product / Community: 5/5 PASS (precision 1.000, recall 1.000)
   - Middle East Conflict: 5/5 PASS (precision 1.000, recall 1.000)
   - Australia Economy: 5/5 PASS (precision 0.800, recall 1.000)
   - **Phase 1 gate: MET (5 domains)**
   - **Phase 2 grounding gate: MET (coverage 100%, uplift +0.500)**

3. **Real LLM integration ready.**
   - `src/adapters/openai_api.py` — works with any OpenAI-compatible API
   - CLI: `--adapter openai --api-key ... --model gpt-4o`
   - Supports: OpenAI, Azure, Groq, Together, vLLM, LM Studio, Ollama

4. **Skill-factory bundles committed (3/3, each 9/9 files)**
   - production-incident-triage (code), housing-instability (social), creator-trust (product)

5. **Real-world scenarios applied (2)**
   - Middle East conflict (Iran-US): 14 signals, 4 root causes, 6 interventions
   - Australia economy (2026-2029): 17 signals, 4 root causes, 8 interventions

6. **Spec components wired (2/4)**
   - VerificationHarness and IntegrationEngine wired into `SIAEngine`
   - ImmersionEngine and SocialLedger remain unwired

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

1. **Run end-to-end with a live LLM**
   - Use `--adapter openai --api-key ... --model gpt-4o` against real signals
   - Compare real LLM results to MockAdapter baseline
   - Prove the multi-stage pipeline (analyze → cluster → ground → prioritize) produces better analysis than a single prompt

2. **Wire remaining spec components**
   - ImmersionEngine and SocialLedger exist but are not connected to `SIAEngine`

3. **Automate narrative generation**
   - The report format should produce a narrative-first output followed by summary table
   - Currently narrative is manual; integrate it into the runner or a post-processing step

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
