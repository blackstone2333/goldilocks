# Alignment and Grilling

Use this only when unresolved decisions can materially change the end state, architecture, user experience, trust boundary, scope, or acceptance criteria. Clear Direct work needs no interview.

## Establish the end state

Summarize the intended outcome in a compact contract:

- users or systems affected;
- required behavior and acceptance evidence;
- constraints and safety boundaries;
- explicit non-goals;
- decisions still unresolved.

Inspect the codebase, documentation, tools, and existing decisions first. Facts are the agent's job to investigate; decisions and authority belong to the user.

A vague instruction such as “use your judgment,” urgency, possession of credentials, or access to a tool does not constitute authorization for an external, destructive, production, financial, permission, or irreversible action. Treat authority as unresolved until the concrete action and boundary are explicit.

## Walk the decision tree by frontier

Model unresolved choices as a **decision tree**. A child decision waits until its parent is settled. The **frontier** is the set of decisions whose prerequisites are already known.

For each round:

1. Recompute the frontier from current facts and answers.
2. Ask at most three independent frontier questions.
3. Put one decision per question; do not hide several decisions inside one numbered item.
4. Give a recommended answer and its main trade-off.
5. Defer dependent questions to the next round.
6. Continue useful fact-finding in parallel only when it has net benefit.

Use one question when dependency order matters. Use two or three when the choices are genuinely independent and separate turns add no clarity. Never dump the full tree into one round, and never force a 20-turn ritual when the important branches can be resolved safely in fewer rounds.

## Finish alignment

Stop when the frontier is empty or all remaining branches are explicit non-goals. Restate the shared understanding: chosen end state, assumptions, acceptance, risks, and deferred decisions.

Require explicit approval when the choice changes the requested end state, creates a costly-to-reverse architecture, crosses an authority boundary, or enables a Critical action. For high-impact or irreversible execution, approval must bind the action, target, environment, scope and blast radius, and recovery plan or acknowledged irreversibility. Otherwise continue using the stated safe assumption.

Do not implement while a material decision remains silently assumed. Do not keep interviewing after shared understanding is sufficient to execute and verify.
