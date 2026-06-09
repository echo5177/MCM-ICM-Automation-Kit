# Data And Source Standards

## Source Roles

Classify every source by role:

- official_problem: contest statement or official contest data;
- true_dataset: downloaded data used directly in computation;
- parameter_source: source used to set or calibrate parameters;
- documentation_source: supports method or data collection discussion;
- validation_source: independent evidence used to check outputs;
- scenario_assumption: synthetic or assumed scenarios created by the team.

Do not let documentation_source or source-card files masquerade as true_dataset.

## External Data Workflow

1. Write concrete data needs before searching.
2. Prefer primary, official, public, stable, citable sources.
3. Record rejected sources and why if the choice is not obvious.
4. Download or save the actual data/evidence used.
5. Record URL, access date, license/terms, local path, hash, role, and paper usage.
6. Parse or transform data with scripts; keep processed outputs reproducible.
7. Tie each parameter or claim to either data, a cited source, or an explicit assumption.

## Parameter Tables

A parameter table should include:

- symbol/name;
- value and unit;
- source role;
- source id or derivation;
- uncertainty/range when relevant;
- where the parameter appears in the model.

Avoid vague entries such as "source-justified modeling assumption" unless accompanied by a concrete citation, range, or derivation.

## When No Real Dataset Exists

It is acceptable to use transparent scenario simulation when the problem permits it, but the paper must say so plainly. Strengthen the answer by adding sensitivity, uncertainty, sanity checks, and a future data-acquisition path.
