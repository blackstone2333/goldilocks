# Presentation Profile

## Activate

Use this profile when the requested artifact is a presentation, slide deck, lesson deck, or speaker-led visual sequence. Load it after the generic artifact protocol; load a specialist presentation skill only when production, editing, rendering, or format-specific QA is needed.

## Plan before production

Standard turns the approved outcome into a storyboard: a slide sequence with a teaching or narrative arc, audience language, shared terminology, source policy, and a visual brief. Lead owns the audience/outcome, narrative decisions, design system, integration, and final QA; Standard supplies domain planning and does not replace those decisions.

Each unit is **one slide**, or a separately named reusable component where that is the safer boundary. A slide must be **independently replaceable**: its contract gives enough context for another worker to rebuild it without changing its neighbours.

### Slide contract

For every slide, state: ID and order; purpose/one takeaway; audience-facing content; dependencies and inputs; activity or presenter action; visual direction under the shared **design system**; required **speaker notes** and sources; acceptance checks; and ownership/batch assignment. Keep one primary job per slide.

## Parallel production and integration

Several non-dependent slides may be a **batch** for one worker session, but batching never merges their contracts or removes individual acceptance checks. Batch only contiguous slides with the same inputs, style, and low hand-off risk. Do not batch a slide that changes global structure, owns a shared visual, or awaits another unit's output.

Treat the slide contract as the rework boundary and the coherent content batch as the **session boundary**. For a simple **12-slide** text-led deck with one frozen storyboard and shared design system, begin with **one worker session** for all ready slide-content units; add another only when independent specialist work or measured critical-path savings repays its startup.

When the packaged Codex Fast adapter is used for slide content, select Luna with `--work-type luna`. Spark is optional only for deterministic presentation-generation code or file automation, not for teaching design, narrative copy, or visual judgment.

Workers produce contracted units and return evidence. Unit QA checks content accuracy, the contract, visual consistency, notes/sources, and local legibility. Rework is **localized rework**: repair only the failed slide and its direct dependency unless the global contract changed.

Exactly one **single integration owner** edits the final deck and resolves ordering, shared elements, transitions, and global consistency. Global QA inspects every slide at **full-size** for legibility, clipping, and notes, then uses a **montage** only to judge sequence, rhythm, and the design system. It also confirms the opening-to-close narrative, cross-slide terminology, required sources, and final-format acceptance rubric.

## Specialist boundary

Goldilocks coordinates contracts, evidence, review, and routing. The specialist presentation skill owns production methods, native-format handling, rendering, visual inspection, accessibility details, and format-specific repair. Do not copy specialist production instructions into this profile.
