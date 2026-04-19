---
name: problem-intelligence-factory
description: |
  Scenario-driven skill factory for building 360-degree signal collection, reliability filtering,
  prioritization bundles, and scenario-specific skills for complex problems.
  Use for code repos, social issues, public systems, product problems, community operations,
  institutional failures, or any problem that requires existential triage under scarcity.
  Triggers: "create scenario skill", "collect background signals", "360 input analysis",
  "prioritization bundle", "problem intelligence", "generalized prioritization".
---

# Problem Intelligence Factory

Turn a user scenario into a reusable problem-solving bundle:

1. A scenario-specific skill
2. A background-information collection plan
3. A reliability and noise-filtering rubric
4. Prompt scaffolds for synthesis, prioritization, and intervention design
5. Deterministic scripts for filtering signals and scoring priorities

This skill exists to keep the project generalized. It must work for:

| Scenario type | Example |
|---|---|
| Code / engineering | recurring production incidents, dependency failures, backlog triage |
| Social / civic | housing instability, youth disengagement, violence prevention |
| Public systems | permit bottlenecks, health-service access, school absenteeism |
| Product / community | churn, complaints, creator trust, moderation backlog |

## Before You Start

Always frame the scenario before collecting signals. Capture:

1. **Problem statement** — what is going wrong?
2. **Decision objective** — what decision or prioritization is needed?
3. **Unit of impact** — users, residents, teams, services, communities, institutions
4. **Time horizon** — immediate, near-term, or structural
5. **Scarcity constraint** — budget, people, attention, political capital, time
6. **Failure bar** — what would count as existential or unacceptable?

If these are not clear, ask for them first.

## Core Workflow

Follow this sequence:

1. **Frame the system**
   - Define the boundary, decision horizon, and scarcity constraint.
   - State what “good” and “bad” outcomes look like.

2. **Map 360-degree inputs**
   - Gather direct pain signals, operational signals, structural context, future trajectory, and counter-signals.
   - Include both present symptoms and longer-range directional inputs.

3. **Filter noise**
   - Score signals by credibility, directness, recency, independence, and manipulation risk.
   - Remove duplicated, weak, brigaded, or stale inputs from the high-trust set.

4. **Synthesize root causes**
   - Cluster symptoms into systemic weaknesses.
   - Separate symptoms from leverage points.

5. **Prioritize interventions under scarcity**
   - Rank interventions by existential risk reduction, breadth, compounding effect, reversibility, and evidence quality.
   - Explicitly state what is deferred and why.

6. **Package the result**
   - Create a scenario-specific skill and prompt bundle that can be reused later.

## 360-Degree Signal Coverage

At minimum, cover these signal families:

| Family | Examples | Why it matters |
|---|---|---|
| Direct pain | complaints, bug reports, support tickets, crisis logs | shows experienced harm |
| Frontline observation | staff notes, moderators, operators, case workers, maintainers | captures practical friction |
| Outcome evidence | incident rates, dropout, relapse, outages, churn, response time | shows what failure costs |
| Structural context | incentives, ownership, policy, regulation, funding, dependencies | explains why symptoms recur |
| Lived experience | interviews, testimony, community feedback, retrospectives | adds context and nuance |
| Research / expert input | academic work, benchmarks, standards, evaluations | checks local narratives against broader evidence |
| Future trajectory | trends, industry direction, demographic shifts, technology changes | prevents local optimization to a dying state |
| Counter-signals | contrary reports, outliers, strategic noise, brigading, cherry-picking | prevents overfitting and capture |

Use more families when the scenario is high stakes.

## Reliability Filter

Prioritize signals that are:

1. **Direct** — close to the failure or harm
2. **Independent** — not just repeated copies of the same claim
3. **Credible** — backed by expertise, operational proximity, or verifiable evidence
4. **Recent enough** — still relevant to the decision horizon
5. **Outcome-linked** — tied to real harm, not just loudness
6. **Hard to game** — resistant to manipulation, novelty spikes, or stakeholder theater

Low-trust signals can stay in the bundle, but they should not dominate prioritization.

## Outputs You Must Produce

Every run should produce:

1. **Scenario brief**
2. **Signal map**
3. **Noise / reliability rubric**
4. **Prioritized intervention list**
5. **Predicted outcomes and what would falsify them**
6. **Scenario-specific skill bundle**

Use the scaffolder:

```bash
python .github/skills/problem-intelligence-factory/scripts/init_bundle.py ^
  --scenario "Housing instability and repeated crisis-service use" ^
  --output C:\path\to\output ^
  --domain social
```

The generated bundle contains:

- `bundle.yaml`
- `prompts/collection_prompt.md`
- `prompts/prioritization_prompt.md`
- `prompts/intervention_prompt.md`
- `signals/raw_signals.template.json`
- `scripts/filter_signals.py`
- `scripts/score_priorities.py`
- `skill/SKILL.md`

## Bundle Rules

### Collection prompt

Must force broad coverage before prioritization:

- direct complaints and incidents
- observational and frontline evidence
- expert and academic material
- trend and trajectory inputs
- counter-evidence and noise checks

### Prioritization prompt

Must force existential and scarcity thinking:

- what cascades?
- what compounds?
- what protects the most people or systems?
- what single intervention clears multiple symptoms?
- what is loud but not strategically important?

### Intervention prompt

Must connect:

- root cause
- intervention
- predicted outcomes
- failure modes
- evidence needed to continue or stop

## Recommended Report Shape

The report should lead with a **narrative** that connects the causal chain for the reader, followed by a **summary table**. The narrative must trace the transmission path from root cause to impact, showing how the clusters interact and compound. It should read as a coherent story, not a list of findings.

Use this default shape unless the user asks for a different one:

```markdown
# [Scenario Title]

## Narrative

[Multi-paragraph narrative that:]
- Starts from the triggering event or structural condition
- Traces the causal chain through each systemic weakness
- Shows how the weaknesses compound each other
- Uses specific numbers and evidence from the signals
- Ends with the most dangerous feedback loop
- Cites sources where available

## Summary

### Systemic Root Causes

| # | Root Cause | Severity | Key Signals | Mechanism |
|---|-----------|----------|-------------|-----------|
| 1 | ... | Existential / Major | signal descriptions | how it transmits harm |

### Prioritized Interventions

| # | Intervention | Root Cause | Score | Predicted Outcome |
|---|-------------|-----------|-------|-------------------|
| 1 | ... | ... | 0.xxx | what should change if it works |

### What Would Falsify These

- If intervention #1 is funded but [metric] doesn't improve → [alternative explanation]
- ...

### Scenario Projections

| Horizon | What happens |
|---------|-------------|
| 6 months | ... |
| 18 months | ... |
| 3 years | ... |
```

## When Creating the Scenario-Specific Skill

The generated skill should teach the next agent to:

1. gather evidence before solving
2. separate symptoms from leverage points
3. score signal reliability explicitly
4. prioritize under scarcity
5. predict outcomes before recommending action

## Reference Files

| File | Purpose |
|---|---|
| [references/workflows.md](references/workflows.md) | End-to-end factory workflow and operating sequence |
| [references/signal-taxonomy.md](references/signal-taxonomy.md) | 360-degree signal families and examples |
| [references/output-bundle.md](references/output-bundle.md) | Bundle contents and expected file roles |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Validation checklist for scenario bundles |
