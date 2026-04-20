import importlib.util
import logging
from pathlib import Path

import azure.functions as func


def _load_daily_run_module():
    base_dir = Path(__file__).resolve().parent
    module_path = base_dir / "daily_run.py"
    if not module_path.exists():
        module_path = base_dir.parent / "daily_run.py"
    spec = importlib.util.spec_from_file_location("sia_daily_run", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


app = func.FunctionApp()


@app.timer_trigger(schedule="0 0 20 * * *", arg_name="timer", run_on_startup=False, use_monitor=True)
def sia_daily_analysis(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logging.warning("SIA daily analysis timer is past due.")
    logging.info("SIA daily analysis triggered")
    module = _load_daily_run_module()
    summary = module.run_daily_pipeline()
    logging.info("SIA daily analysis complete: %s", summary)
