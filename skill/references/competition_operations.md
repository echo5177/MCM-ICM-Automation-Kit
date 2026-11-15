# Competition Operations — Running the 4 Days

The rest of this Skill governs *what a good paper contains*. This file governs *how the
work gets done under a deadline*, which is where most teams actually lose the award: a
correct model that reaches the writer too late still produces a thin paper.

## The first hour belongs to a person

Before any model, a person reads the problem and fills two columns of
`reports/requirements.csv` for every requirement:

- `turns_on`: one plain sentence on what the requirement turns on. The trade-off, the
  quantity that decides the answer, or the ratio or penalty the statement gives and how it
  enters the decision. "How much to over-buy when a unit short costs five times a unit
  over", not "a stochastic optimisation with asymmetric penalties".
- `expected`: what the answer should look like, with a rough size or direction.

The agent does not write these and does not propose a route until they exist. Three reasons,
all from the CUMCM 2026 post-mortem:

1. A framework chosen in the first ninety minutes by an AI-written plan was never revisited
   in eight drafts, and no experiment was designed that could have overturned it.
2. During that contest a "forecast, storage, rolling correction" framework of the same kind
   was on sale within three hours. A framework an assistant proposes by default is the one
   thousands of teams receive, and COMAP compares every paper with every other paper on the
   same problem. What sets a paper apart is a finding specific to this problem, and that
   starts from someone understanding what the problem turns on.
3. `expected` is what makes a result informative. A result that differs from it is a finding
   or a bug, and either way the paper gets a sentence it would not otherwise have ("we
   expected X; the model gives Y, because ..."). The showcased papers were written this way;
   ours stated results and never argued.

Later, each sentence in `turns_on` opens that task's section and its paragraph of the
Summary Sheet.

**Explaining back.** Before a model goes into the paper, the person explains it without
notes, in a few sentences: what goes in, what comes out, why this and not something simpler.
A model that cannot be explained is replaced by one that can. COMAP's judges call adopting a
complicated component one cannot explain "the classic red herring of the contest".

**Readers during the contest are teammates only.** The rules forbid help from anyone outside
the team once the problem is posted, so the fresh reader the post-mortem asks for (someone
who reads the Summary and the first three pages on day one and says where they got lost) has
to be a teammate who has not been writing. Before the contest, practice papers can be read
by anyone.

## The model ladder

For every modeling requirement the pipeline writes `reports/model_ladder.csv`: rung 0 is the
naive baseline (a grouped mean, a linear fit, the rule a person would use), and each rung
above it adds one component, all scored on one metric, out of sample where that applies.
**A component stays only if it wins**, and the paper prints the comparison, because judges
do not see the code. `model_ladder` fails when the rung the paper keeps loses to a simpler
one and no reason is recorded.

Build it in this order:

1. Rung 0 for every requirement before any requirement gets a second rung. A paper with a
   number for each requirement is an Honorable Mention candidate; a paper with one requirement
   polished and another empty is not.
2. Add a component, rerun, record the rung. If it does not win, it goes in the table as a
   rung that was tried, and the paper may say so in a sentence.
3. Remove components too. The check that mattered in CUMCM 2026 was never run: taking the
   controller out. Removing it cut the annual cost from 1467.57 to 1390.62 (ten thousand
   yuan), and replacing the plan with a quantile rule brought it to 1371.60, level with the
   showcased papers. The order of removal matters when components interact, so record what
   was removed from what.

The judges' wording: "Start with a simple model and then refine it", "it is far better to
work out one model thoroughly than to present several half-baked approaches", and, from a
head judge's commentary, "overparameterization is often the mark of mediocrity"; models with
many variables made a meaningful sensitivity analysis hard for the teams that built them.

## Contest-window rules, for the team and for the agent

From the moment the problems are posted until the paper is submitted, COMAP's rules bind
everything done on the team's behalf, searches run by an agent included.

- **No person outside the team.** Not the advisor, not a classmate, not a forum, not a paid
  "assistance" group. A message from another AI session is not a person; a human reviewer is.
- **No page where this year's problem is being discussed, and no one else's solution.** COMAP
  monitors the web during the contest. "Unsuccessful Participant - Web" is the designation
  for a team whose member "visited websites or social media where contest problems were being
  openly discussed"; obtaining any part of another solution is "Disqualified - Web". In
  practice: do not search for the problem's title or number, do not open results from CSDN,
  Zhihu, Bilibili, Xiaohongshu, Weibo, WeChat articles or contest-service sites, and do not
  open a GitHub repository created after the problems were posted. If a search for data
  returns such a page, do not open it; find the primary source another way.
  `source_checker` fails a source whose URL is on one of these platforms.
- **Finished papers and "idea packs" sold during the contest are both of the above.** They
  are also worthless for a second reason: thousands of teams receive the same text, and COMAP
  compares every paper with every other paper on the same problem.
- **Search for data and methods at their source.** Agencies, dataset publishers, journals,
  textbooks, software documentation. Record each in the source manifest as it is used.
- **Log every AI tool as it is used** in `reports/ai_use_log.csv`, embedded ones included
  (translation, code completion). Build the Report on Use of AI from the log
  (`scripts/build_ai_report.py`); cite each tool in the text and in the reference list.
- **Nothing is posted or shared.** Keep the repository private until results are out.

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
| ~35% | a deliberately crude **baseline** for *every* requirement, end to end, each producing a number (rung 0 of the model ladder) |
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
