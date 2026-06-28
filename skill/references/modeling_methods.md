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

## Validation and sensitivity (mandatory in a contest paper)

- Sensitivity analysis is not optional. Perturb key parameters (+/-10%, +/-20%) and report
  how the objective/prediction moves; a tornado plot ranks parameter influence well.
- For optimization, perturb RHS or objective coefficients and check whether the optimal
  solution changes qualitatively. For prediction, perturb assumptions/initial conditions
  and report curve drift.
- If a small perturbation causes a large change, the model is sensitive to that parameter
  — say so explicitly rather than hiding it.

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

## MCM/ICM (2026) specifics

- **Page limit: 25 pages** counting the Summary Sheet, table of contents, solution, and
  references — but **NOT** the AI Use Report appendix. LLM/generative-AI use is allowed and
  must be disclosed in that report; it does not count toward 25.
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
