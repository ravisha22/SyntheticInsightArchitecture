# Synthetic Insight Architecture (SIA)

A general-purpose problem intelligence system that takes messy, diverse signals from any domain — bug reports, community complaints, geopolitical events, economic indicators, field observations — and produces prioritised, evidence-grounded interventions with predicted outcomes.

## What Is This?

SIA models how genuine insight emerges: not by optimising LLM output quality, but by replicating the **cognitive process** — accumulated tension, failure-informed learning, cross-domain collision, scarcity-driven prioritisation, and autonomous goal formation. The architecture is described in the formal specification (`Cognitive_Insight_Architecture_Specification.docx`) as 13 core components plus 4 closure mechanisms.

The system has been validated across **5 domains**: social/civic, code/engineering, product/community, geopolitical (Iran-US conflict), and economic (Australia 2026-2029).

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -q

# Run multi-domain blinded evaluation (mock adapter, no API key needed)
python -m simulation.run_blinded_test

# Run with a real LLM
python -m simulation.run_blinded_test --adapter openai --api-key sk-... --model gpt-4o

# Scaffold a new scenario bundle
python .github/skills/problem-intelligence-factory/scripts/init_bundle.py \
  --scenario "Your problem statement" --output scenarios --domain your-domain
```

## Architecture

17 components across 4 layers:

**Foundation:** Deep Immersion, Tension Register, Failure Journal
**Creative:** Serendipity Engine, Dream Engine, Collision Search, Crystallization Detector
**Grounding:** Physical Reality Layer, Verification Harness, Integration Engine
**Existential:** Urgency Dynamics, Affect Homeostat, Body Budget, Social Ledger, Goal Pipeline

## Key Design Principles

1. **Fidelity over performance** — success = process similarity to humans, not output quality
2. **Deterministic MVP** — core loop runs without LLM calls (mock adapter)
3. **Unified state** — SQLite + append-only event log as single source of truth
4. **Human-readable artifacts** — inspectable at every step
5. **Scarcity is real** — resource budgets are enforced, not simulated

## Documentation

- `Cognitive_Insight_Architecture_Specification.docx` — Full formal specification
- `PRD.md` / `PRD.docx` — Quantified product requirements with release gates
- `LLM_HANDOFF.md` — Next-session handoff with validated state and priorities
- `recall.md` — Continuity file with comprehensive test plan and session proof
- `configs/default.yaml` — All tunable parameters and LLM backend configuration
- `.github/skills/problem-intelligence-factory/SKILL.md` — Scenario bundle factory

## Running with a Real LLM

By default, SIA uses a deterministic mock adapter for evaluation. To use a real LLM:

### OpenAI / GPT
```bash
python -m simulation.run_blinded_test --adapter openai --api-key sk-... --model gpt-4o
```

### Azure OpenAI
```bash
python -m simulation.run_blinded_test --adapter openai \
  --base-url https://your-resource.openai.azure.com/openai/deployments/your-deployment \
  --api-key your-azure-key --model gpt-4o
```

### Groq
```bash
python -m simulation.run_blinded_test --adapter openai \
  --base-url https://api.groq.com/openai/v1 \
  --api-key gsk_... --model llama-3.1-70b-versatile
```

### Local (Ollama, LM Studio, vLLM)
```bash
# Ollama native
python -m simulation.run_blinded_test --adapter ollama --model llama3.1:8b-instruct

# Ollama OpenAI-compatible mode
python -m simulation.run_blinded_test --adapter openai \
  --base-url http://localhost:11434/v1 --model llama3.1:8b-instruct

# LM Studio
python -m simulation.run_blinded_test --adapter openai \
  --base-url http://localhost:1234/v1 --model local-model
```

### Environment variable
```bash
export SIA_API_KEY=sk-...
python -m simulation.run_blinded_test --adapter openai --model gpt-4o
```
