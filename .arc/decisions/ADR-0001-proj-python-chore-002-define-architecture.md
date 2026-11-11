---
id: ADR-0001
category: component
title: PROJ Python Chore 002 Define Architecture
status: accepted
superseded_by: null
component_id: comp_proj_python_chore_002_define_architecture
responsibility: 'Flask web app and JSON API (blueprints auth, main, api, errors) for
  the Microblog application: users, posts, followers, private messages, notifications,
  search, translation, and enqueueing background jobs; served by gunicorn.'
kind: api_service
split_reason: exists in the code
talks_to:
- component_id: comp_relational_database
  interaction: sync
  evidence: app/__init__.py db = SQLAlchemy()
- component_id: comp_job_queue
  interaction: async
  evidence: app.task_queue enqueues jobs (app/__init__.py)
- component_id: comp_search_index
  interaction: sync
  evidence: app/search.py
evidence: 'scan: repo root manifest, Flask; app/__init__.py registers auth, main,
  api, errors blueprints'
---

## Context

scan: repo root manifest, Flask; app/__init__.py registers auth, main, api, errors blueprints

## Decision

Flask web app and JSON API (blueprints auth, main, api, errors) for the Microblog application: users, posts, followers, private messages, notifications, search, translation, and enqueueing background jobs; served by gunicorn.

Kept separate because exists in the code.

## Talks to

- **Relational Database** (sync) — app/__init__.py db = SQLAlchemy()
- **Job Queue** (async) — app.task_queue enqueues jobs (app/__init__.py)
- **Search Index** (sync) — app/search.py
