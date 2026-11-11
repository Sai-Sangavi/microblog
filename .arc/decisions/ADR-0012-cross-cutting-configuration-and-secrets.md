---
id: ADR-0012
category: cross_cutting
title: 'Cross-cutting: Configuration and secrets'
status: accepted
superseded_by: null
component_id: null
decision: Environment variables loaded via config.py/.env (SECRET_KEY, DATABASE_URL,
  MAIL_*, MS_TRANSLATOR_KEY, ELASTICSEARCH_URL, REDIS_URL); SECRET_KEY has an insecure
  default that must be overridden in production.
evidence: config.py
---

## Context

config.py

## Decision

Environment variables loaded via config.py/.env (SECRET_KEY, DATABASE_URL, MAIL_*, MS_TRANSLATOR_KEY, ELASTICSEARCH_URL, REDIS_URL); SECRET_KEY has an insecure default that must be overridden in production.
