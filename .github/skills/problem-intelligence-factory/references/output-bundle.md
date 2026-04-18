# Output Bundle Specification

The generated bundle should be understandable without replaying the whole design session.

## Required Files

| File | Purpose |
|---|---|
| `bundle.yaml` | scenario metadata, scope, scarcity, outcomes, signal families |
| `prompts/collection_prompt.md` | instructions for broad background-information collection |
| `prompts/prioritization_prompt.md` | existential, scarcity-driven ranking prompt |
| `prompts/intervention_prompt.md` | intervention design and predicted outcomes prompt |
| `signals/raw_signals.template.json` | signal register template with quality fields |
| `scripts/filter_signals.py` | deterministic reliability and noise filtering |
| `scripts/score_priorities.py` | deterministic scoring of interventions under scarcity |
| `skill/SKILL.md` | scenario-specific reusable skill |

## Signal Register Shape

Each raw signal should support:

```json
{
  "id": "signal-001",
  "type": "complaint",
  "source": "field interview",
  "summary": "Short description",
  "evidence": "What was observed or claimed",
  "timestamp": "2026-04-19",
  "stakeholder": "tenant",
  "severity_hint": 0.8,
  "breadth_hint": 0.6,
  "recency_hint": 0.9,
  "credibility_hint": 0.7,
  "independence_hint": 0.8,
  "noise_flags": ["possible-duplication"]
}
```

## Bundle Quality Standard

The bundle is not complete if it only contains:

- loud complaints
- local anecdotes
- present-day symptoms
- one stakeholder perspective

It is complete when it supports:

1. signal collection
2. signal filtering
3. root-cause synthesis
4. scarcity-driven prioritization
5. predicted-outcome review
