# Orchestration Map

## 1. Why split / why not

Cortex should be split into a short team because the strongest reason is the independent validator. The drafter is responsible for reading the task, pulling project context, and writing the leadership update and backlog story proposal. That same agent is also the one most likely to overstate progress or invent a number, a date, or a risk. A second agent with a separate prompt and a separate call is the cleanest way to check whether the output is grounded in the actual project activity and source data before it reaches the PM.

This is not a large fleet. There is no need for parallelism or a large specialist team for the current lab. The real split is a single critic that exists to catch the draft's blind spots.

## 2. Topology

```text
[Inbound PM task]
    ↓
[Cortex: reads task + pulls project data + drafts update + stories]
    ↓
[Validator / Critic]
    ├─ fail → back to Cortex (revise, up to cap)
    ├─ fail after cap → escalate to human
    └─ pass → [PM review checkpoint] → queued for approval
```

## 3. Roster

| Agent | Responsibility | Runs from |
|---|---|---|
| Cortex | Reads the request, pulls context, drafts update, proposes backlog stories | Loop Spec / M2 |
| Critic | Validates the draft for traceability, invented claims, and policy compliance | Module 3 validator |
| PM | Reviews approved draft and decides whether to accept or adjust | Human decision point |

## 4. Hand-offs

The drafter hands off three things to the critic:
- the proposed draft
- the source log / evidence used to support it
- the task context and any tool outputs that were pulled

This is a plain in-process hand-off, not a formal MCP/A2A integration. The point is that the validator sees the finished output and the tools/data it relied on, but not the same drafting context or hidden assumptions that may have caused the draft to drift.

## 5. The validator

The critic is responsible for checking whether the draft is traceable and honest. It should reject any status update that:
- cites a project, a metric, or a date that the data does not support
- invents progress, risk, or delivery status without evidence
- makes commitments or promises outside the agent line
- adds unconfirmed dates or firm launch commitments
- claims an item is safe or green when the source data does not support it

Fail-action: revise and return the draft to Cortex, up to a hard revision cap.
Revision cap: 3 revisions, then escalate to the human instead of looping forever.
Pass-action: if the critic passes, the draft advances to the PM review checkpoint. It does not auto-send or auto-post anything.

## 6. Shared vs isolated state

Shared state:
- PM task brief
- project data pulled by Cortex
- recent activity / issue list / PRs / norms / roadmap
- draft text itself

Isolated state:
- the critic's reasoning and fail notes should remain separate from the drafter's loop
- the critic cannot inherit the drafter's same prompt assumptions or hidden context
- the validator must not be allowed to “help” the drafter by reusing the same internal chain-of-thought or the same working memory

This separation is the point of the design. The critic is useful precisely because it is not the same model state as the drafter.

## 7. Cost & latency budget

The validator is an extra model call and a bounded retry loop. In a PM workflow, that is a worthwhile tradeoff because it prevents a human from reading an update that was invented, over-optimistic, or not grounded in the project data. The budget is intentionally strict: one validation round is normal, and a revision cap stops the system from looping forever. For risky drafts, we can spend a bit more to catch a bad proposal before it reaches the PM.

In this lab, the design is a high-cost validation budget: the critic adds a second model pass, plus a strict cap on revision loops, so the PM gets a grounded output without paying for infinite rework.

## Final decision

The agent is a small team, but only in the narrow sense that matters: one drafter and one validator. The drafter owns the task and the draft; the critic acts as a hard gate. The PM remains the final human decision-maker, and nothing is posted or committed without human review.
