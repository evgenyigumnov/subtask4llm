#!/usr/bin/env python3
"""Behavioral tests for the sequential Codex workflow runner.

The suite never invokes a real Codex model. Integration cases put a tiny fake
``codex`` executable at the front of ``PATH`` and assert what the runner sends
to it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_workflow.py"


def step(
    step_id: str,
    *,
    task: str | None = None,
    depends_on: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": step_id,
        "title": f"Step {step_id}",
        "task": task or f"Perform task {step_id}",
        "acceptance": [f"Task {step_id} is complete"],
        "depends_on": depends_on or [],
    }


def plan(*steps: dict[str, object]) -> dict[str, object]:
    return {
        "version": 1,
        "goal": "Exercise the workflow runner",
        "steps": list(steps),
    }


class RunnerCase(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="subtask4llm-test-")
        self.base = Path(self.tempdir.name)
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_runner(
        self,
        plan_data: dict[str, object],
        *extra_args: str,
        env_updates: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        plan_path = self.base / "plan.json"
        plan_path.write_text(json.dumps(plan_data), encoding="utf-8")
        env = os.environ.copy()
        env.pop("CODEX_WORKFLOW_CHILD", None)
        env.pop("CODEX_WORKFLOW_DEPTH", None)
        if env_updates:
            env.update(env_updates)
        return subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                str(plan_path),
                "--workspace",
                str(self.workspace),
                "--model",
                "test-worker-model",
                *extra_args,
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )

    def assert_failed_with(self, result: subprocess.CompletedProcess[str], *words: str) -> None:
        self.assertNotEqual(result.returncode, 0, result.stdout)
        output = (result.stdout + "\n" + result.stderr).lower()
        self.assertTrue(
            any(word.lower() in output for word in words),
            f"expected one of {words!r} in:\n{output}",
        )


class PlanValidationTests(RunnerCase):
    def test_rejects_more_than_ten_steps(self) -> None:
        result = self.run_runner(
            plan(*(step(f"s{index}") for index in range(11))),
            "--dry-run",
        )
        self.assert_failed_with(result, "10", "maximum", "too many")

    def test_rejects_duplicate_step_ids(self) -> None:
        result = self.run_runner(plan(step("same"), step("same")), "--dry-run")
        self.assert_failed_with(result, "duplicate", "unique")

    def test_rejects_unknown_or_future_dependency(self) -> None:
        result = self.run_runner(
            plan(step("first", depends_on=["later"]), step("later")),
            "--dry-run",
        )
        self.assert_failed_with(result, "dependency", "depends_on", "earlier")

    def test_rejects_step_ids_outside_documented_safe_alphabet(self) -> None:
        for step_id in ("Uppercase", "contains.dot"):
            with self.subTest(step_id=step_id):
                result = self.run_runner(plan(step(step_id)), "--dry-run")
                self.assert_failed_with(result, "id", "match", "lowercase")

    def test_rejects_empty_acceptance_criteria(self) -> None:
        invalid_step = step("empty-acceptance")
        invalid_step["acceptance"] = []
        result = self.run_runner(plan(invalid_step), "--dry-run")
        self.assert_failed_with(result, "acceptance", "empty")

    def test_child_environment_blocks_even_dry_run(self) -> None:
        result = self.run_runner(
            plan(step("only")),
            "--dry-run",
            env_updates={"CODEX_WORKFLOW_CHILD": "1"},
        )
        self.assert_failed_with(result, "child", "nested", "recurs")

    def test_positive_depth_blocks_even_without_child_flag(self) -> None:
        result = self.run_runner(
            plan(step("only")),
            "--dry-run",
            env_updates={"CODEX_WORKFLOW_DEPTH": "1"},
        )
        self.assert_failed_with(result, "depth", "nested", "recurs")

    def test_malformed_or_nonzero_depth_fails_closed(self) -> None:
        for depth in ("not-a-number", "-1", "2"):
            with self.subTest(depth=depth):
                result = self.run_runner(
                    plan(step("only")),
                    "--dry-run",
                    env_updates={"CODEX_WORKFLOW_DEPTH": depth},
                )
                self.assert_failed_with(result, "depth", "nested", "recurs", "invalid")

    def test_dry_run_exposes_safety_critical_child_arguments(self) -> None:
        result = self.run_runner(plan(step("only")), "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        for expected in (
            "--ephemeral",
            "--strict-config",
            "--output-schema",
            "--output-last-message",
            "--sandbox",
            "workspace-write",
            "skills.config",
            "enabled=false",
            "CODEX_WORKFLOW_CHILD",
            "CODEX_WORKFLOW_DEPTH",
            str((ROOT / "SKILL.md").resolve()),
        ):
            self.assertIn(expected, output)


class FakeCodexTests(RunnerCase):
    def setUp(self) -> None:
        super().setUp()
        self.bin_dir = self.base / "bin"
        self.bin_dir.mkdir()
        self.log_path = self.base / "codex-calls.jsonl"
        self.state_path = self.base / "codex-state.txt"
        fake_codex = self.bin_dir / "codex"
        fake_codex.write_text(
            textwrap.dedent(
                f"""\
                #!{sys.executable}
                import json
                import os
                from pathlib import Path
                import sys

                args = sys.argv[1:]
                prompt = sys.stdin.read() if "-" in args else (args[-1] if args else "")
                state_path = Path(os.environ["FAKE_CODEX_STATE"])
                try:
                    call_number = int(state_path.read_text(encoding="utf-8")) + 1
                except (FileNotFoundError, ValueError):
                    call_number = 1
                state_path.write_text(str(call_number), encoding="utf-8")

                record = {{
                    "args": args,
                    "prompt": prompt,
                    "child": os.environ.get("CODEX_WORKFLOW_CHILD"),
                    "depth": os.environ.get("CODEX_WORKFLOW_DEPTH"),
                }}
                with Path(os.environ["FAKE_CODEX_LOG"]).open("a", encoding="utf-8") as log:
                    log.write(json.dumps(record) + "\\n")

                if call_number <= int(os.environ.get("FAKE_CODEX_FAILS", "0")):
                    print("synthetic child failure", file=sys.stderr)
                    raise SystemExit(9)

                output_index = args.index("--output-last-message") + 1
                if os.environ.get("FAKE_CODEX_NO_OUTPUT") == "1":
                    raise SystemExit(0)
                if os.environ.get("FAKE_CODEX_INVALID_OUTPUT") == "1":
                    Path(args[output_index]).write_text("not-json", encoding="utf-8")
                    raise SystemExit(0)
                result = {{
                    "status": os.environ.get("FAKE_CODEX_STATUS", "completed"),
                    "summary": os.environ.get("FAKE_CODEX_SUMMARY", f"summary-{{call_number}}"),
                    "files_changed": [f"file-{{call_number}}.txt"],
                    "verification": [{{
                        "command": "synthetic-check",
                        "outcome": "passed",
                    }}],
                    "risks": [],
                }}
                Path(args[output_index]).write_text(json.dumps(result), encoding="utf-8")
                print(json.dumps(result))
                """
            ),
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

    def fake_env(self, **updates: str) -> dict[str, str]:
        env = {
            "PATH": str(self.bin_dir) + os.pathsep + os.environ.get("PATH", ""),
            "FAKE_CODEX_LOG": str(self.log_path),
            "FAKE_CODEX_STATE": str(self.state_path),
        }
        env.update(updates)
        return env

    def calls(self) -> list[dict[str, object]]:
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
        ]

    def test_runs_steps_sequentially_and_limits_dependency_context(self) -> None:
        long_summary = "UNIQUE_DEPENDENCY_TEXT_" + ("x" * 200)
        result = self.run_runner(
            plan(
                step("build"),
                step("test", depends_on=["build"]),
                step("check"),
            ),
            "--retries",
            "0",
            "--max-summary-chars",
            "64",
            env_updates=self.fake_env(FAKE_CODEX_SUMMARY=long_summary),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(report.get("status"), {"completed", "success"})
        self.assertEqual(len(report["steps"]), 3)

        calls = self.calls()
        self.assertEqual(len(calls), 3)
        self.assertEqual([call["child"] for call in calls], ["1", "1", "1"])
        self.assertEqual([call["depth"] for call in calls], ["1", "1", "1"])
        self.assertIn("UNIQUE_DEPENDENCY_TEXT_", calls[1]["prompt"])
        self.assertNotIn(long_summary, calls[1]["prompt"])
        self.assertNotIn("UNIQUE_DEPENDENCY_TEXT_", calls[2]["prompt"])

    def test_retries_once_then_stops_before_later_steps(self) -> None:
        result = self.run_runner(
            plan(
                step("broken", task="BROKEN_TASK_MARKER"),
                step("must-not-run", task="LATER_TASK_MARKER"),
            ),
            "--retries",
            "1",
            env_updates=self.fake_env(FAKE_CODEX_FAILS="2"),
        )
        self.assertNotEqual(result.returncode, 0)
        calls = self.calls()
        self.assertEqual(len(calls), 2)
        self.assertTrue(all("BROKEN_TASK_MARKER" in call["prompt"] for call in calls))
        self.assertTrue(all("LATER_TASK_MARKER" not in call["prompt"] for call in calls))
        report = json.loads(result.stdout)
        self.assertIn(report.get("status"), {"failed", "stopped"})

    def test_missing_or_invalid_child_result_retries_then_fails(self) -> None:
        for key in ("FAKE_CODEX_NO_OUTPUT", "FAKE_CODEX_INVALID_OUTPUT"):
            with self.subTest(mode=key):
                self.log_path.unlink(missing_ok=True)
                self.state_path.unlink(missing_ok=True)
                result = self.run_runner(
                    plan(step("broken-result"), step("must-not-run")),
                    "--retries",
                    "1",
                    env_updates=self.fake_env(**{key: "1"}),
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(len(self.calls()), 2)
                report = json.loads(result.stdout)
                self.assertIn(report.get("status"), {"failed", "stopped"})

    def test_blocked_or_failed_child_status_retries_then_fails(self) -> None:
        for status in ("blocked", "failed"):
            with self.subTest(status=status):
                self.log_path.unlink(missing_ok=True)
                self.state_path.unlink(missing_ok=True)
                result = self.run_runner(
                    plan(step("reported-failure"), step("must-not-run")),
                    "--retries",
                    "1",
                    env_updates=self.fake_env(FAKE_CODEX_STATUS=status),
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(len(self.calls()), 2)
                report = json.loads(result.stdout)
                self.assertIn(report.get("status"), {"failed", "stopped"})


if __name__ == "__main__":
    unittest.main()
