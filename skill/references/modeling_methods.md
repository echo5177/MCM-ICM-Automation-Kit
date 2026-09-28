# Modeling Methods — Anti-Error Reference

A defensive checklist of common modeling and coding mistakes, plus MCM/ICM-specific
norms. This is **not** a model-selection mandate: a capable agent (e.g. Claude) decides
which mathematical model fits the problem. Use this only to avoid known traps and to
match contest conventions — read the relevant block when building or reviewing a model.

> Adapted and condensed from the MathModelAgent norms knowledge base
> (`jihe520/MathModelAgent`, personal-use license), refocused on MCM/ICM and on
> anti-error rather than model selection.

## Modeling discipline (all problems)

- Re-verify the problem source: PDF extraction errors in formulas, sub/superscripts,
  units, and table fields silently send the whole model in the wrong direction.
- A sub-problem is only a top-level numbered question ("Problem 1/2"), not background,
  data notes, or submission requirements. State each one's input, output, decision
  variable/prediction target, objective metric, constraints, and dependency on others.
- Assumptions must be necessary, explainable, and parameterizable. Each one needs a
  reason, a scope of effect, and (where it matters) an alternative. Every key assumption
  must be **referenced where it is used** in the model — an assumption never cited again
  is dead weight a judge will challenge.
- Physical/business constraints outrank a good-looking fit. Computational convenience is
  not a reason to delete a key mechanism.
- If a later sub-problem adds resources/constraints/information but results barely move,
  go back and audit the base assumptions — something is probably wired wrong.

## Coding pitfalls (verify these before trusting any result)

- `scipy.optimize.minimize` only minimizes. To maximize profit/coverage/score, negate
  the objective and restore the true (positive) value in the results record.
- `scipy` inequality constraints are `fun(x) >= 0`. Capacity/upper-bound/budget
  constraints are the ones most often written backwards — write `C - x >= 0` for `x <= C`
  and plug in a few boundary points to check the sign.
- Never trust a solver's `success` flag alone. Re-substitute the solution into every
  constraint and print each constraint's value, bound, slack, and whether it is active.
- Integer / 0-1 / count variables cannot stay at the continuous relaxation. After
  rounding, re-validate feasibility; if infeasible, use an explicit repair heuristic, not
  blind rounding.
- Prevent data leakage: split first, then `fit` the scaler/encoder on train only and
  `transform` test. Never shuffle a time series. The test set never touches tuning.
- Fix the RNG seed for any stochastic algorithm; report mean and spread over multiple
  runs (>= 5) and, where possible, compare against an exact small-scale solution.
- Check data on load: encoding, column names, shape, units, missing/outliers. Do not
  keep modeling on misaligned columns or garbled headers.
- Units and symbols in code must match the modeling report exactly (length, mass, speed,
  radius, time step, coordinate origin).

## Anti-error by model family (traps only — not "use this for that")

- **Evaluation (AHP / entropy / TOPSIS / fuzzy).** Unify indicator direction first
  (benefit vs cost), weights sum to 1. AHP: consistency ratio CR < 0.1 or fix the matrix.
  Entropy: an indicator with identical values across alternatives correctly gets weight 0
  (not a bug). TOPSIS: needs >= 2 alternatives, standardize before distances; closeness
  C = D-/(D+ + D-) is not a 0-100 score. Highly correlated indicators double-count — run
  PCA first. Fuzzy: use a weighted-average operator, not max-min (which discards info).
- **Prediction / time series / regression.** Split by time, never shuffle. ARIMA: choose
  d by ADF, p/q by ACF/PACF or AIC/BIC. Grey GM(1,1) only suits short, near-exponential
  monotone series. Regression: check VIF (>10 = collinearity), residual normality /
  homoscedasticity / autocorrelation; declare extrapolation risk outside the training
  range. Always clip predictions to physical bounds (no negative population, prob <= 1).
- **Optimization.** Feasibility before objective — a model with no feasible solution is
  worse than one with a poor objective. Multi-objective: normalize each objective before
  weighting or do Pareto analysis; never add raw different-unit objectives. Heuristics
  (GA/SA/PSO) never "prove" global optimum without multi-start/seed stability or an exact
  comparison. TSP/VRP: forbid subtours (MTZ/lazy constraints); check capacity/time
  windows. Assignment: Hungarian needs a square matrix (pad with dummies).
