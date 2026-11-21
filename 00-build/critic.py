"""Independent validator (M3). A separate model call that never saw the drafting
context, so it can't inherit the draft's blind spots. Returns a pass/fail verdict.
The revision cap that stops a critic<->drafter loop lives in `agent.py`.
"""

from __future__ import annotations

import json
from typing import Optional

from prompts import CRITIC_SYSTEM


def build_messages(proposed_output: str, source_data: str) -> list[dict]:
    return [
        {"role": "system", "content": CRITIC_SYSTEM},
        {"role": "user", "content":
            f"SOURCE DATA Cortex used:\n{source_data}\n\n"
            f"CORTEX PROPOSED OUTPUT:\n{proposed_output}"},
    ]


def review(client, model: str, proposed_output: str, source_data: str, *,
           timeout: Optional[float] = None, max_tokens: int = 2048) -> dict:
    """Return {"verdict": "pass"|"fail", "reasons": [...]} for a proposed output."""
    resp = client.chat.completions.create(
        model=model,
        messages=build_messages(proposed_output, source_data),
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
        timeout=timeout,
    )
    usage = resp.usage
    try:
        parsed = json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        parsed = None

    if (not isinstance(parsed, dict)
            or set(parsed) != {"verdict", "reasons"}
            or not isinstance(parsed.get("verdict"), str)
            or parsed["verdict"] not in {"pass", "fail"}
            or not isinstance(parsed.get("reasons"), list)
            or not all(isinstance(reason, str) for reason in parsed["reasons"])
            or (parsed["verdict"] == "fail"
                and not any(reason.strip() for reason in parsed["reasons"]))):
        verdict = {
            "verdict": "fail",
            "reasons": ["critic returned an invalid verdict; rejecting output"],
        }
    else:
        verdict = {"verdict": parsed["verdict"], "reasons": parsed["reasons"]}
    verdict["_usage"] = {"prompt": usage.prompt_tokens, "completion": usage.completion_tokens}
    return verdict
