
---
name: creator-trust-erosion-and-community-health-decay-scenario
description: |
  Scenario-specific skill for Creator trust erosion and community health decay. Use for signal collection, reliability filtering,
  prioritization under scarcity, and intervention design.
  Triggers: "Creator trust erosion and community health decay", "prioritize creator-trust-erosion-and-community-health-decay", "analyze creator-trust-erosion-and-community-health-decay".
---

# Creator trust erosion and community health decay

Use the bundle files in this folder before recommending interventions.

1. Fill `signals/raw_signals.template.json`
2. Run `scripts/filter_signals.py`
3. Draft interventions in `analysis/interventions.template.json`
4. Run `scripts/score_priorities.py`
5. Use the prompts in `prompts/` to synthesize and recommend action
