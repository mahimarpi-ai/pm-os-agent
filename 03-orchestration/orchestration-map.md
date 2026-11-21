# Orchestration Map

## 1. Why split / why not

This version of Cortex stays intentionally compact, but it still includes a separate validator step. The main reason to split is to keep a second pass on the draft before it reaches the PM, so the output is checked for traceability and policy compliance instead of being accepted on the drafter's own blind spots. The design stays small, but it is not a pure single-agent system because the validation pass is a deliberate architectural gate.

## 2. Topology

```text
[Inbound PM task]
    ↓
[Cortex: reads task + pulls project data + drafts update + stories]
    ↓
[Validator: separate post-draft check]
    ├─ fail → back to Cortex (revise, max N revisions)
    ├─ fail after cap → escalate to human
    └─ pass → [PM review checkpoint] → queued for human review
```

## 3. Roster

| Agent | Responsibility | Runs from |
|---|---|---|
| Cortex | Reads the request, pulls context, drafts the update, proposes stories | Loop Spec / M2 |
| Validator | Checks the draft for groundedness and policy compliance | Module 3 validator |
| PM | Reviews approved draft and decides whether to accept or adjust | Human decision point |

## 4. Hand-offs

The drafter hands off two things to the validator:
- the proposed draft
- the source log / evidence used to support it

The validator then returns either a pass or a reasoned rejection. If the draft fails, it is sent back to the drafter. Once it passes, it advances to the PM review checkpoint.

## 5. The validator

The critic checks both traceability and policy. It is responsible for making sure the draft:
- matches the real project data and pulled activity
- does not invent numbers, dates, or progress
- stays within the team norms and bounded operating rules

Fail-action: return the draft to the drafter and retry up to a fixed cap.
Revision cap: 2 revisions, then escalate to a human instead of looping forever.
Pass-action: if the critic passes, the draft reaches the PM review checkpoint.

## 6. Shared vs isolated state

Shared state:
- PM task brief
- project data pulled by Cortex
- recent activity / issue list / PRs / norms / roadmap
- draft text itself

Isolated state:
- the validator should not inherit the draft's same blind spots or internal assumptions
- validation reasoning stays separate from the drafter's loop

This keeps the two passes conceptually distinct without turning the design into a large fleet.

## 7. Cost & latency budget

This is a high validation budget because the design accepts additional model calls and a controlled retry loop to preserve quality. The extra cost is justified by the need to catch unsupported claims, bad dates, and policy violations before the PM sees the draft. The validator adds a meaningful but bounded overhead to the workflow.

## Final decision

The final topology is a single drafter plus a separate validator, with a PM checkpoint after approval. The validator sits after the draft, the fail path sends the draft back to the drafter, and the revision cap stops the loop before it burns tokens forever. Nothing is auto-sent; the PM remains the final human decision-maker.