- **Differential / dynamics / simulation.** State variables need units; initial and
  boundary conditions must be explicit. Stiff systems use `solve_ivp(method='Radau'|'BDF')`,
  not default RK45. Check conserved quantities (SIR: S+I+R=N) and step-size convergence
  (halve the step; change < 1% to call it converged). Fit on one window, validate on
  another. Monte Carlo: usually >= 10,000 samples; report a confidence interval, not just
  a mean. Markov: each transition row sums to 1; steady state needs irreducible + aperiodic.
- **Graph / network.** State directed vs undirected. Dijkstra forbids negative edges
  (use Bellman-Ford). Max flow needs flow conservation at every interior node and
  non-negative capacities; model an undirected edge as two opposing arcs. For > 1000
  nodes, O(V^3) Floyd is unacceptable — use repeated Dijkstra.
- **Statistics / ML.** Three-way split; tune on validation, evaluate once on test.
  Imbalanced data: report F1 / AUC, not accuracy. Time series CV uses TimeSeriesSplit, not
  random K-Fold. Prefer SHAP over tree `feature_importances_` (biased under correlation).

## Audit actions that can overturn your own choice

Lessons from the CUMCM Kit's 2026 post-mortem, where the official marking points were
published after the contest and could be compared with every draft. Each item below is a
check that is **allowed to overturn a choice already made**; a check that can only confirm
the current plan is not a check.

