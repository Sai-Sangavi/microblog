---
id: ADR-0003
category: component
title: Relational Database
status: accepted
superseded_by: null
component_id: comp_relational_database
responsibility: Stores users, posts, followers, messages, notifications and task records;
  schema managed by Alembic migrations. Runs on PostgreSQL (managed) in production;
  SQLite only for local development.
kind: infrastructure
split_reason: backing service the project uses but doesn't build
evidence: recommended default, accepted by the human without review
---

## Context

recommended default, accepted by the human without review

## Decision

Stores users, posts, followers, messages, notifications and task records; schema managed by Alembic migrations. Runs on PostgreSQL (managed) in production; SQLite only for local development.

Kept separate because backing service the project uses but doesn't build.
