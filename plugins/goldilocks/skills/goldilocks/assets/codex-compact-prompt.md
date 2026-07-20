# Goldilocks Codex compaction prompt

This file is a **complete override** for Codex history compaction, not an additive fragment. Preserve enough operational state for a competent agent to continue without replaying consumed instructions or repeating completed work.

Produce a concise continuation summary with these sections:

## Objective

The original requested end state. A later steer changes it only when the user explicitly replaced or cancelled it.

## Constraints and non-goals

Active authorization, safety, project, tool, and verification boundaries.

## Steering ledger

For each material mid-flight user message, record `ADD`, `REPLACE`, `CANCEL`, or `QUESTION` and whether it is `pending`, `applied`, or `superseded`. Never present an applied steer as fresh work.

## Execution frontier

Separate Done, In progress, and Remaining. Include evidence for Done and exactly one **Exact next action**.

## Repository and verification state

Record the worktree or branch, important changed files or commits, checks already run with results, checks still required, blockers, authority needed, and the terminal condition.

## Do not repeat

List investigations, edits, migrations, external actions, and tests that remain valid and must not be repeated without contradictory evidence.

## Durable recovery source

If `.goldilocks/ACTIVE.md` exists, preserve its path and instruct the next agent to read it first, reconcile it with `git status`, diffs, commits, and current files, and then continue from Exact next action. Repository evidence wins over a stale ledger; the durable ledger wins over a lossy conversational reconstruction.

Also preserve applicable repository instructions, costly decisions with rationale, rejected approaches, unresolved risks, relevant file paths, and concise tool-result evidence. Aggressively discard duplicated narration, obsolete speculation, and large raw outputs.
