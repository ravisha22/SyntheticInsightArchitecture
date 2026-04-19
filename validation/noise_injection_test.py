"""Noise injection robustness test — measures precision degradation as noise increases."""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simulation.scenarios.generalized_blinded import build_generalized_scenario
from simulation.run_blinded_test import run_condition


NOISE_POOL = [
    {"number": 201, "signal_type": "feedback", "source": "astronomy-club",
     "title": "Telescope mirror needs realignment after transport",
     "body": "The primary mirror shifted during the move to the new observatory site.",
     "labels": ["Telescope", "Optics", "Alignment"]},
    {"number": 202, "signal_type": "field_observation", "source": "botanical-survey",
     "title": "Fern canopy density increased after rainfall season",
     "body": "The forest floor received less light as upper canopy ferns expanded.",
     "labels": ["Botany", "Ferns", "Canopy"]},
    {"number": 203, "signal_type": "community_report", "source": "pottery-guild",
     "title": "Kiln temperature variance produced unexpected glaze colours",
     "body": "Members noticed different colours when the kiln cycled unevenly during firing.",
     "labels": ["Pottery", "Kiln", "Glaze"]},
    {"number": 204, "signal_type": "other", "source": "weather-station",
     "title": "Morning dew collection exceeded seasonal average",
     "body": "The moisture traps recorded higher volumes than the ten-year mean.",
     "labels": ["Weather", "Dew", "Collection"]},
    {"number": 205, "signal_type": "feedback", "source": "chess-club",
     "title": "Opening repertoire database needs format update",
     "body": "The club's game archive uses an outdated notation standard.",
     "labels": ["Chess", "Database", "Notation"]},
    {"number": 206, "signal_type": "field_observation", "source": "tide-monitor",
     "title": "Spring tide exceeded predicted height by twelve centimetres",
     "body": "Coastal gauges recorded higher water than the forecast model expected.",
     "labels": ["Tide", "Coastal", "Measurement"]},
    {"number": 207, "signal_type": "community_report", "source": "birdwatch-network",
     "title": "Migratory pattern shifted two weeks earlier this year",
     "body": "Observers in the southern corridor reported early arrivals of wading birds.",
     "labels": ["Birds", "Migration", "Seasonal"]},
    {"number": 208, "signal_type": "other", "source": "soil-lab",
     "title": "Nitrogen fixation rates lower than expected in test plots",
     "body": "The legume cover crop produced less nitrogen than the trial design assumed.",
     "labels": ["Soil", "Nitrogen", "Agriculture"]},
]


def inject_noise(scenario, noise_fraction, seed=42):
    """Add noise signals to a scenario at the given fraction of real signal count."""
    real_issues = list(scenario["issues"])
    n_noise = max(1, int(len(real_issues) * noise_fraction))
    rng = random.Random(seed)
    noise = rng.sample(NOISE_POOL, min(n_noise, len(NOISE_POOL)))
    noisy = real_issues + [{**n, "labels": list(n["labels"]), "tags": list(n["labels"])} for n in noise]
    return {"issues": noisy, "observed_outcomes": list(scenario["observed_outcomes"])}


def main():
    print("=" * 60)
    print("Noise Injection Robustness Test")
    print("=" * 60)

    scenario = build_generalized_scenario()

    result_0 = run_condition("0% noise", scenario, "noise_0")
    p_0 = result_0["score"]["precision"]
    h_0 = result_0["score"]["hit_count"]

    results = [{"noise": "0%", "precision": p_0, "hits": h_0, "total_signals": len(scenario["issues"])}]

    for pct in [25, 50, 75, 100]:
        noisy = inject_noise(scenario, pct / 100.0)
        label = f"{pct}% noise"
        result = run_condition(label, noisy, f"noise_{pct}")
        p = result["score"]["precision"]
        h = result["score"]["hit_count"]
        results.append({"noise": f"{pct}%", "precision": p, "hits": h, "total_signals": len(noisy["issues"])})

    print(f"\n{'Noise':<10} {'Signals':<10} {'Hits':<6} {'Precision':<10} {'Degradation':<12}")
    print("-" * 50)
    for result in results:
        deg = p_0 - result["precision"] if p_0 > 0 else 0
        print(f"{result['noise']:<10} {result['total_signals']:<10} {result['hits']:<6} {result['precision']:<10.3f} {deg:+.3f}")

    precision_at_75 = results[-2]["precision"] if len(results) > 3 else 0
    graceful = precision_at_75 >= p_0 * 0.5
    print(f"\nBaseline precision: {p_0:.3f}")
    print(f"Precision at 75% noise: {precision_at_75:.3f}")
    print(f"Graceful degradation (>= 50% of baseline): {'YES' if graceful else 'NO'}")


if __name__ == "__main__":
    main()
