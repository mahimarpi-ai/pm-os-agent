from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import agent


class RuntimeBoundsTests(unittest.TestCase):
    def test_deadline_expires(self):
        with patch("agent.time.monotonic", side_effect=[100.0, 191.0]):
            bounds = agent.Bounds(timeout_seconds=90)
            self.assertIn("run timeout", bounds.stop_reason())

    def test_kill_switch_marker_stops_run_before_client_creation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            marker = Path(temp_dir) / "KILL"
            marker.touch()
            with ExitStack() as stack:
                stack.enter_context(patch.object(agent, "KILL_SWITCH_FILE", marker))
                stack.enter_context(patch.object(
                    agent, "OUTPUT_DIR", Path(temp_dir) / "output"))
                stack.enter_context(patch.object(
                    agent, "OpenAI", side_effect=AssertionError("client created")))
                stack.enter_context(patch.object(
                    agent.tools, "get_task", return_value={"body": "Review Northstar."}))
                output = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                agent.run("happy")

        self.assertIn("kill switch marker detected", output.getvalue())

    def test_cost_reservation_caps_output_and_rejects_unaffordable_request(self):
        bounds = agent.Bounds(cost_cap=0.001, timeout_seconds=90)
        request = bounds.reserve_request(
            [{"role": "user", "content": "short prompt"}],
            tools_schema=[],
        )

        if request is None:
            self.fail("the request should fit under the cost cap")
        self.assertLessEqual(request[1], 2048)
        self.assertLessEqual(bounds.cost, bounds.cost_cap)
        bounds.cost = bounds.cost_cap
        self.assertIsNone(bounds.reserve_request(
            [{"role": "user", "content": "short prompt"}]))

    def test_usage_reconciliation_releases_unused_reservation(self):
        bounds = agent.Bounds(cost_cap=0.50, timeout_seconds=90)
        reservation = bounds.reserve_request(
            [{"role": "user", "content": "short prompt"}],
        )
        if reservation is None:
            self.fail("the request should fit under the cost cap")
        reserved_cost = bounds.cost

        within_budget = bounds.reconcile_request(
            reservation, prompt_tokens=1, completion_tokens=1)

        self.assertTrue(within_budget)
        self.assertLess(bounds.cost, reserved_cost)

    def test_usage_over_reservation_trips_cost_cap(self):
        bounds = agent.Bounds(cost_cap=0.001, timeout_seconds=90)
        reservation = bounds.reserve_request(
            [{"role": "user", "content": "short prompt"}],
        )
        if reservation is None:
            self.fail("the request should fit under the cost cap")

        within_budget = bounds.reconcile_request(
            reservation, prompt_tokens=10000, completion_tokens=2048)

        self.assertFalse(within_budget)
        self.assertGreater(bounds.cost, bounds.cost_cap)

    def test_model_and_critic_requests_receive_limits(self):
        class FakeCompletions:
            def __init__(self):
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                content = (
                    json.dumps({"verdict": "pass", "reasons": []})
                    if "response_format" in kwargs
                    else "ESCALATE: scripted test"
                )
                return SimpleNamespace(
                    usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
                    choices=[SimpleNamespace(message=SimpleNamespace(
                        content=content, tool_calls=None))],
                )

        completions = FakeCompletions()
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=completions))
        with tempfile.TemporaryDirectory() as temp_dir:
            with ExitStack() as stack:
                openai_client = stack.enter_context(
                    patch.object(agent, "OpenAI", return_value=client))
                stack.enter_context(patch.object(agent.tools, "get_task", return_value={
                    "body": "Review the Northstar project."
                }))
                stack.enter_context(patch.object(agent, "OUTPUT_DIR", Path(temp_dir)))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                agent.run("happy")

        openai_client.assert_called_once_with(
            timeout=agent.TIMEOUT_SECONDS, max_retries=0)
        self.assertEqual(len(completions.calls), 2)
        for request in completions.calls:
            self.assertGreater(request["timeout"], 0)
            self.assertLessEqual(request["timeout"], agent.TIMEOUT_SECONDS)
            self.assertGreater(request["max_tokens"], 0)
            self.assertLessEqual(request["max_tokens"], agent.MAX_COMPLETION_TOKENS)


if __name__ == "__main__":
    unittest.main()