1. **Screen predictors for every quantity you forecast.** Correlate the target with every
   variable known at decision time (other data files, day type, season, the previous
   period), then compare the chosen model against two naive candidates out of sample: a
   grouped mean and a simple regression. In CUMCM 2026 the electricity-price factor was
   forecast with AR(1) (error 0.121, barely below the factor's own spread of 0.137); a
   two-class grouped mean scored 0.078 and a regression on the forecast supply gap 0.037.
   The diagnostic had already found a 0.983 correlation, used only to explain a result. The
   official marking points asked for exactly those two things. Rule: a decision-relevant
   variable with |r| > 0.8 in any diagnostic is re-evaluated for the model, even after freeze.
2. **Find the structure the problem setter planted.** Contest data are curated, sometimes
   generated: day-type classes, identities between files, one series driven by another. For
   each data file ask how it relates to the others, whether it has classes or cycles, and
   which quantity looks generated from which. When you find one, **name it in the paper**
   ("Fridays and Saturdays form one class"); a judge will not infer it from "same-type days".
3. **Values the problem states are the reference answer's baseline.** An initial state or a
   parameter given in the statement is almost always the setting the reference solution
   uses. Solve with it; put a "better" alternative in a comparison table. (CUMCM 2026 kept a
   free initial state as the main answer for six drafts; the official result used the given
   value.)
4. **Implicit use of future data.** In any rolling or day-ahead decision, a statistic
   computed over the whole evaluation period (an annual mean, a "typical day" built from the
   full year, a parameter tuned on the evaluation window) is future information. Use only
   history before each decision, or disclose the retrospective choice and validate it on a
   held-out window. Official marking points name this: "including implicit use".
5. **Asymmetric penalties become a quantile.** When shortfall and surplus cost differently,
   the optimal plan sits at the newsvendor critical ratio `c_u / (c_u + c_o)` of the forecast
   distribution, where `c_u` is the extra cost of a unit short and `c_o` the cost of a unit
   over. In CUMCM 2026 the emergency price was five times the planned price, so a unit short
   cost 4 extra against 1 for a unit over: plan to roughly the 80% quantile. A stochastic
   program already does this implicitly; write it explicitly and report the realised
   coverage.
6. **Give the reliability of every strategy the problem names.** When the statement
   contrasts two policies (plan vs adjust, fixed vs flexible), report each one's
   distribution, not just totals: the share of bad days, the worst day, the spread across
   random seeds, for every question including the last.
7. **Check what each decision variable is allowed to do.** A model can be arithmetically
   right and semantically wrong: CUMCM 2026 let an emergency purchase charge the battery,
   which the statement never allowed (63% of the emergency volume in one question).
8. **Sanity-check every headline table against a relation you know.** Recompute one
   identity from the table itself (P = V·I, a mass balance, a total). The 2026 MCM A entry's
   main results table printed average currents two to seven times smaller than its own power
   column implies at a 3.7 V cell voltage, and judges catch this kind of error on sight.

## Validation and sensitivity (mandatory in a contest paper)

- Sensitivity analysis is not optional. Perturb key parameters (+/-10%, +/-20%) and report
  how the objective/prediction moves; a tornado plot ranks parameter influence well.
- For optimization, perturb RHS or objective coefficients and check whether the optimal
  solution changes qualitatively. For prediction, perturb assumptions/initial conditions
  and report curve drift.
- If a small perturbation causes a large change, the model is sensitive to that parameter
  — say so explicitly rather than hiding it.
- Every sensitivity subsection must **end in a consequence or limitation**, not in "the
  model is robust". Say why the response is small or large mechanistically, and what a
  practitioner should therefore watch or what the model still cannot do. This is how the
  O papers write it (see `award_patterns.md`); a section that stops at "robust" is unfinished.

## Writing anti-error checklist

- The paper is not a worklog. No internal filenames, script names, temp dirs, result-JSON
  paths, or "generated by AI" traces in the body.
- Every numeric claim must trace to the results record / results JSON / a table / code
  output. Do not re-estimate or re-round at writing time.
- Define every symbol at first use. Lead into and interpret every figure/table — never
  stack figures with no prose between them, and never report a number without saying what
  it means for which decision.
- An assumption not referenced where it is used reads as filler. Tie each one to the model.
- References must be real and verifiable. Never fabricate a citation to look academic.

## MCM/ICM contest norms — VERIFY BEFORE RELYING ON THIS

> **This block is a snapshot, not authority.** It reflects the 2026 cycle as understood when
> written. COMAP changes rules between cycles (page counting, AI disclosure, formatting,
> submission mechanics). Before drafting, confirm the current rules against the official
> COMAP contest instructions and record what you found — year, page limit, what the limit
> counts, minimum font size, per-page team-number/page-number requirements, anonymity rules,
> AI disclosure and where the AI report goes, file naming and size — into
> `reports/rules_snapshot.md` with the source URL and the date you checked.
>
> If the official rules and this block disagree, **the official rules win** and this file
> should be updated. Never let a contest submission rest on a hardcoded snapshot.

- Checked 2026-09-28 against the instructions COMAP has posted for 2027
  (https://www.contest.comap.com/undergraduate/contests/mcm/instructions.php):
  - **25 pages** for the entire submission: Summary Sheet, table of contents, solution,
    reference list, notes, appendices, **code**, and any problem-specific requirement
    (a letter or memo the problem asks for). A team that used AI adds a section titled
    **Report on Use of AI** after the end of the report; it has no page limit and does not
    count.
  - English, readable font of **at least 12-point** type.
  - **Every page carries the team control number and the page number at the top.**
  - No names of students, advisor or institution anywhere; the control number is the only
    identifying information.
  - One Adobe PDF, **named `<control number>.pdf`**, under **25 MB**. Do not send programs,
    software, databases or other files; they are not used in judging.
  - `submission_checker` enforces the mechanical parts of this list.
- The **Summary Sheet** is a standalone page with very high judge weight: method
  highlights, key quantitative conclusions, and the modeling innovation — not a paste of
  the abstract.
- **Scoring dimensions** judges weight: reasonableness of assumptions; creativity of the
  modeling (multi-model comparison, non-standard approaches earn credit); correctness and
  plausibility of results (physically sensible, constraints respected, limiting cases
  behave); and clarity (coherent logic, professional visuals, reproducibility).
- **Visualization.** Award-winning papers are figure-heavy (often a majority of the page
  area). Use high-resolution vector figures (PDF/SVG), captioned and referenced in the
  body, with palettes that survive grayscale printing and are colorblind-safe.
- **Problem-type orientation** (what each historically emphasizes, not a model mandate):
  A (continuous) — PDE/physical/engineering modeling, heavy derivation; B (discrete) —
  graph/scheduling/combinatorial optimization, algorithm implementation; C (data
  insight) — data analysis, prediction, visualization, data handling; D/E/F (ICM) —
  operations research, sustainability, policy, interdisciplinary and written argument.
