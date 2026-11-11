---
id: ADR-0008
category: deployment_target
title: "Deployment target: AWS, containers (ECS/Fargate) built from the existing Dockerfile;\
  \ staging and\u2026"
status: accepted
superseded_by: null
component_id: null
decision: 'AWS, containers (ECS/Fargate) built from the existing Dockerfile; staging
  and prod environments, each in a single region (region topology: one region, no
  replicas); managed database, Redis and Elasticsearch; web and worker run as separate
  services from the same image.'
evidence: recommended default, accepted by the human without review
contested: true
alternatives_considered:
- 'Heroku-style PaaS using the Procfile: less control over networking and managed
  services'
- 'Single VM with nginx + supervisor: no redundancy, manual operations'
consequences:
- Commits to container image builds and a managed-services setup on AWS
- Single region means a regional outage is an outage
---

## Context

recommended default, accepted by the human without review

## Decision

AWS, containers (ECS/Fargate) built from the existing Dockerfile; staging and prod environments, each in a single region (region topology: one region, no replicas); managed database, Redis and Elasticsearch; web and worker run as separate services from the same image.

## Alternatives considered

- Heroku-style PaaS using the Procfile: less control over networking and managed services
- Single VM with nginx + supervisor: no redundancy, manual operations

## Consequences

- Commits to container image builds and a managed-services setup on AWS
- Single region means a regional outage is an outage
