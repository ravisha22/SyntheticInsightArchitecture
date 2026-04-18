# Acceptance Criteria: problem-intelligence-factory

## 1. Trigger and Purpose

### ✅ Correct

- The skill description makes it clear that the skill is for scenario-driven problem solving.
- Trigger phrases mention background signals, 360-degree input analysis, and prioritization bundles.

### ❌ Incorrect

- The skill reads like a narrow code-only helper.
- The skill only talks about bugs or repositories.

## 2. Bundle Coverage

### ✅ Correct

The skill creates or instructs creation of:

- a scenario-specific skill
- a collection prompt
- a prioritization prompt
- an intervention prompt
- a raw signal register template
- deterministic filtering and scoring scripts

### ❌ Incorrect

- only a prompt
- only a report
- only a prioritization script with no collection phase

## 3. Signal Collection Depth

### ✅ Correct

The workflow explicitly requires:

- direct pain signals
- structural signals
- future-direction signals
- counter-signals

### ❌ Incorrect

- collection based only on complaints or bug reports
- collection that ignores reliability and manipulation risk

## 4. Reliability Filter

### ✅ Correct

Signals are scored on:

- credibility
- directness
- recency
- independence
- noise / manipulation risk

### ❌ Incorrect

- all signals are treated as equally trustworthy
- duplication and brigading are not checked

## 5. Prioritization Logic

### ✅ Correct

The prioritization prompt and scripts account for:

- existential risk
- breadth of impact
- scarcity
- compounding effects
- evidence quality
- predicted outcomes

### ❌ Incorrect

- ranking by loudness alone
- ranking without explicit deferrals
- recommendations without predicted outcomes

## 6. Domain Generality

### ✅ Correct

The skill can be applied to:

- code and operational systems
- social and civic systems
- institutional and policy systems
- product and community systems

### ❌ Incorrect

- the language assumes software-only use
- the examples are all from one domain
