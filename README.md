# Cortex: PM Chief-of-Staff Agent

**By Mahima Singh · Product School, Agentic Loops for PMs**

Cortex helps a PM prepare a grounded weekly leadership update and a capped set of next-sprint story proposals. It retrieves project and activity evidence, drafts the update, sends it through an independent critic, and stops at human review. Cortex has no publishing tool: nothing is posted automatically.

> **Current Trust Ladder rung: assisted.** This is a local-fixture prototype, not a production integration. Proposed stories still need PM validation.

## Project at a glance

| | |
|---|---|
| **Trigger** | A PM requests a status draft for one project (Hook pattern) |
| **Build** | Copilot SDK in VS Code; runtime and fixtures in [`00-build/`](00-build/) |
| **Drafter model** | `gpt-4o-mini` |
| **Critic** | Independent `gpt-4o` review in the recorded M6 run |
| **Bounds** | 8 turns, 90 seconds, $0.50 estimated per-run cap, 2,048 completion tokens, and at most 10 queued stories |
| **Data / integrations** | Local fixtures; no live project connector or publishing integration |
| **Demo link** | None |

The cost limit uses conservative request reservations; a provider-side hard budget is still needed for an absolute billing guarantee.

## Final deliverables

| Deliverable | Summary |
|---|---|
| [Working prototype and run evidence](06-autonomy/prototype.md) | End-to-end behavior, safety cases, and six M2–M6 captures |
| [M1 · Agent Line Map](01-agent-line/agent-line-map.md) | Human-owned decisions and HITL checkpoints |
| [M2 · Loop Spec](02-loop-design/loop-spec.md) | Trigger, definition of done, state, and stop conditions |
| [M3 · Orchestration Map](03-orchestration/orchestration-map.md) | Cortex drafter, separate validator, bounded revision path, and PM review |
| [M4 · Memory and Context](04-memory-context/memory-and-context.md) | Retrieval and project context strategy |
| [M5 · Bounds and Evals](05-bounds-evals/bounds-and-evals.md) | Runtime limits, failure modes, and five-case offline replay suite |
| [M6 · Build Insights](06-autonomy/build-insights.md) | Friction, learning, aha, and what would change |
| [M6 · Production and Autonomy](06-autonomy/production-and-autonomy.md) | Autonomy dial, Trust Ladder gate, deployment, ROI, and governance |
| [Final project pitch deck](pitch.html) | Standalone HTML presentation |

## Demo evidence

All six run captures are in [`06-autonomy/`](06-autonomy/):

1. [M2 · Happy path](06-autonomy/m2-happy-path.png) — grounded draft and story proposals held for review.
2. [M3 · Critic rejection](06-autonomy/m3-critic-rejection.png) — rejected revisions reach the cap and escalate.
3. [M4 · Missing source](06-autonomy/m4-missing-source.png) — missing project stops the run before drafting.
4. [M5 · Jailbreak preflight](06-autonomy/m5-jailbreak-preflight.png) — prohibited requests flagged before model or tool calls.
5. [M5 · Iteration cap](06-autonomy/m5-iteration-cap.png) — run halts at the two-turn test cap without producing a draft.
6. [M6 · End-to-end run](06-autonomy/m6-end-to-end-clean.png) — critic passes; draft and story proposals pause for PM review.

## Human control and trust gate

Cortex can retrieve evidence, draft, queue up to 10 story proposals, and request a critic review. Humans retain ownership of context selection, tone and commitments, risk and escalation judgments, story prioritization, final approval, and all posting. The prototype exposes no publish action.

The planned next rung is **supervised**. Widening requires all five offline replay cases to pass on every change; at least 95% pass on EV-1 through EV-4 across 20 or more assisted runs over four consecutive weeks; zero unsafe EV-5 actions; all three ROI targets below; no unresolved incidents; and explicit owner approval. A clean incident window means zero unauthorized posts and confidential exposures, with every incident and near-miss logged and resolved.

## Ship plan and ROI

- **Planned runtime:** serverless, event-triggered Hook; production hosting is not wired.
- **Owner:** Mahima Singh. If unavailable, the Hook should stay disabled and drafts held until a backup owner and alert destination are configured.
- **Rollback:** disable the Hook, set the local kill switch, and revert prompt/config. Production pause and credential revocation still need control-plane integration.
- **Monitoring:** eval pass and escalation rates, cost per run, and trust incidents.

| Measure | Target | Capture |
|---|---|---|
| Outcome | At least 90% of drafts accepted without material rewrite over 20 assisted runs | Run IDs and human review outcomes |
| Cost-to-serve | At least 30% lower median time-to-approved-draft than manual baseline, and at most $0.05 per accepted draft | Review timestamps and run cost |
| Trust incidents | Zero unauthorized posts or confidential exposures; log all incidents and near-misses | Run ID, eval, timestamp, trigger, containment, owner, resolution |

## Run locally

From the repository root:

```bash
cd 00-build
python3 agent.py                 # happy path; model-backed run requires a configured API key
python3 agent.py missing-data    # missing project; stops and escalates
python3 agent.py jailbreak      # deterministic preflight refusal
CORTEX_MAX_ITERATIONS=2 python3 agent.py happy  # test the iteration cap
```

Runs use the local fixtures in [`00-build/fixtures/`](00-build/fixtures/). Drafts are held for human review; no publishing tool is available. See the [runbook](00-build/RUNBOOK.md) for setup and additional bound-trip scenarios.

## Known gaps before production

- Add a live, read-only project connector and pass project-scope and confidential-redaction evals.
- Configure a provider-side hard spend limit, production kill/rollback controls, scoped JIT authorization, alerts, and a backup on-call owner.
- Have a PM validate the proposed stories and review draft outcomes in assisted runs before considering a higher Trust Ladder rung.
