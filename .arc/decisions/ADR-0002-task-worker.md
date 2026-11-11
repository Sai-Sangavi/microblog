---
id: ADR-0002
category: component
title: Task Worker
status: accepted
superseded_by: null
component_id: comp_task_worker
responsibility: RQ worker consuming the 'microblog-tasks' queue (app/tasks.py, e.g.
  export_posts, emailing results); runs from the same codebase as the web app.
kind: worker
split_reason: separate process with its own lifecycle, started by Procfile and supervisor
  as its own program
talks_to:
- component_id: comp_job_queue
  interaction: async
  evidence: rq worker microblog-tasks (Procfile)
- component_id: comp_relational_database
  interaction: sync
  evidence: app/tasks.py uses db.session and Task model
evidence: 'app/tasks.py; Procfile ''worker: rq worker microblog-tasks''; deployment/supervisor/microblog-tasks.conf'
---

## Context

app/tasks.py; Procfile 'worker: rq worker microblog-tasks'; deployment/supervisor/microblog-tasks.conf

## Decision

RQ worker consuming the 'microblog-tasks' queue (app/tasks.py, e.g. export_posts, emailing results); runs from the same codebase as the web app.

Kept separate because separate process with its own lifecycle, started by Procfile and supervisor as its own program.

## Talks to

- **Job Queue** (async) — rq worker microblog-tasks (Procfile)
- **Relational Database** (sync) — app/tasks.py uses db.session and Task model
