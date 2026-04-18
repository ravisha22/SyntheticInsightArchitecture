# Problem Intelligence Factory Workflows

## Standard Workflow

Use this sequence for every scenario:

1. **Frame the scenario**
   - Problem statement
   - Objective
   - Time horizon
   - Scarcity constraint
   - Existential failure bar

2. **Build the source map**
   - Direct pain signals
   - Operational signals
   - Structural signals
   - Future-direction signals
   - Counter-signals

3. **Create the initial bundle**
   - Run `scripts/init_bundle.py`
   - Fill `bundle.yaml`
   - Start `signals/raw_signals.template.json`

4. **Collect evidence**
   - Gather candidate signals into the raw register
   - Preserve uncertainty instead of flattening it

5. **Filter noise**
   - Run `scripts/filter_signals.py`
   - Review low-trust and duplicated signals manually

6. **Score priorities**
   - Run `scripts/score_priorities.py`
   - Check whether the top interventions make systemic sense

7. **Write the scenario skill**
   - Finalize `skill/SKILL.md`
   - Keep it procedural, reusable, and domain-aware

## Decision Gates

### Gate 1: Is the problem framed?

Do not collect signals until these are explicit:

- what decision is needed
- who is affected
- what the scarcity constraint is
- what failure looks like

### Gate 2: Is the signal map broad enough?

Do not prioritize until the evidence mix includes:

- present pain
- structural causes
- future trajectory
- counter-signals

### Gate 3: Is the bundle reusable?

Do not finish until another agent could use the bundle without replaying the full investigation.
