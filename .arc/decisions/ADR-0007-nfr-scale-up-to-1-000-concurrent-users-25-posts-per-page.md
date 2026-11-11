---
id: ADR-0007
category: nfr
title: "NFR: Scale \u2014 up to 1,000 concurrent users; 25 posts per page"
status: accepted
superseded_by: null
dimension: Scale
metric: Concurrent users
threshold: up to 1,000 concurrent users; 25 posts per page
component_id: null
needs_dedicated_tracking: true
evidence: recommended default, accepted by the human without review (page size from
  config.py POSTS_PER_PAGE)
---

## Context

recommended default, accepted by the human without review (page size from config.py POSTS_PER_PAGE)

## Decision

Concurrent users: up to 1,000 concurrent users; 25 posts per page
