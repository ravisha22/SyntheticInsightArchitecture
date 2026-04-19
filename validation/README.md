# SIA Validation Suite

This directory contains validation tests that go beyond the standard blinded evaluation to answer harder questions about whether the system actually works.

## Tests

| Test | File | Question it answers |
|------|------|-------------------|
| **Hindcast** | `../simulation/scenarios/hindcast_2008_blinded.py` | Can the system predict known outcomes using only pre-event signals? |
| **A/B Pipeline vs Prompt** | `ab_pipeline_vs_prompt.py` | Does the multi-stage pipeline produce better results than a raw LLM prompt? |
| **Noise Injection** | `noise_injection_test.py` | How robust is the system to irrelevant noise in the signal set? |

## Running

```bash
# Standard blinded eval (includes hindcast)
python -m simulation.run_blinded_test

# A/B pipeline vs raw LLM prompt
python validation/ab_pipeline_vs_prompt.py

# Noise injection robustness
python validation/noise_injection_test.py
```

## Results

See `RESULTS.md` for full results and analysis.
