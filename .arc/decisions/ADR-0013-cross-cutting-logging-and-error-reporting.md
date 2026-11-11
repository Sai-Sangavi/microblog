---
id: ADR-0013
category: cross_cutting
title: 'Cross-cutting: Logging and error reporting'
status: accepted
superseded_by: null
component_id: null
decision: Rotating file log or stdout (LOG_TO_STDOUT); ERROR-level logs emailed to
  ADMINS via SMTP.
evidence: app/__init__.py
---

## Context

app/__init__.py

## Decision

Rotating file log or stdout (LOG_TO_STDOUT); ERROR-level logs emailed to ADMINS via SMTP.
