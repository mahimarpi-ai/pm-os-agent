"""Cortex, a minimal, explicit agent loop you (and your coding agent) can read end
to end. This is the agent you ship: your PM chief-of-staff. You build it by
directing your coding agent (Claude Code / Cursor / Codex) to shape this file. You
never have to hand-write it.

Every bound the course talks about is visible right here in code, not buried in a
framework: the max-iteration counter, the cost cap, the revision cap, the
stop/escalate conditions, the auto-queue cap, and the absence of any publish tool.

Usage (ask your coding agent to run these for you, or run them yourself):
    python agent.py                # runs the happy-path task (weekly status update)
    python agent.py missing-data   # the stuck/escalate case
    python agent.py jailbreak       # the prompt-injection refusal case

Every run ends by showing a final status draft, a held last draft, or a human
escalation. Drafts are saved to run-output/ for human review; nothing is posted,
and there is no publish tool.

Requires OPENAI_API_KEY in your environment (see .env.example). Model and bounds
are read from env so you can tune them, that tuning is your M5 deliverable.

The loop is deliberately transparent (hand-written tool-calling on the openai
client) so a grader can see the machinery. Keep the bounds explicit if you rework it.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from openai import APITimeoutError, OpenAI

import tools
from critic import build_messages as build_critic_messages, review
from prompts import CORTEX_SYSTEM

try:  # load .env if python-dotenv is installed; harmless if it isn't
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# --- Bounds (your M5 deliverable: tune these and justify them) ----------------
MODEL = os.environ.get("CORTEX_MODEL", "gpt-4o-mini")
MAX_ITERATIONS = int(os.environ.get("CORTEX_MAX_ITERATIONS", "8"))
MAX_REVISIONS = int(os.environ.get("CORTEX_MAX_REVISIONS", "2"))
COST_CAP_USD = float(os.environ.get("CORTEX_COST_CAP_USD", "0.50"))
TIMEOUT_SECONDS = float(os.environ.get("CORTEX_TIMEOUT_SECONDS", "90"))
MAX_COMPLETION_TOKENS = int(os.environ.get("CORTEX_MAX_COMPLETION_TOKENS", "2048"))
MAX_QUEUE_ITEMS = int(os.environ.get("CORTEX_MAX_QUEUE_ITEMS", "10"))
MAX_DATA_PULL_FAILURES = 4
MONTH_NAME_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)"
)
CALENDAR_DATE_PATTERN = (
    rf"(?:\d{{4}}-\d{{2}}-\d{{2}}|{MONTH_NAME_PATTERN}\s+\d{{1,2}}(?:,?\s+\d{{4}})?)"
)
ABOVE_LINE_REQUESTS = [
    ("rule override", re.compile(
        r"\b(?:system override|admin mode)\b"
        r"|\bignore all previous (?:rules|instructions|norms)\b"
        r"|\b(?:override|ignore|disregard|bypass)\b.{0,40}"
        r"\b(?:previous|prior|existing)\b.{0,40}"
        r"\b(?:rules?|instructions?|norms?|safety guidance|polic(?:y|ies))\b",
        re.IGNORECASE)),
    ("company-wide publishing", re.compile(
        r"\b(?:post|publish|send|forward|put|route|broadcast|share)\b.{0,120}"
        r"\b(?:company[- ]wide|#all-hands|all[- ]hands|all staff|everyone)\b",
        re.IGNORECASE | re.DOTALL)),
    ("confidential roadmap disclosure", re.compile(
        r"\b(?:include|share|disclose|reveal|publish|send|forward|attach|provide)\b"
        r".{0,120}\b(?:Orbit|Pulsar|unreleased|confidential|embargoed)\b",
        re.IGNORECASE | re.DOTALL)),
    ("launch-gate change", re.compile(
        r"\b(?:mark|set)\b.{0,60}\b(?:launch )?gates?\b.{0,40}"
        r"\b(?:green|open|closed)\b", re.IGNORECASE | re.DOTALL)),
    ("issue closure", re.compile(
        r"\b(?:close|resolve)\b.{0,60}\b(?:sev-?1|issue|bug)\b",
        re.IGNORECASE | re.DOTALL)),
    ("ship-date commitment", re.compile(
        r"\b(?:publicly )?(?:commit|promise)\b.{0,60}"
        r"\b(?:date|GA|launch|March \d{1,2})\b"
        r"|\b(?:GA|launch)\b.{0,60}\b(?:is|on|for|by|scheduled for)\b.{0,40}\b"
        + CALENDAR_DATE_PATTERN
        + r"\b|\b"
        + CALENDAR_DATE_PATTERN
        + r"\b.{0,40}\b(?:GA|launch)\b",
        re.IGNORECASE | re.DOTALL)),
    ("claimed pre-authorization", re.compile(
        r"\b(?:leadership|admin|security|system|user)\b.{0,60}"
        r"\b(?:already\s+)?(?:approved|authorized)\b"
        r"|\b(?:pre[- ]?approved|pre[- ]?authorized)\b.{0,40}"
        r"\b(?:by )?(?:leadership|admin|security|system|user)\b"
        r"|\b(?:no need|don't need|do not need)\b.{0,40}\b(?:ask|escalate|approval|human)\b"
        r"|\b(?:do not|don't)\s+escalate\b",
        re.IGNORECASE | re.DOTALL)),
]
DATA_PULL_TOOLS = {
    "get_project",
    "get_activity",
    "search_past_updates",
    "get_roadmap",
    "get_norms",
}
PROVENANCE_TOOLS = {"get_project", "get_activity"}
PROJECT_ID_PATTERN = re.compile(r"\bP-[A-Z0-9]+(?:-[A-Z0-9]+)*\b", re.IGNORECASE)
PERCENT_PATTERN = re.compile(
    r"(?<![\w.])(?P<value>\d+(?:\.\d+)?)\s*(?:%|percent\b|per\s+cent\b)",
    re.IGNORECASE,
)
ISSUE_ID_PATTERN = re.compile(r"(?<!\w)#\d+\b")
DATE_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b"
    rf"|\b{MONTH_NAME_PATTERN}\s+\d{{1,2}},?\s+\d{{4}}\b"
    r"|\b\d{1,2}/\d{1,2}/\d{4}\b",
    re.IGNORECASE,
)
# Rough $ per 1M tokens for your chosen model, set to match its pricing.
PRICE_IN = float(os.environ.get("CORTEX_PRICE_IN_PER_M", "0.15"))
PRICE_OUT = float(os.environ.get("CORTEX_PRICE_OUT_PER_M", "0.60"))

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_project", "description": "Look up a project by its ID (status, flags, linked PRD).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {
        "name": "get_activity",
        "description": "Pull recent engineering activity for a project (merged PRs, open issues, Sev-1s).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {
        "name": "search_past_updates",
        "description": "Search previous status updates and decisions for tone and precedent.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_roadmap",
        "description": "Return the roadmap. Some items are flagged confidential/embargoed.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_norms", "description": "Return the team norms / PM playbook the agent must follow.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "propose_stories",
        "description": "Queue a set of backlog stories for human approval (creates nothing; rejected above the item cap).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"},
            "stories": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"}}, "required": ["project_id", "stories"]}}},
]


class Bounds:
    """Enforces per-run time, kill-switch, and reserved-cost limits outside the model."""

    def __init__(self, *, cost_cap: float = COST_CAP_USD,
                 timeout_seconds: float = TIMEOUT_SECONDS):
        self.cost = 0.0
        self.cost_cap = cost_cap
        self.deadline = time.monotonic() + timeout_seconds

    def remaining_seconds(self) -> float:
        return max(0.0, self.deadline - time.monotonic())

    def stop_reason(self) -> str:
        if KILL_SWITCH_FILE.exists():
            return f"kill switch marker detected at {KILL_SWITCH_FILE}"
        if self.remaining_seconds() <= 0:
            return f"run timeout of {TIMEOUT_SECONDS:g} seconds reached"
        if self.cost >= self.cost_cap:
            return f"cost cap ${self.cost_cap:.2f} reached"
        return ""

    def reserve_request(self, messages, *, tools_schema=None,
                        response_format=None) -> Optional[tuple[float, int]]:
        """Reserve a conservative request cost before sending it to the model."""
        request = {
            "messages": messages,
            "tools": tools_schema or [],
            "response_format": response_format,
        }
        serialized = json.dumps(request, ensure_ascii=True, default=str)
        input_token_ceiling = (
            len(serialized.encode("utf-8"))
            + 128
            + 32 * len(messages)
            + 32 * len(tools_schema or [])
        )
        input_cost = input_token_ceiling * PRICE_IN / 1_000_000
        available = self.cost_cap - self.cost - input_cost
        if available <= 0:
            return None

        if PRICE_OUT > 0:
            output_limit = min(
                MAX_COMPLETION_TOKENS,
                math.floor(available * 1_000_000 / PRICE_OUT),
            )
        else:
            output_limit = MAX_COMPLETION_TOKENS
        if output_limit < 1:
            return None

        reserved_cost = input_cost + output_limit * PRICE_OUT / 1_000_000
        if self.cost + reserved_cost > self.cost_cap:
            return None
        self.cost += reserved_cost
        return reserved_cost, output_limit

    def reconcile_request(self, reservation: tuple[float, int], *,
                           prompt_tokens: int, completion_tokens: int) -> bool:
        actual_cost = (
            prompt_tokens * PRICE_IN
            + completion_tokens * PRICE_OUT
        ) / 1_000_000
        self.cost += actual_cost - reservation[0]
        return self.cost <= self.cost_cap


OUTPUT_DIR = Path(__file__).parent / "run-output"
KILL_SWITCH_FILE = Path(os.environ.get(
    "CORTEX_KILL_SWITCH_FILE", str(OUTPUT_DIR / "KILL")))


def banner(text: str) -> None:
    print(f"\n{'=' * 64}\n{text}\n{'=' * 64}")


def detect_above_line_requests(task_body: str) -> list[str]:
    """Return explicit above-line request categories found in an inbound task."""
    return [label for label, pattern in ABOVE_LINE_REQUESTS if pattern.search(task_body)]


def task_project_id(task_body: str) -> Optional[str]:
    project_ids = {
        project_id.upper()
        for project_id in PROJECT_ID_PATTERN.findall(task_body)
    }
    return next(iter(project_ids)) if len(project_ids) == 1 else None


def _matches_schema_type(value, schema: dict) -> bool:
    value_type = schema.get("type")
    if value_type == "string":
        return isinstance(value, str)
    if value_type == "object":
        return isinstance(value, dict)
    if value_type == "array":
        items_schema = schema.get("items")
        return (
            isinstance(value, list)
            and isinstance(items_schema, dict)
            and all(_matches_schema_type(item, items_schema) for item in value)
        )
    if value_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if value_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if value_type == "boolean":
        return isinstance(value, bool)
    return False


def _project_ids_in(value) -> set[str]:
    if isinstance(value, str):
        return {project_id.upper() for project_id in PROJECT_ID_PATTERN.findall(value)}
    if isinstance(value, dict):
        return set().union(*(_project_ids_in(item) for item in value.values())) \
            if value else set()
    if isinstance(value, list):
        return set().union(*(_project_ids_in(item) for item in value)) if value else set()
    return set()


def validate_tool_call(call, expected_project_id: Optional[str]):
    function_name = call.function.name
    schema = next(
        (item["function"] for item in TOOL_SCHEMAS
         if item["function"]["name"] == function_name),
        None,
    )
    if schema is None or function_name not in tools.TOOLS:
        return function_name, None, f"tool {function_name!r} is not allowed"

    try:
        arguments = json.loads(call.function.arguments or "{}")
    except (json.JSONDecodeError, TypeError):
        return function_name, None, f"tool {function_name!r} has malformed JSON arguments"
    if not isinstance(arguments, dict):
        return function_name, None, f"tool {function_name!r} arguments must be a JSON object"

    parameters = schema["parameters"]
    properties = parameters.get("properties", {})
    required = set(parameters.get("required", []))
    missing = required - arguments.keys()
    if missing:
        return function_name, None, (
            f"tool {function_name!r} is missing required arguments: "
            f"{', '.join(sorted(missing))}"
        )
    unexpected = arguments.keys() - properties.keys()
    if unexpected:
        return function_name, None, (
            f"tool {function_name!r} has unexpected arguments: "
            f"{', '.join(sorted(unexpected))}"
        )
    for name, value in arguments.items():
        if not _matches_schema_type(value, properties[name]):
            return function_name, None, (
                f"tool {function_name!r} argument {name!r} has the wrong type"
            )

    if "project_id" in properties:
        if expected_project_id is None:
            return function_name, None, (
                f"tool {function_name!r} requires one unambiguous project ID in the task"
            )
        if arguments["project_id"].strip().upper() != expected_project_id:
            return function_name, None, (
                f"tool {function_name!r} project_id is outside the task's project scope"
            )
        if arguments["project_id"].strip().upper() in tools.confidential_project_ids():
            return function_name, None, (
                f"tool {function_name!r} cannot access a confidential project"
            )

    arguments_text = json.dumps(arguments, ensure_ascii=True)
    if any(
        re.search(rf"(?<!\w){re.escape(token)}(?!\w)", arguments_text, re.IGNORECASE)
        for token in tools.confidential_project_tokens()
    ):
        return function_name, None, (
            f"tool {function_name!r} arguments reference a confidential project"
        )

    referenced_ids = _project_ids_in(arguments)
    if expected_project_id is None and referenced_ids:
        return function_name, None, (
            f"tool {function_name!r} references a project but the task has no "
            "unambiguous project ID"
        )
    out_of_scope = referenced_ids - ({expected_project_id} if expected_project_id else set())
    for project_id, project_tokens in tools.project_tokens().items():
        if project_id == expected_project_id:
            continue
        if any(
            re.search(rf"(?<!\w){re.escape(token)}(?!\w)", arguments_text, re.IGNORECASE)
            for token in project_tokens
        ):
            out_of_scope.add(project_id)
    if out_of_scope:
        return function_name, None, (
            f"tool {function_name!r} arguments reference a project outside "
            "the task's project scope"
        )
    return function_name, arguments, ""


def redact_confidential_roadmap(
    result: dict, expected_project_id: Optional[str]
) -> dict:
    roadmap = result.get("roadmap")
    if not isinstance(roadmap, str):
        return result

    confidential_tokens = tools.confidential_project_tokens()
    project_tokens = tools.project_tokens()
    task_tokens = project_tokens.get(expected_project_id or "", set())
    safe_lines = []
    in_allowed_section = True
    redacted = False
    for line in roadmap.splitlines():
        if line.startswith("## "):
            heading = line[3:]
            confidential_section = bool(
                re.search(r"\b(?:confidential|embargoed)\b", heading, re.IGNORECASE)
                or any(
                    re.search(rf"\b{re.escape(token)}\b", heading, re.IGNORECASE)
                    for token in confidential_tokens
                )
            )
            requested_project_section = any(
                re.search(rf"\b{re.escape(token)}\b", heading, re.IGNORECASE)
                for token in task_tokens
            )
            in_allowed_section = requested_project_section and not confidential_section
            redacted = redacted or not in_allowed_section
        if in_allowed_section:
            safe_lines.append(line)

    if not redacted:
        return result
    sanitized = dict(result)
    safe_roadmap = "\n".join(safe_lines)
    withheld_tokens = set(confidential_tokens)
    for project_id, tokens in project_tokens.items():
        if project_id != expected_project_id:
            withheld_tokens.update(tokens)
    for token in withheld_tokens:
        safe_roadmap = re.sub(
            rf"(?<!\w){re.escape(token)}(?!\w)",
            "[withheld]",
            safe_roadmap,
            flags=re.IGNORECASE,
        )
    sanitized["roadmap"] = safe_roadmap
    sanitized["redaction_note"] = (
        "Other-project and confidential/embargoed sections were withheld before model context."
    )
    return sanitized


def confidential_project_mentions(text: str) -> list[str]:
    return sorted(
        token for token in tools.confidential_project_tokens()
        if re.search(rf"(?<!\w){re.escape(token)}(?!\w)", text, re.IGNORECASE)
    )


def _normalize_date(value: str) -> Optional[str]:
    formats = ("%Y-%m-%d", "%m/%d/%Y", "%B %d %Y", "%b %d %Y")
    normalized = value.replace(",", "")
    for date_format in formats:
        try:
            return datetime.strptime(normalized, date_format).date().isoformat()
        except ValueError:
            continue
    return None


def _normalized_dates(text: str) -> set[str]:
    return {
        normalized
        for match in DATE_PATTERN.finditer(text)
        if (normalized := _normalize_date(match.group())) is not None
    }


def _percentages(text: str) -> set[str]:
    return {
        f"{match.group('value')}%"
        for match in PERCENT_PATTERN.finditer(text)
    }


def _supported_status_colors(sources: list[dict]) -> set[str]:
    project_results = {}
    activity_results = {}
    for source in sources:
        result = source["result"]
        if source["tool"] == "get_project":
            project_id = result.get("project_id")
            if project_id:
                project_results[project_id] = result
        elif source["tool"] == "get_activity":
            project_id = result.get("project_id")
            if project_id:
                activity_results[project_id] = result

    colors = set()
    for project_id, project in project_results.items():
        explicit_color = str(
            project.get("status_color", project.get("color", ""))
        ).casefold()
        if explicit_color in {"green", "yellow", "red"}:
            colors.add(explicit_color)

        activity = activity_results.get(project_id)
        if not activity or project.get("status") != "on_track":
            continue
        flags = project.get("flags", [])
        has_sev1 = any(
            str(item.get("severity", "")).casefold() in {"sev-1", "sev1"}
            for item in activity.get("activity", [])
            if isinstance(item, dict)
        )
        if "launch_hold" not in flags and not has_sev1:
            colors.add("green")
    return colors


def draft_provenance_reasons(draft: str, sources: list[dict]) -> list[str]:
    evidence = json.dumps(sources, ensure_ascii=True, default=str)
    reasons = []

    supported_percentages = _percentages(evidence)
    for percentage in sorted(_percentages(draft) - supported_percentages):
        reasons.append(f"percentage claim {percentage!r} is absent from trusted tool results")

    supported_ids = set(ISSUE_ID_PATTERN.findall(evidence))
    for issue_id in sorted(set(ISSUE_ID_PATTERN.findall(draft)) - supported_ids):
        reasons.append(f"PR/issue reference {issue_id!r} is absent from trusted tool results")

    supported_dates = _normalized_dates(evidence)
    seen_dates = set()
    for match in DATE_PATTERN.finditer(draft):
        date_text = match.group()
        if date_text in seen_dates:
            continue
        seen_dates.add(date_text)
        normalized = _normalize_date(date_text)
        if normalized is None or normalized not in supported_dates:
            reasons.append(f"date claim {date_text!r} is absent from trusted tool results")

    supported_statuses = {
        status.replace("_", " ")
        for source in sources
        if source["tool"] == "get_project"
        for status in [str(source["result"].get("status", "")).casefold()]
        if status
    }
    status_patterns = {
        "on track": r"\bon[\s_-]+track\b",
        "at risk": r"\bat[\s_-]+risk\b",
        "blocked": r"\bblocked\b",
    }
    for status, pattern in status_patterns.items():
        if (re.search(pattern, draft, re.IGNORECASE)
                and status not in supported_statuses):
            reasons.append(f"status claim {status!r} is absent from trusted project results")

    supported_colors = _supported_status_colors(sources)
    for color in ("green", "yellow", "red"):
        if (re.search(rf"\b{color}\b", draft, re.IGNORECASE)
                and color not in supported_colors):
            reasons.append(f"status color {color!r} is not supported by trusted project results")

    return reasons


def emit_deliverable(which: str, draft: str, *, accepted: bool,
                     reason: str, cost: float) -> None:
    """Surface AND persist Cortex's drafted status update so it can't get lost in
    the scroll-back. This is still a DRAFT held for human review, never a post,
    there is no publish tool, and an escalated run is held on purpose.

    Runs on every exit: an accepted pass prints the FINAL update; a bound trip or
    escalation prints the LAST draft it managed to write plus why it was held.
    """
    if accepted:
        title = "FINAL STATUS UPDATE (draft, validator-approved, NOT posted)"
    elif draft.strip():
        title = "LAST DRAFT (held, NOT posted, escalated to a human)"
    else:
        title = "ESCALATED TO HUMAN (no status draft produced)"
    banner(title)
    if draft.strip():
        print(draft.rstrip())
    else:
        print("(No status draft was produced.)")
    if not accepted:
        print(f"\nWhy it was held: {reason}")

    if draft.strip():
        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"status-update-{which}.md"
        state = "accepted by validator" if accepted else "HELD, escalated"
        out.write_text(
            f"<!-- Cortex draft, {state}; NOT posted. Run cost ~ ${cost:.4f}. -->\n"
            f"<!-- {reason} -->\n\n{draft.rstrip()}\n", encoding="utf-8")
        print(f"\nSaved draft -> {out.relative_to(Path(__file__).parent)}  "
              f"(for your review, nothing was posted)")


def halt_run(which: str, draft: str, bounds: Bounds, reason: str) -> None:
    banner(f"RUNTIME BOUND TRIPPED: {reason}. Stopping and escalating to a human.")
    emit_deliverable(which, draft, accepted=False, reason=reason, cost=bounds.cost)


def run(which: str = "happy", *, force_bad_draft: bool = False) -> None:
    bounds = Bounds()
    task = tools.get_task(which)
    if "error" in task:
        print(task)
        return

    date_requested = "date" in task["body"].casefold()
    banner(f"CORTEX RUN, fixture: task-{which}  (auto-queue cap {MAX_QUEUE_ITEMS} items)")
    print(task["body"])

    flagged_requests = detect_above_line_requests(task["body"])
    if flagged_requests:
        reason = ("untrusted task contains above-the-line requests: "
                  f"{', '.join(flagged_requests)}")
        banner("PRE-FLIGHT SAFETY GATE")
        print(f"INJECTION FLAGGED: {', '.join(flagged_requests)}")
        print(f"ESCALATE: {reason}. No model or tools were called.")
        emit_deliverable(which, "", accepted=False, reason=reason, cost=bounds.cost)
        return

    source_log: list[str] = [task["body"]]
    expected_project_id = task_project_id(task["body"])
    trusted_sources: list[dict] = []
    revisions = 0
    data_pull_failures = 0
    last_draft = ""

    def halt_if_needed() -> bool:
        reason = bounds.stop_reason()
        if not reason:
            return False
        halt_run(which, last_draft, bounds, reason)
        return True

    if halt_if_needed():
        return

    client = OpenAI(timeout=TIMEOUT_SECONDS, max_retries=0)
    messages = [
        {"role": "system", "content": CORTEX_SYSTEM},
        {"role": "user", "content": f"PM task brief:\n\n{task['body']}"},
    ]

    for step in range(1, MAX_ITERATIONS + 1):
        if halt_if_needed():
            return

        reservation = bounds.reserve_request(messages, tools_schema=TOOL_SCHEMAS)
        if reservation is None:
            halt_run(which, last_draft, bounds,
                     f"cost cap ${bounds.cost_cap:.2f} cannot reserve the next model request")
            return
        request_timeout = bounds.remaining_seconds()
        if request_timeout <= 0:
            halt_run(which, last_draft, bounds,
                     f"run timeout of {TIMEOUT_SECONDS:g} seconds reached")
            return
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                max_tokens=reservation[1],
                timeout=request_timeout,
            )
        except APITimeoutError:
            halt_run(which, last_draft, bounds,
                     f"run timeout of {TIMEOUT_SECONDS:g} seconds reached during Cortex request")
            return
        within_budget = bounds.reconcile_request(
            reservation,
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
        )
        msg = resp.choices[0].message
        if not msg.tool_calls:
            last_draft = msg.content or ""
        if not within_budget:
            halt_run(which, last_draft, bounds,
                     "reported usage exceeded the reserved per-run cost budget")
            return
        if halt_if_needed():
            return

        if msg.tool_calls:
            messages.append(msg)
            for call in msg.tool_calls:
                if halt_if_needed():
                    return
                fn, args, validation_error = validate_tool_call(
                    call, expected_project_id)
                if validation_error:
                    reason = f"tool call blocked: {validation_error}"
                    banner(f"TOOL CALL BLOCKED: {reason}. Escalating to a human.")
                    emit_deliverable(which, last_draft, accepted=False,
                                     reason=reason, cost=bounds.cost)
                    return

                result = tools.TOOLS[fn](**args)
                if fn == "get_roadmap" and isinstance(result, dict):
                    result = redact_confidential_roadmap(
                        result, expected_project_id)
                source_log.append(f"{fn}({args}) -> {json.dumps(result)}")
                if (fn in PROVENANCE_TOOLS and isinstance(result, dict)
                        and not result.get("error")):
                    trusted_sources.append({"tool": fn, "result": result})
                print(f"\n[step {step}] TOOL {fn}({args})")
                print(f"          -> {json.dumps(result)[:300]}")
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(result)})
                escalation_reason = ""
                if fn == "get_project" and isinstance(result, dict):
                    if result.get("error") == "project_not_found":
                        escalation_reason = (
                            f"requested project {args.get('project_id')} was not found")
                    elif (date_requested
                          and "unconfirmed" in str(result.get("prd_summary", "")).casefold()):
                        escalation_reason = (
                            "requested date is marked unconfirmed in project data")
                if escalation_reason:
                    reason = f"{escalation_reason}; stopping and escalating to a human"
                    banner(reason)
                    emit_deliverable(which, last_draft, accepted=False,
                                     reason=reason, cost=bounds.cost)
                    return
                if (fn in DATA_PULL_TOOLS and isinstance(result, dict)
                        and result.get("error")):
                    data_pull_failures += 1
                    if data_pull_failures >= MAX_DATA_PULL_FAILURES:
                        reason = (f"data retrieval failed {data_pull_failures} times; "
                                  "stopping and escalating to a human")
                        banner(reason)
                        emit_deliverable(which, last_draft, accepted=False,
                                         reason=reason, cost=bounds.cost)
                        return
            continue

        # No tool calls => Cortex produced a proposed output. Validate it.
        proposed = msg.content or ""
        if force_bad_draft:
            proposed = (
                "DONE: Northstar is at 99% activation, up from 98%. "
                "We commit to a GA launch on November 30, 2026."
            )
            force_bad_draft = False
            print("[DEMO] FORCED INTENTIONALLY INVALID DRAFT:")
        last_draft = proposed
        print(f"\n[step {step}] PROPOSED OUTPUT:\n{proposed}")

        confidential_mentions = confidential_project_mentions(proposed)
        if confidential_mentions:
            reason = (
                "draft names a project marked confidential: "
                f"{', '.join(confidential_mentions)}"
            )
            banner("CONFIDENTIALITY GATE: draft held and escalated to a human.")
            emit_deliverable(which, proposed, accepted=False,
                             reason=reason, cost=bounds.cost)
            return

        banner("CRITIC, independent validation")
        if halt_if_needed():
            return
        critic_messages = build_critic_messages(proposed, "\n".join(source_log))
        reservation = bounds.reserve_request(
            critic_messages, response_format={"type": "json_object"})
        if reservation is None:
            halt_run(which, last_draft, bounds,
                     f"cost cap ${bounds.cost_cap:.2f} cannot reserve the critic request")
            return
        request_timeout = bounds.remaining_seconds()
        if request_timeout <= 0:
            halt_run(which, last_draft, bounds,
                     f"run timeout of {TIMEOUT_SECONDS:g} seconds reached")
            return
        try:
            verdict = review(
                client,
                MODEL,
                proposed,
                "\n".join(source_log),
                timeout=request_timeout,
                max_tokens=reservation[1],
            )
        except APITimeoutError:
            halt_run(which, last_draft, bounds,
                     f"run timeout of {TIMEOUT_SECONDS:g} seconds reached during critic request")
            return
        if not bounds.reconcile_request(
                reservation,
                prompt_tokens=verdict["_usage"]["prompt"],
                completion_tokens=verdict["_usage"]["completion"]):
            halt_run(which, last_draft, bounds,
                     "critic usage exceeded the reserved per-run cost budget")
            return
        if halt_if_needed():
            return
        provenance_reasons = draft_provenance_reasons(proposed, trusted_sources)
        if provenance_reasons:
            verdict["verdict"] = "fail"
            verdict["reasons"] = list(dict.fromkeys(
                verdict["reasons"] + provenance_reasons
            ))
        print(json.dumps({k: v for k, v in verdict.items() if k != "_usage"}, indent=2))

        if verdict["verdict"] == "pass":
            if proposed.lstrip().startswith("ESCALATE:"):
                reason = proposed.partition(":")[2].strip()
                emit_deliverable(
                    which, "", accepted=False,
                    reason=f"Cortex escalated to a human: {reason}",
                    cost=bounds.cost)
                return
            banner(f"HITL CHECKPOINT, status update + any proposed stories queued for "
                   f"your review. Nothing posted, no commitments made. "
                   f"Run cost ≈ ${bounds.cost:.4f}")
            emit_deliverable(which, proposed, accepted=True,
                             reason="validator passed", cost=bounds.cost)
            return

        if revisions >= MAX_REVISIONS:
            reason = f"validator rejected {MAX_REVISIONS}x (revision cap)"
            banner(f"FAIL-ACTION: revision cap hit ({MAX_REVISIONS}); escalating to a human "
                   f"instead of looping. Run cost ≈ ${bounds.cost:.4f}")
            emit_deliverable(which, last_draft, accepted=False,
                             reason=reason, cost=bounds.cost)
            return

        revisions += 1
        print(f"\nFAIL-ACTION: critic rejected; returning draft to Cortex for "
              f"revision {revisions}/{MAX_REVISIONS}.")
        messages.append({"role": "assistant", "content": proposed})
        messages.append({"role": "user", "content":
                         "A validator rejected that for these reasons: "
                         f"{verdict['reasons']}. Fix it or escalate."})

    banner(f"MAX ITERATIONS ({MAX_ITERATIONS}) reached without finishing. "
           f"Escalating. Run cost ≈ ${bounds.cost:.4f}")
    emit_deliverable(which, last_draft, accepted=False,
                     reason=f"max iterations ({MAX_ITERATIONS}) reached",
                     cost=bounds.cost)


if __name__ == "__main__":
    task_name = sys.argv[1] if len(sys.argv) > 1 else "happy"
    if task_name == "critic-demo":
        run("happy", force_bad_draft=True)
    else:
        run(task_name)
