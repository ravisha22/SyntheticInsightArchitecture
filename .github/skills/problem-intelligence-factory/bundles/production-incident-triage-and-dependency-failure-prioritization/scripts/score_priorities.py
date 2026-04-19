
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
