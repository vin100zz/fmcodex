from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from random import Random

from benchmarks.fixtures import build_fixture, load_fixture, save_fixture
from benchmarks.match import run_match_suite
from core.config import load_config
from core.world import derive_active_club_ratings, import_source_data


DEFAULT_FIXTURE = Path("benchmarks/effectifs/source_v1.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Football Manager Light calibration suites.")
    parser.add_argument("--suite", choices=("match",), default="match")
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--create-snapshot", action="store_true")
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()

    workspace = Path.cwd()
    config = load_config(workspace / "config")
    if arguments.create_snapshot:
        report = import_source_data(workspace / "data", config)
        fixture = build_fixture(
            derive_active_club_ratings(report, config),
            workspace / "data" / "players.csv",
            config.world.version_config,
        )
        save_fixture(fixture, workspace / arguments.fixture)
        print(f"Snapshot created: {arguments.fixture} ({len(fixture.ratings)} clubs)")
        return 0

    fixture = load_fixture(workspace / arguments.fixture)
    benchmark_config = config.raw_documents["benchmarks"]
    default_iterations = int(benchmark_config["execution"]["iterations_defaut_match"])
    seed = int(benchmark_config["execution"]["graine_defaut"])
    checks = run_match_suite(config, fixture, arguments.iterations or default_iterations, Random(seed))
    for check in checks:
        state = "OK" if check.passed else "ECHEC"
        print(
            f"{check.reference_id}/{check.metric:<9} {check.measured:.3f} "
            f"cible {check.target:.3f} ±{check.tolerance:.3f} {state}"
        )
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(
            json.dumps([asdict(check) | {"passed": check.passed} for check in checks], indent=2) + "\n",
            encoding="utf-8",
        )
    return 0 if all(check.passed for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
