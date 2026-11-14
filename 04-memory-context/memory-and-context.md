# Context Engineering & Memory: Cortex PM Chief-of-Staff Agent

> Module 4 · Context Engineering & Memory
>
> We kept the starter fixture data for this round and documented the plan rather than swapping in a fresh data pack. The design goal is to be explicit about what each run can read, how it retrieves it, and how long that state is kept.

## 1. Context budget

Cortex should not receive the entire history of the system on every pass. The important context is:
1. the current task brief (the single bounded ask)
2. the project and its status/flags
3. the recent activity that proves what changed
4. the team norms and any relevant precedent
5. only then the next-sprint stories, which are queued for review rather than committed

Priority order: the current task is the anchor; project + activity are the source of truth; norms and precedent are guardrails; roadmap details stay retrieved and narrowed so confidential items never leak into a company-wide update.

## 2. Retrieve vs. long-context: per source

| Source | Size / volatility | Decision | Why |
|---|---|---|---|
| `get_activity` | large and changing | Retrieve | This is the fastest-moving source and the one that must be cited for progress claims. It needs an exact slice, not a giant long-context block. |
| `search_past_updates` | large and open-ended | Retrieve | Prior updates are useful precedent but should be searched and ranked. The model should not carry a whole history in-context. |
| `get_roadmap` | medium, structured, sensitive flags | Retrieve | It contains confidential/embargoed items, so it must be filtered and checked before any external update is drafted. |
| `get_norms` | medium, bounded but policy-critical | Retrieve | The agent must cite the exact rule it relied on, and the norms must stay current without flooding the context window. |
| `get_task` | bounded and static for the run | Long-context | One request is the anchor for the run and should be visible in full without extra retrieval. |

## 3. Retrieval quality plan

Each retrieved source gets at least one agentic move justified by its failure mode.

- **`get_activity`**: routing, document grading, reranking, caching
  - Routing picks the right project record; grading filters the PR/issue list; reranking keeps the most relevant updates first; caching avoids repeated reads in the same run.
- **`search_past_updates`**: reranking, self-verification, caching
  - Past updates are noisy; the system should rank the most relevant precedent and then verify that the draft reflects the matched pattern rather than inventing tone.
- **`get_roadmap`**: document grading, caching
  - The roadmap is relevant only for the in-scope project and must be filtered for confidential items before any update is drafted. |
- **`get_norms`**: routing, document grading, reranking, caching
  - The norms are a policy document, so the agent should retrieve the right section and verify that the draft obeys it before the PM sees it. |
- **`get_task`**: no retrieval move; keep it in-context for the run
  - This is the user ask, not a fetched corpus.

## 4. Memory map (your PM brain)

| Memory type | What Cortex stores | Scope / TTL |
|---|---|---|
| **Working** | task brief, current project context, this run’s tool results, active draft | current run + one retry loop |
| **Episodic** | recently completed task traces, accepted status drafts, prior approvals | 7 days |
| **Semantic** | durable team norms, project facts, approval preferences, known constraints | until explicitly updated |
| **Shared** | approved PM artifacts and queued backlog proposals | current run only |

## 5. Memory risks & mitigations

| Risk | Mitigation |
|---|---|
| Drift | Refresh the data on every run and re-validate key facts before the PM sees the draft. |
| Poisoning | Treat task content as data, not instructions; isolate tool outputs from the model's own prompt logic; reject embedded prompt-injection attempts and escalate. |
| Staleness | Use short episodic TTLs and refresh the source data at the start of each run. |
| PII / retention | Keep only the minimal approved artifact set; delete working memory after the run and avoid retaining raw drafts beyond the TTL unless a human explicitly approves. |

## Final note

This is the design choice I kept: short-lived working memory, bounded episodic retention, durable semantic facts, and no long-lived shared artifacts unless the PM has explicitly approved them. That keeps the loop readable, auditable, and safe without overloading the model context.
