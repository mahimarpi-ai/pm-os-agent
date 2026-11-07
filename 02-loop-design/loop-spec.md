# Loop Spec: Cortex PM Chief-of-Staff Agent

> Module 2 · Loop Engineering, ★ Deliverable 2
>
> ✅ **What this validates:** the agent knows when to run and when to stop, by the end you'll have proven a one-page Loop Spec with a trigger, a definition of "done," and explicit stop conditions.
>
> Your one-page blueprint for how the work you handed to the agent (M1) actually *runs*.
> An agent is just a prompt that fires itself, this spec says when it fires, what "done" means, and what it needs to do the job. Living document; refine as the course progresses.

## 1. Trigger & loop type

**Chosen type:** Hook — triggered when a PM asks for a status draft.

**Why:** It should only be triggered when a PM asks for it.

**Why not the alternatives:** No heartbeat or cron because there is no periodic run; goal describes the work, not the trigger.

**Deduplication:** Before creating a draft, check whether the same draft already exists; if it does, do not create it again.

## 2. Goal / definition of done

A grounded status draft is created and sent to a human for review. It must never be posted without human review.

## 3. Stop conditions

| Condition | What it looks like | What happens |
|---|---|---|
| **Success** | A grounded draft has been created and sent to a human for review. | Stop successfully. |
| **Stuck / give up** | Four data-pull attempts fail for other retrieval errors. | Stop and log the failure. |
| **Escalate to human** | The requested project is not found, a requested date is explicitly marked unconfirmed in project data, or a completed draft is awaiting review. | Stop and escalate missing data/date questions; queue completed drafts for human review and never post automatically (HITL checkpoint). |

## 4. State

Within a run, track what has been added to or removed from the draft between iterations. Keep this state scoped to the current project and run.

## 5. The five things a loop can lean on

_`state` is always-on. `connectors` only if you already have one wired (e.g. a Jira key or Google MCP), otherwise just note it as a plan. `skills`, `subagents`, `work tree` scale with autonomy; "not needed yet, because…" is a valid answer._

| Component | For Cortex |
|---|---|
| **Work tree** (isolated workspace per run, a git worktree) | Not needed yet; it may be useful in the ideal case. |
| **Skills** (reusable capabilities) | Not needed yet. |
| **Plugins / connectors** (tools & access, optional if you don't have one yet) | None needed yet; current tools use local fixtures, with no live connector wired. |
| **Subagents** (independent check when the loop can't grade itself) | Not needed yet; existing tools retrieve information and the critic reviews outputs. |
| **State tracking** | Track draft additions and removals between iterations within the current project and run. |

> Context plan (M4) and the hand-off to bounds & evals (M5) come in later modules, you'll add them to their own deliverables then, not here.

## Link to live loop

_[path to your agent in `00-build/`]_
