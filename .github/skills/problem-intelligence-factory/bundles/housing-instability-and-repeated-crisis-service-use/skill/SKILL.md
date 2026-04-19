
---
name: housing-instability-and-repeated-crisis-service-use-scenario
description: |
  Scenario-specific skill for Housing instability and repeated crisis-service use. Use for signal collection, reliability filtering,
  prioritization under scarcity, and intervention design.
  Triggers: "Housing instability and repeated crisis-service use", "prioritize housing-instability-and-repeated-crisis-service-use", "analyze housing-instability-and-repeated-crisis-service-use".
---

# Housing instability and repeated crisis-service use

Use the bundle files in this folder before recommending interventions.

1. Fill `signals/raw_signals.template.json`
2. Run `scripts/filter_signals.py`
3. Draft interventions in `analysis/interventions.template.json`
4. Run `scripts/score_priorities.py`
5. Use the prompts in `prompts/` to synthesize and recommend action
