---
id: ADR-0005
category: component
title: Search Index
status: accepted
superseded_by: null
component_id: comp_search_index
responsibility: Full-text index of posts, enabled in production; runs on Elasticsearch
  (managed). The code stays optional when ELASTICSEARCH_URL is unset.
kind: infrastructure
split_reason: backing service the project uses but doesn't build
evidence: recommended default, accepted by the human without review
---

## Context

recommended default, accepted by the human without review

## Decision

Full-text index of posts, enabled in production; runs on Elasticsearch (managed). The code stays optional when ELASTICSEARCH_URL is unset.

Kept separate because backing service the project uses but doesn't build.
