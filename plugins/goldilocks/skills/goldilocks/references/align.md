# Align

Use alignment only when unresolved choices can materially change the end state, architecture, user experience, trust boundary, scope, acceptance, or authority. A clear low-risk task needs no interview.

## Inspect before asking

Read the relevant code, docs, existing decisions, constraints, and project patterns first. Facts are the agent's job to investigate; preferences, trade-offs, and authority belong to the user.

Summarize a compact end-state contract:

- affected users or systems;
- required behavior and observable acceptance;
- constraints, safety boundaries, and non-goals;
- unresolved decisions.

## Question the decision frontier

Represent unresolved choices as a dependency tree. Ask only about frontier decisions whose prerequisites are known.

For each round:

1. Ask one question when choices depend on each other; ask at most three genuinely independent questions otherwise.
2. Put one decision in each question.
3. Recommend an option and state its main trade-off.
4. Defer child decisions until their parent is settled.
5. Continue useful read-only investigation when it can remove questions.

Do not dump every imaginable question, force a fixed interview count, or continue after the important branches are resolved.

For creative work, inspect the existing design system, libraries, assets, product language, and accessibility constraints. Offer two or three meaningfully different directions only when comparison helps; recommend one. Define how success will be recognized before implementation.

## Approval and authority

Require explicit approval when a choice changes the requested end state, commits to costly architecture, crosses an authority boundary, or enables a Critical action. Bind high-impact approval to the action, target, environment, scope, blast radius, and recovery plan or acknowledged irreversibility.

Credentials, tool access, urgency, or “use your judgment” are not authority for production, financial, destructive, permission, communication, or irreversible actions.

Stop alignment when the frontier is empty or remaining branches are explicit non-goals. Restate the chosen end state, assumptions, evidence, risks, and deferred decisions, then return to execution. Do not implement while a material choice is silently assumed; do not demand ceremonial approval for an already clear Direct task.
