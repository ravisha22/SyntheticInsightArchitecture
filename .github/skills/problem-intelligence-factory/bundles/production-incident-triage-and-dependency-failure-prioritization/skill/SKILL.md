
---
name: production-incident-triage-and-dependency-failure-prioritization-scenario
description: |
  Scenario-specific skill for Production incident triage and dependency failure prioritization. Use for signal collection, reliability filtering,
  prioritization under scarcity, and intervention design.
  Triggers: "Production incident triage and dependency failure prioritization", "prioritize production-incident-triage-and-dependency-failure-prioritization", "analyze production-incident-triage-and-dependency-failure-prioritization".
---

# Production incident triage and dependency failure prioritization

Use the bundle files in this folder before recommending interventions.

1. Fill `signals/raw_signals.template.json`
2. Run `scripts/filter_signals.py`
3. Draft interventions in `analysis/interventions.template.json`
4. Run `scripts/score_priorities.py`
5. Use the prompts in `prompts/` to synthesize and recommend action
