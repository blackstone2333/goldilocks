# Goldilocks v0.4.0 Structured-Artifact Pilot

Date: 2026-07-25
Artifact: 12-slide HSK4 one-to-one lesson, **网络购物：方便还是麻烦？**

## Question

Can Goldilocks apply its company-style hierarchy to a real presentation without embedding presentation-production instructions, while keeping every slide independently replaceable and one owner in control of the final PPTX?

## Route used

1. Lead froze the generic Artifact Contract, progressive-disclosure boundary, final quality gate, and integration ownership.
2. One Terra Standard owner produced the tool-agnostic Presentation Profile and 12-slide storyboard. Lead rejected its first classroom-size assumption; Standard repaired the storyboard from 8–20 learners to one-to-one instruction without touching the protocol.
3. Three parallel `gpt-5.3-codex-spark` Fast sessions produced slides 1–4, 5–8, and 9–12 as independent JSON unit packages. They never edited the final PPTX.
4. Lead acted as the single integration owner, adapted exact Codex Grid layouts, added notes/source policy, rendered every slide, inspected all slides full-size, inspected a montage, ran overflow validation, and exported the final PPTX.
5. Visual QA found one repeated orphan-punctuation defect class on slides 4, 5, 6, 8, and 9. Localized rework shortened only those unit strings; accepted slide content and the shared system were retained before the deck was re-exported.

## Measured evidence

| Dimension | Result | Boundary |
|---|---:|---|
| artifact quality | 12/12 slides inspected full-size; final montage coherent; 12/12 speaker-note records present; `slides_test.py` passed with no overflow | Human/Lead visual inspection plus deterministic file checks; no learner outcome study |
| expensive-token share | Not measurable for the full task because the native Standard and Lead paths did not expose comparable usage telemetry. The instrumented Fast production wave used Spark only, so it contained 0% Lead/Standard tokens | Do not generalize this to the full project |
| raw tokens | 142,686 reported Fast tokens: 22,356 + 59,398 + 60,932 | Fast worker wave only; excludes Lead and Standard |
| elapsed time | 208 seconds wall-clock for the three-worker wave; approximate individual durations totalled 541 seconds, so parallel execution shortened that wave's critical path by about 62% | Integration and QA were not timed as a controlled benchmark |
| user rounds | 0 after approval | The topic and release direction were already authorized |
| localized rework | 5/12 slides repaired for one repeated punctuation-wrap defect; no passing unit copy was rewritten | The canonical PPTX was necessarily re-exported by its integration owner |
| integration defects | 1 repeated presentation-fit defect class found, 0 unresolved; no concurrent canonical-file edits | This is one pilot, not a defect-rate estimate |

## File evidence

- `evals/artifacts/v040-hsk4-network-shopping.storyboard.md`
- `evals/artifacts/v040-hsk4/units/slides-01-04.json`
- `evals/artifacts/v040-hsk4/units/slides-05-08.json`
- `evals/artifacts/v040-hsk4/units/slides-09-12.json`
- `evals/artifacts/v040-hsk4-network-shopping.pptx`
- `evals/artifacts/v040-hsk4-network-shopping-montage.png`

The PPTX archive test passed, it contains 12 slide XML files and 12 notes XML files, every note carries the invented-classroom-material source statement, and the final PowerPoint render—not only the in-memory artifact render—was used for the montage review.

## Interpretation

The architecture worked: planning, content production, integration, and repair had separate owners; the final file had one editor; a format defect returned to the smallest affected units; and the Goldilocks active route stayed under its 1,600-word budget without copying the specialist presentation API.

The efficiency result is mixed. Parallelism materially shortened the Fast critical path, but three Spark sessions consumed far more raw tokens than the small copy task warranted because every session paid substantial plugin/MCP and general-agent startup context. v0.4 therefore must not translate “replaceable unit” into “one session per unit” or fixed worker quotas. For similar 12-slide decks, one Fast session or fewer larger batches is the initial route to test.

A follow-up optimization candidate is contract-selective tool startup: keep plugin/App/MCP capability available by default, but let a complete Fast contract explicitly declare that it needs no external tools. That idea requires a separate regression and must not restore blanket capability removal.

## Claim boundary

This pilot proves that Goldilocks v0.4.0 can orchestrate and validate one real structured artifact. It does not prove universal quality, speed, token, quota, or cost superiority over Direct production, and it does not change the published v0.2.2 Superpowers head-to-head certification.
