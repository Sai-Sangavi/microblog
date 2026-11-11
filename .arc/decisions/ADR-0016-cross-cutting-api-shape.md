---
id: ADR-0016
category: cross_cutting
title: 'Cross-cutting: API shape'
status: accepted
superseded_by: null
component_id: null
decision: Single API inside the existing Flask app (/api blueprint) serving the server-rendered
  web UI and JSON clients; no gateway/BFF and no per-domain split until further clients
  exist.
evidence: recommended default, accepted by the human without review
---

## Context

recommended default, accepted by the human without review

## Decision

Single API inside the existing Flask app (/api blueprint) serving the server-rendered web UI and JSON clients; no gateway/BFF and no per-domain split until further clients exist.
