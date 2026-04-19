# Synthetic Insight Architecture (SIA)

A 17-component computational framework that replicates the human creative insight process.

## What Is This?

SIA models how humans arrive at creative breakthroughs — not by improving LLM output quality, but by replicating the **cognitive process**: accumulated tension, failure-informed learning, cross-domain collision, purpose-biased dreaming, scarcity-driven prioritisation, and autonomous goal formation.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run the PageRank case study simulation
python -m simulation.run_pagerank
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
- `configs/default.yaml` — All tunable parameters

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
