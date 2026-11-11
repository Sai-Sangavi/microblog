---
id: ADR-0004
category: component
title: Job Queue
status: accepted
superseded_by: null
component_id: comp_job_queue
responsibility: Queue and job-state store between web app and worker; runs on Redis
  (managed) via RQ.
kind: infrastructure
split_reason: backing service the project uses but doesn't build
evidence: recommended default, accepted by the human without review
---

## Context

recommended default, accepted by the human without review

## Decision

Queue and job-state store between web app and worker; runs on Redis (managed) via RQ.

Kept separate because backing service the project uses but doesn't build.
