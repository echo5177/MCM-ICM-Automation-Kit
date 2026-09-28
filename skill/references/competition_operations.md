# Competition Operations — Running the 4 Days

The rest of this Skill governs *what a good paper contains*. This file governs *how the
work gets done under a deadline*, which is where most teams actually lose the award: a
correct model that reaches the writer too late still produces a thin paper.

## Three lanes, not three people

Work splits into three lanes. A three-person team maps one person per lane; a solo entrant
(or one person working with an agent) still runs all three, just serially. The point is
that the lanes have **different done-conditions** and must not block each other.

```
Modeling lane   problem interpretation -> candidate models -> formulation -> assumptions -> validation plan
Coding lane     data -> implementation -> experiments -> figures/tables -> results manifest
Writing lane    outline -> figure storyboard -> body -> Summary Sheet -> stakeholder deliverable
```

The writing lane must start before the modeling lane finishes. Waiting for final numbers
before drafting is the most common way to end up with 14 thin pages: the structure,
notation, assumptions, and figure captions can all be written against *placeholders that
are clearly marked as such* and filled in as results land.

## The handoff contract

Every time work crosses lanes, it carries these fields. A number without them is not
usable and will be mis-stated in the paper:

| Field | Why |
| --- | --- |
| What it is | the quantity, in words |
| Units | the single most common source of silent error |
| Provenance | which script, which data, which parameter set produced it |
| Status | draft / validated / final — the writer must know if it can be quoted |
| Uncertainty | spread, interval, or "point estimate only" |
| Interpretation | what it means for the problem, in one sentence |
| Known risks | what could still change it |

Mark anything not yet final so it is visibly a placeholder in the draft. An unmarked
provisional number that survives into the Summary is a scoring defect.

## Contest clock

Derive the milestones from the *actual* contest window recorded in
`reports/rules_snapshot.md`, not from a hardcoded schedule. As fractions of the total
window:

| Progress | Milestone |
| --- | --- |
| ~10% | problem chosen; every sub-problem written as input / output / decision variable / objective / constraint |
| ~20% | data in hand and audited; assumptions drafted; figure storyboard sketched |
| ~35% | a deliberately crude **baseline** that runs end to end and produces a number |
| ~50% | the real model runs; first real figures exist |
| ~65% | complete draft of the body, placeholders marked |
| ~80% | validation, sensitivity, and uncertainty complete; results frozen |
| ~90% | Summary Sheet and the stakeholder deliverable written against final numbers |
| ~95% | **freeze** — no new modeling; only defect fixes, layout, and proofreading |
| 100% | rules re-check, AI report, `release_stage: final`, full gate (control numbers, page count, upload name), release packet |

The baseline at ~35% matters more than it looks: it converts "we have a plan" into "we
have a number", and a team that has never produced a number by the one-third mark is
usually the team that submits an incomplete paper.

## Freeze discipline

After the freeze point, a new idea is a liability, not an improvement. Past freeze, only:

- defects that make a claim wrong;
- missing required deliverables;
- layout, captions, and proofreading;
- the AI use report and submission mechanics.

Anything else goes in Future Work. A model improvement landed in the last hours is
unvalidated by definition, and it invalidates every number already written into the paper.

### Page-cut triage

Going over 25 pages late is common, and the cut is where papers break. The 2026 MCM A entry
found itself ten pages over in the last half hour; its section 6 collapsed to a heading while
the Summary still claimed a Latin-hypercube Monte Carlo sensitivity study. Cut in this order,
and re-read the Summary against the body after every cut:

1. repeated explanation and restated assumptions;
2. thin subsections merged into their neighbours;
3. figures resized or combined (never below legibility);
4. only then results, and never a result the Summary cites or a judge expects.

Do not buy pages with smaller fonts or tighter spacing: COMAP requires at least 12-point type.

### Draft, then final

Keep `release_stage: draft` in the config while drafting: the judge review is bound to the
PDF's SHA-256 and every rebuild voids it, so a draft only warns. Switch to `final` once, for
the submission build, then review that PDF, bind the review to it, and run the full gate.

## What to prepare before the contest opens

Nothing in this list requires knowing the problem, and all of it is expensive to build
under time pressure:

- the LaTeX skeleton on the official template, compiling, with the Summary Sheet header,
  running header, caption setup, and float parameters already tuned;
- the figure style: palette, fonts, sizing, export settings, and a reusable caption pattern;
- table styles for a notation table and a parameter table;
- a data-audit and results-manifest scaffold;
- the Kit's checks running green on the empty skeleton;
- editable figure sources (SVG/JSON/diagram code) organised so a figure can be revised in
  minutes rather than redrawn.

Related: [[award_patterns]] for what the finished paper must contain, `paper_standards.md`
for layout rules, `judge_rubric.md` for the release decision.
