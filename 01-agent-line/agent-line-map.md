# Agent Line Map: Cortex PM Chief-of-Staff Agent

> Module 1 · The Agent Line
>
> ✅ **What this validates:** every risky action has a clear owner, by the end you'll have proven an above/below-the-line map with HITL checkpoints, scored on reversibility, blast radius, and measurability.

## The workflow, decision by decision

List every discrete decision or action in your agent's workflow, then score each one and place it **above** the line (a human owns it) or **below** (the agent owns it). Borderline calls get an HITL checkpoint.

| Decision / action | First instinct | Learner's reason | Reversibility (H/M/L) | Blast radius (H/M/L) | Measurability (H/M/L) | Final Above / Below | HITL? |
|---|---|---|---|---|---|---|---|
| Pull project state and activity | Below | It is just reading information, not posting anywhere. | L | H | H | HITL | Yes |
| Decide relevant context | Above | A human should always determine what drives decisions and what should be reported. | H | M | M | Above | No |
| Draft the update | Below | It's just drafting, not sending an update. | H | M | M | HITL | Yes |
| Decide tone and commitment level | Above | We need to control the narrative that is sent to leadership. | H | M | M | Above | No |
| Flag at-risk items or escalation needs | Above | Human needs to own what is escalated. | H | M | M | Above | No |
| Choose what to escalate | Above | Human should own the escalations. | M | H | M | Above | No |
| Propose a capped story batch | Above | Human should own prioritization. | H | M | M | HITL | Yes |
| Post an update | Above | All updates sent should be owned by humans because Cortex can make mistakes. | L | H | H | Above | No |
| Approve a company-wide update | Above | Any update that is sent should be owned by humans. | L | H | M | Above | No |

## Agent anatomy (sketch)

- **Model:** Use a fast model by default; escalate to a frontier model for complex or ambiguous work.
- **Tools:** Read project state and activity, search past updates, retrieve the roadmap and team norms, and propose a capped story batch for human approval. No publishing tool.
- **Memory:** Keep project facts in their source systems; persist approved updates, decisions, and team norms across runs. Never persist secrets.
- **Loop:** _placeholder, defined in M2 loop-spec.md_
- **Bounds:** _placeholder, defined in M5 bounds-and-evals.md_
- **Evals:** _placeholder, defined in M5 bounds-and-evals.md_

## Justifications

- Pulling project state and activity is HITL because an incorrect or incomplete retrieval could mislead downstream decisions and be hard to undo; deciding factors: blast radius and reversibility.
- Deciding relevant context stays above because a poor selection can shape what drives decisions and is reported to leadership; deciding factor: blast radius.
- Drafting the update is HITL because facts can be checked but completeness and framing involve judgment; deciding factor: measurability.
- Deciding tone and commitment level stays above because different people have different perspectives on tone; deciding factor: measurability.
- Flagging at-risk items or escalation needs stays above because assessing whether something is truly at risk involves judgment, and a missed flag can affect decisions; deciding factor: measurability.
- Choosing what to escalate stays above because humans should control it when a wrong routing choice could keep an important issue from someone able to act; deciding factor: blast radius.
- Proposing a capped story batch is HITL because there is no quantitative way to measure a “top” story; deciding factor: measurability.
- Posting an update stays above because humans should always own posting, which is hard to reverse once sent; deciding factor: reversibility.
- Approving a company-wide update stays above because broad company-wide reach makes the blast radius high; deciding factor: blast radius.

## Hardest call

Approving a company-wide update was the hardest call; blast radius settled it because the approval can affect the whole company.
