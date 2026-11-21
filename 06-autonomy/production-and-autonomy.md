# Production & Autonomy: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 5, how you'd ship it, govern it, and widen trust over time
>
> ✅ **What this validates:** you can ship it, govern it, and widen trust deliberately, by the end you'll have proven an autonomy dial, a Trust Ladder rung with its eval gate, and a governance plan.

## Autonomy Dial by segment

Autonomy is a product decision per user, not one global setting.

| Segment | Desired autonomy | Why |
|---|---|---|
| Seasoned PM / operations user | supervised | Final review and posting stays with a human. |
| New engineering lead | assisted | Cortex asks clarification questions; the lead answers; Cortex drafts; the human posts. |

## Trust Ladder

- **Current rung:** assisted. "To ensure that it does not create incorrect updates."
- **Eval gate to reach the next rung:** all five offline replay cases pass on every change; then at least 95% pass on EV-1 through EV-4 across at least 20 assisted runs over four consecutive weeks, with zero unsafe EV-5 actions.
- **Incident record so far:** clean means zero unauthorized actions or confidential exposures; 100% of incidents and near-misses logged with run ID, M5 eval, timestamp, trigger, containment, owner, and resolution; no unresolved incidents at the end of the four-week window.

## Deployment plan

- **Runtime:** planned serverless, event-triggered Hook. It runs only when a PM requests a status draft, so it does not need an always-on worker. The prototype still uses local fixtures; production hosting and a live connector are not wired.
- **Operator / on-call owner:** Mahima Singh.
- **Escalation path:** escalate to Mahima Singh; the draft remains unchanged until she reviews it. If she is unavailable, disable the Hook and hold drafts; do not enable production until a backup owner and alert destination are configured.
- **Rollback:** disable the Hook, set the local KILL switch, and revert the prompt/config. Production pause and credential revocation remain external and unwired.
- **Monitoring:** eval pass rate, escalation rate, cost per run, and trust incidents.

## ROI metrics (beyond adoption & tokens)

| Metric | Target |
|---|---|
| Outcome | At least 90% of drafts accepted without material rewrite over 20 assisted runs; capture the run ID and human review outcome. |
| Cost-to-serve | At least 30% lower median time-to-approved-draft than the manual baseline and no more than $0.05 per accepted draft; capture human review timestamps and run cost. |
| Trust incidents | Zero unauthorized posts or confidential exposures; log 100% of incidents and near-misses with run ID, M5 eval, timestamp, trigger, containment, owner, and resolution. |

## Widen-autonomy decision rule

Move from assisted to supervised only after all five offline replays pass on every change; EV-1 through EV-4 reach at least 95% across at least 20 assisted runs over four consecutive weeks; EV-5 has zero unsafe actions; all three ROI targets are met; no incidents remain unresolved; and Mahima explicitly approves the change.

## Governance & forward strategy

- **Compliance:** never put secrets, credentials, confidential or embargoed content, or unnecessary PII in a prompt. Minimize PII and redact sensitive data from traces.
- **Safety:** keep every M1 above-the-line decision human-owned: project retrieval and context selection, draft review, tone and commitment level, risk flags and escalation choices, story prioritization, posting, and company-wide approval. Cortex has no publishing tool.
- **Kill switch:** the local `00-build/run-output/KILL` marker stops new calls when checked but cannot cancel an in-flight call. Production must be able to disable the Hook and revoke scoped access; that control-plane integration is external and unwired. If the owner is unavailable, keep the Hook disabled and drafts held.
- **Reliability:** enforce the M5 limits of 8 turns, 90 seconds per run, $0.50 per run, and 2,048 completion tokens; stop and escalate at a limit. A provider-side hard cost cap is required for an absolute billing guarantee. If the model is unavailable, fail closed and use the manual PM workflow.
- **Strategy:** next, add a live read-only project connector; keep write and post actions unavailable. Before expansion, all five offline replays must pass on every change; EV-1 through EV-4 must reach at least 95% across at least 20 assisted runs over four consecutive weeks; EV-5 must have zero unsafe actions; all ROI targets must be met; connector project-scope and confidential-redaction evals must pass; no incidents may remain unresolved; and Mahima must explicitly approve.
