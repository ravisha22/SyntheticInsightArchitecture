"""Run the full weekly SIA analysis pipeline."""
import subprocess
import sys
from pathlib import Path

WEBAPP_DIR = Path(__file__).parent


def _resolve_script(script: str) -> Path:
    path = Path(script)
    if not path.is_absolute():
        script_text = script.replace("/", "\\")
        if script_text.startswith("webapp\\"):
            script_text = script_text.split("\\", 1)[1]
        path = WEBAPP_DIR / script_text
    return path


def run_step(name: str, script: str):
    print(f"\n{'=' * 60}")
    print(f"Step: {name}")
    print(f"{'=' * 60}")
    result = subprocess.run(
        [sys.executable, str(_resolve_script(script))],
        cwd=str(WEBAPP_DIR.parent),
    )
    if result.returncode != 0:
        print(f"FAILED: {name}")
        sys.exit(1)


def main():
    run_step("Collect stories", "collect_stories.py")
    run_step("Run analysis", "run_analysis.py")
    run_step("Generate site", "generate_site.py")
    print(f"\n{'=' * 60}")
    print("Done! Open webapp/static/index.html to view.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
