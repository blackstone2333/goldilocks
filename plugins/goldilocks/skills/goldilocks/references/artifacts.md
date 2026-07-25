# Structured Artifact Orchestration

Use this protocol when a deliverable has a global system and independently checkable units: slides in a deck, sections in a report, sheets or regions in a workbook, or scenes in a video. Goldilocks owns the organization of production. A format-specific specialist skill owns the actual file format, rendering APIs, and domain mechanics.

The minimum complete route is:

`Goal → Global Artifact Contract → Unit Contracts → Parallel Production → Unit QA → Localized Rework → Integration → Global QA → Durable Lessons`

Skip the pipeline when one producer can finish and verify a small inseparable artifact sooner than the contracts can be briefed and reviewed.

## Freeze the global contract

Before units are dispatched, name one Lead owner and settle only the decisions every unit needs:

- audience and outcome;
- final format and delivery constraints;
- structure map and dependency graph;
- narrative, style, data, terminology, and source system;
- shared terminology and sources;
- unit inputs, outputs, dependencies, and stable boundaries;
- acceptance rubric and global verification method;
- merge order and exactly one integration owner.

Use [artifact-contract.md](../../artifact-production/assets/artifact-contract.md) when the contract must survive delegation or compaction. Adapt the repository's existing spec instead when it already carries the same information. Do not create a second planning hierarchy.

## Externalize one unit at a time

Turn the structure map into unit contracts using [artifact-unit-contract.md](../../artifact-production/assets/artifact-unit-contract.md). Each contract must be independently reviewable and replaceable without guessing global intent. It states identity, objective, inputs, dependencies, output shape, shared-system constraints, acceptance checks, ownership, forbidden changes, and evidence returned.

An execution unit is not necessarily an agent session. Keep the unit small enough for localized rework, but batch several independent, similarly tooled units in one worker session when startup and context cost would otherwise dominate. A batch never weakens per-unit acceptance or creates hidden cross-unit state.

## Route the production graph

Lead owns user intent, the global contract, shared interfaces, integration, and final acceptance. Give unresolved but bounded domain judgment to Standard; Standard may freeze that domain and issue complete contracts to Fast. Send already-decided units or batches directly to Fast. Fast is a leaf and may not change the global system or expand scope.

Parallelize only ready units. Shared dependencies and common assets receive one owner. Keep concurrent writers away from the same fragile final file; unit producers return contract-ready components, and the integration owner alone assembles or mutates the canonical artifact. Use the specialist skill required by each unit rather than teaching Goldilocks how to produce every format.

## Review locally, then integrate once

Run Unit QA against the unit contract before integration. Failures return to the smallest responsible unit with the failed criterion and retained passing evidence. This localized rework loop must not regenerate passing units unless a global decision changed. After a repeated unit failure, repair the contract, upgrade the worker, or keep that unit with its owner instead of restarting the entire artifact.

The integration owner merges accepted units in declared order, resolves shared-boundary conflicts, and runs Global QA for coherence, ordering, consistency, accessibility, source integrity, rendering, and final-format validity. A globally discovered defect still routes back to the smallest unit or shared system that caused it.

## Preserve only useful learning

Record Durable Lessons only when they are likely to improve a later artifact: a verified production route, reusable design/source system, recurring integration defect, or deferred idea. Store it in the project's existing execution memory, debug notes, or idea backlog. Do not keep worker transcripts, duplicate contracts, or temporary render files as workflow residue.
