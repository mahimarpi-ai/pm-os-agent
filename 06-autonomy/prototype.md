# Prototype: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 1, the working agent demo
>
> This version captures the M4 grounding proof: one grounded happy-path run and one withheld-source fail-safe run.

## What it does

Cortex reads a PM task, retrieves the project/activity/norms/precedent it needs, drafts a leadership update and queued stories, and stops at a human review checkpoint instead of posting or committing anything. In the M4 grounding probe, it proves it can cite its pulled sources and refuses to invent data when a required source is missing.

## How you built it

- **Coding agent:** the repo was run directly with the starter agent build in `00-build/`
- **Model + bounds:** default starter settings from `00-build/.env` (`gpt-4o-mini`; iteration cap, revision cap, queue cap retained in `agent.py`)
- **Repo / config:** `/Users/mahima.singh/pm-os-agent/00-build`
- **Live link:** not required for this repo-local demo

## Grounding evidence (required M4 capture)

### 1) Grounded answer with fresh pulled data

Caption: Cortex cites the refreshed project activity and metric from the retrieved data before it drafts the update.

```text
$ cd /Users/mahima.singh/pm-os-agent/00-build && python3 agent.py

[step 1] TOOL get_activity({'project_id': 'P-NORTH'})
  -> {"project_id": "P-NORTH", "activity": [{"id": "#820", "title": "Day-2 milestone email"}, {"id": "#823", "title": "Empty-state guidance copy (closes #818)"}, ...]}

[step 3] PROPOSED OUTPUT:
### Leadership Status Update for Project P-NORTH (Northstar)
... 
- **#820**: Day-2 milestone email (Merged on July 2, 2026)
- **#823**: Empty-state guidance copy (Merged on July 3, 2026)
- **Activation Rate:** 43% (increased from 41% week-over-week)

CRITIC, independent validation
{ "verdict": "pass", "reasons": [] }
```

### 2) Withheld-source failure case

Caption: Cortex refuses to invent the missing project and escalates instead of fabricating a GA date or a project that does not exist.

```text
$ cd /Users/mahima.singh/pm-os-agent/00-build && python3 agent.py missing-data

[step 1] TOOL get_project({'project_id': 'P-HALO'})
  -> {"error": "project_not_found", "project_id": "P-HALO", "known_projects": [...]}

================================================================
requested project P-HALO was not found; stopping and escalating to a human
================================================================
```

## How to run it

```bash
cd 00-build
python3 agent.py
python3 agent.py missing-data
```

This reproduces the grounded pass and the fail-safe withheld-source case in the same repo configuration.

