# Benchmarking Lessons for Agent Workflows

[简体中文](benchmarking-lessons.zh-CN.md)

These practices come from the frozen v0.5.0 release matrix and its offline audit. They are a method guide, not a claim that every workflow or host will behave the same way.

## Classify the failure before using the result

Keep three classes separate in the ledger:

- **Participant failure:** the agent's completed work fails the specified acceptance.
- **Harness failure:** the driver, completion predicate, scope rule, or grader misclassifies a result.
- **Infrastructure failure:** provider, stream, filesystem, or transport prevents a cell from reaching a product outcome.

Only participant failures support product-quality conclusions. Preserve every row, including its raw telemetry, but do not convert a harness or infrastructure failure into a product defect or a quality ranking.

## Exercise the real activation path

Testing a Hook by calling its script directly is not evidence that the host activates it. Use an installed fixture, start a fresh host task, and record discovery/activation evidence separately from the participant's work. A missing expected child-name prefix is a useful signal that the Hook or Skill did not load; it is not evidence about routing quality.

## Let the host account for usage

Usage belongs to host telemetry, not participant prose or a participant-side accounting command. Treat usage as unavailable when the host has not emitted a checkpoint; fail silently rather than estimating or reporting zero. This prevents benchmark overhead and self-reported usage from changing the thing being measured.

## Grade meaning, not a preferred word

Acceptance tests should assert the required state or behavior, not a token such as one heading word. Add both positive paraphrase fixtures and negative missing-state fixtures before freezing a grader. If an audit discovers a lexical false negative, preserve the raw row, make the correction offline, disclose it, and do not rerun a completed model cell merely to obtain a different label.

## Drive interactive workflows as interactions

An assistant workflow may legitimately ask for approval, a recommended A/B choice, a terminal yes/no, or confirmation that a TDD baseline may fail. The driver needs frozen, requirement-preserving replies to those expected gates and a repeated-no-progress safety stop. Do not mistake an unrecognized but answerable question for a participant failure.

## Separate official cost from an authorization proxy

Publish official priced-model subtotals as such. Keep a separately named comparison estimate when a model is supplied from an allowance pool without a public numeric rate. For this release, normalized cost is the official subtotal plus a user-authorized Luna-equivalent Spark proxy; it is not an invoice and it must not be described as one.

## Freeze the protocol and maintain a ledger

Before model calls, freeze inputs, hidden acceptance, arm identity, order, model/host configuration, and the accounting rule. Record prompt envelopes, outcome state, elapsed time, raw Token, model mix, cost boundary, and every exception in a ledger. Do not automatically rerun a scored cell: preserve the attempt, classify the cause, and authorize any retry explicitly under a stated rule.

## Keep continuity distinct from ownership

A fresh session can continue from durable evidence without replaying old work. That does not justify splitting a known mutable execution chain between owners: one owner should carry the complete known chain, with Lead performing one final combined acceptance. Evaluate session continuity and ownership boundaries independently.

See the [v0.5.0 release evidence](../benchmarks/V050-RELEASE-EVIDENCE.md) for the frozen matrix to which these lessons apply.
