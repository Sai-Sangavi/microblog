---
id: ADR-0011
category: cross_cutting
title: 'Cross-cutting: Authentication'
status: accepted
superseded_by: null
component_id: null
decision: Session login via Flask-Login for the web UI; token (bearer/basic) auth
  for the JSON API under /api.
evidence: app/api/auth.py, app/api/tokens.py, app/__init__.py LoginManager
---

## Context

app/api/auth.py, app/api/tokens.py, app/__init__.py LoginManager

## Decision

Session login via Flask-Login for the web UI; token (bearer/basic) auth for the JSON API under /api.
