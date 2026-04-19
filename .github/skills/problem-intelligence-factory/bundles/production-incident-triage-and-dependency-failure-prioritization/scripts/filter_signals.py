
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
