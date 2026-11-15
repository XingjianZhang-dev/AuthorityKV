import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def test_outcome_runners_resolve_scripts_module() -> None:
    code = """
import inspect
import run_outcome_informed_authority as outcome
import run_retention_diagnostic as retention
expected = 'scripts/run_kvpress_authority.py'
outcome_source = inspect.getsourcefile(inspect.unwrap(outcome.generate_one))
retention_source = inspect.getsourcefile(
    inspect.unwrap(retention.generate_one)
)
assert outcome_source is not None
assert retention_source is not None
assert outcome_source.replace('\\\\', '/').endswith(
    'scripts/generate_layerwise_cache.py'
), outcome_source
assert retention_source.replace('\\\\', '/').endswith(
    expected
), retention_source
"""
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={"PYTHONPATH": str(SCRIPTS)},
        check=True,
    )
