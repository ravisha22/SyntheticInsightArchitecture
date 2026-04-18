"""Scaffold a scenario-specific problem-intelligence bundle."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from textwrap import dedent


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "scenario"


def write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def bundle_yaml(scenario: str, domain: str, horizon: str) -> str:
    return dedent(
        f"""
        scenario:
          name: "{scenario}"
          slug: "{slugify(scenario)}"
          domain: "{domain}"
          horizon: "{horizon}"
          objective: "Replace with the decision this bundle should support"
          scarcity_constraint: "Replace with budget, time, staffing, or political-capital constraint"
          existential_failure_bar: "Replace with what would count as unacceptable failure"

        signal_families:
          - direct_pain
          - frontline_observation
          - outcome_evidence
          - structural_context
          - research_and_expert_input
          - future_direction
          - counter_signals
          - intervention_evidence

        outputs:
          - prioritized_interventions
          - deferred_actions
          - predicted_outcomes
          - scenario_skill
        """
    )


def collection_prompt(scenario: str) -> str:
    return dedent(
        f"""
        # Collection Prompt — {scenario}

        Collect background intelligence for this scenario before proposing interventions.

        Required coverage:
        1. Direct pain signals
        2. Frontline observations
        3. Outcome evidence
        4. Structural context
        5. Research and expert input
        6. Future-direction signals
        7. Counter-signals and noise checks
        8. Prior intervention evidence

        For each signal, capture:
        - source
        - summary
        - evidence
        - timestamp
        - stakeholder
        - severity hint
        - breadth hint
        - recency hint
        - credibility hint
        - independence hint
        - noise flags
        """
    )


def prioritization_prompt(scenario: str) -> str:
    return dedent(
        f"""
        # Prioritization Prompt — {scenario}

        Use the filtered signal set to rank interventions under scarcity.

        Questions to answer:
        1. Which root causes are existential if ignored?
        2. Which interventions reduce cascading harm?
        3. Which actions resolve multiple symptoms at once?
        4. Which ideas are loud but weakly evidenced?
        5. What should be deferred, and why?

        Output:
        - top interventions
        - rationale
        - predicted outcomes
        - failure risks
        - deferrals
        """
    )


def intervention_prompt(scenario: str) -> str:
    return dedent(
        f"""
        # Intervention Prompt — {scenario}

        For each high-priority intervention:
        - define the intervention
        - state what root cause it addresses
        - predict what should improve if it works
        - list what would falsify the intervention
        - describe the main implementation risk
        """
    )


def raw_signals_template() -> str:
    template = [
        {
            "id": "signal-001",
            "type": "complaint",
            "source": "replace-me",
            "summary": "replace-me",
            "evidence": "replace-me",
            "timestamp": "2026-01-01",
            "stakeholder": "replace-me",
            "severity_hint": 0.5,
            "breadth_hint": 0.5,
            "recency_hint": 0.5,
            "credibility_hint": 0.5,
            "independence_hint": 0.5,
            "noise_flags": [],
        }
    ]
    return json.dumps(template, indent=2)


FILTER_SCRIPT = dedent(
    """
    import json
    import sys
    from pathlib import Path


    def clamp(value):
        return max(0.0, min(1.0, float(value)))


    def score_signal(signal):
        severity = clamp(signal.get("severity_hint", 0.5))
        breadth = clamp(signal.get("breadth_hint", 0.5))
        recency = clamp(signal.get("recency_hint", 0.5))
        credibility = clamp(signal.get("credibility_hint", 0.5))
        independence = clamp(signal.get("independence_hint", 0.5))
        noise_penalty = 0.1 * len(signal.get("noise_flags", []))
        score = (
            severity * 0.20
            + breadth * 0.15
            + recency * 0.15
            + credibility * 0.25
            + independence * 0.25
            - noise_penalty
        )
        return round(max(score, 0.0), 3)


    def main():
        input_path = Path(sys.argv[1] if len(sys.argv) > 1 else "signals/raw_signals.template.json")
        output_path = Path(sys.argv[2] if len(sys.argv) > 2 else "signals/filtered_signals.json")

        signals = json.loads(input_path.read_text(encoding="utf-8"))
        filtered = []
        for signal in signals:
            signal = dict(signal)
            signal["reliability_score"] = score_signal(signal)
            signal["is_high_trust"] = signal["reliability_score"] >= 0.6
            filtered.append(signal)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(filtered, indent=2), encoding="utf-8")


    if __name__ == "__main__":
        main()
    """
)


SCORE_SCRIPT = dedent(
    """
    import json
    import sys
    from pathlib import Path


    def clamp(value):
        return max(0.0, min(1.0, float(value)))


    def score_intervention(item):
        existential = clamp(item.get("existential_risk_reduction", 0.5))
        breadth = clamp(item.get("breadth_of_impact", 0.5))
        compounding = clamp(item.get("compounding_benefit", 0.5))
        evidence = clamp(item.get("evidence_quality", 0.5))
        reversibility = clamp(item.get("reversibility", 0.5))
        score = (
            existential * 0.30
            + breadth * 0.20
            + compounding * 0.20
            + evidence * 0.20
            + reversibility * 0.10
        )
        return round(score, 3)


    def main():
        input_path = Path(sys.argv[1] if len(sys.argv) > 1 else "analysis/interventions.template.json")
        output_path = Path(sys.argv[2] if len(sys.argv) > 2 else "analysis/priorities.json")

        interventions = json.loads(input_path.read_text(encoding="utf-8"))
        ranked = []
        for item in interventions:
            item = dict(item)
            item["priority_score"] = score_intervention(item)
            ranked.append(item)

        ranked.sort(key=lambda item: item["priority_score"], reverse=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(ranked, indent=2), encoding="utf-8")


    if __name__ == "__main__":
        main()
    """
)


def intervention_template() -> str:
    template = [
        {
            "id": "intervention-001",
            "name": "replace-me",
            "root_cause": "replace-me",
            "existential_risk_reduction": 0.5,
            "breadth_of_impact": 0.5,
            "compounding_benefit": 0.5,
            "evidence_quality": 0.5,
            "reversibility": 0.5,
            "predicted_outcome": "replace-me",
        }
    ]
    return json.dumps(template, indent=2)


def scenario_skill(scenario: str) -> str:
    slug = slugify(scenario)
    return dedent(
        f"""
        ---
        name: {slug}-scenario
        description: |
          Scenario-specific skill for {scenario}. Use for signal collection, reliability filtering,
          prioritization under scarcity, and intervention design.
          Triggers: "{scenario}", "prioritize {slug}", "analyze {slug}".
        ---

        # {scenario}

        Use the bundle files in this folder before recommending interventions.

        1. Fill `signals/raw_signals.template.json`
        2. Run `scripts/filter_signals.py`
        3. Draft interventions in `analysis/interventions.template.json`
        4. Run `scripts/score_priorities.py`
        5. Use the prompts in `prompts/` to synthesize and recommend action
        """
    )


def main():
    parser = argparse.ArgumentParser(description="Scaffold a problem-intelligence bundle.")
    parser.add_argument("--scenario", required=True, help="Scenario or problem name")
    parser.add_argument("--output", required=True, help="Output directory for the generated bundle")
    parser.add_argument("--domain", default="general", help="Scenario domain (code, social, civic, product, etc.)")
    parser.add_argument("--horizon", default="near-term and structural", help="Decision horizon")
    args = parser.parse_args()

    scenario_dir = Path(args.output) / slugify(args.scenario)
    write_text(scenario_dir / "bundle.yaml", bundle_yaml(args.scenario, args.domain, args.horizon))
    write_text(scenario_dir / "prompts" / "collection_prompt.md", collection_prompt(args.scenario))
    write_text(scenario_dir / "prompts" / "prioritization_prompt.md", prioritization_prompt(args.scenario))
    write_text(scenario_dir / "prompts" / "intervention_prompt.md", intervention_prompt(args.scenario))
    write_text(scenario_dir / "signals" / "raw_signals.template.json", raw_signals_template())
    write_text(scenario_dir / "analysis" / "interventions.template.json", intervention_template())
    write_text(scenario_dir / "scripts" / "filter_signals.py", FILTER_SCRIPT)
    write_text(scenario_dir / "scripts" / "score_priorities.py", SCORE_SCRIPT)
    write_text(scenario_dir / "skill" / "SKILL.md", scenario_skill(args.scenario))

    print(f"Created bundle at: {scenario_dir}")


if __name__ == "__main__":
    main()
