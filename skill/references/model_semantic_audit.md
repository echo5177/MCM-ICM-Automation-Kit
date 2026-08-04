# Model Semantic Audit — Does the Math Mean What You Say It Means?

`modeling_methods.md` catches errors *inside* the math: sign flips, constraint direction,
leakage, infeasible rounding, unit mismatches. This reference covers the failure it cannot
see — math that runs correctly and still measures the wrong thing.

This is the highest-value review a judge performs and the one automation cannot do for you.
A model can be dimensionally consistent, numerically converged, and completely meaningless.

## The case that motivates this file

A real award-winning MCM paper (2023 Problem B, team 2316192) set the AHP pairwise
comparison weights for *Biodiversity*, *Environmental Quality*, *Economic Benefit*, and
*Difficulty of Implementation* by counting **Google Scholar search hits** — "Biodiversity"
returned about 47.7 million indexes, "Environmental Quality" about 13.1 million, and the
ratio was used to weight the criteria.

Search-hit counts measure how much literature exists, how broad a phrase is, and how a
database indexes it. They do not measure how much a criterion should matter to a
conservation policy decision. The arithmetic is fine. The construct is not. This passed
judging — do not assume a defect like this will be caught for you.

## The audit

Run this on every quantity that stands in for a real-world concept.

1. **Construct validity.** Does this number actually represent the concept it is named
   after? Write the sentence "X is a valid measure of Y because ..." and see whether it
   survives being read aloud. If the justification is "it was available", say so in the
   limitations instead of implying it measures Y.
2. **Proxy validity.** When a proxy stands in for an unmeasurable quantity, what evidence
   links proxy to target? Cite it, or show a correlation on real data, or label it an
   assumption with a sensitivity test attached. Popularity, search volume, and word
   frequency are *especially* weak proxies for importance, value, or priority.
3. **Causal direction.** Does the model use a correlation as if it were a cause? If the
   recommendation implies intervening on a variable, the evidence has to support that
   intervening changes the outcome, not merely that the two move together.
4. **Functional form.** Why *this* function? A weight defined as `sin α`, an exponential
   decay, or a logistic curve needs a reason beyond convenient shape. State what the form
   implies mechanistically, and test at least one alternative form to show the conclusion
   is not an artifact of the curve you happened to pick.
5. **Monotonicity and boundary behavior.** Push every input to its extremes — zero, very
   large, the ends of the feasible range. Does the output stay finite, stay in physical
   bounds, and move in the direction reality would? Report what happens at the boundary.
6. **Scale and commensurability.** Quantities being added, averaged, or weighted must be
   commensurable. Normalize before combining, and never sum raw values in different units
   or on different scales.
7. **Threshold provenance.** Every classification cut, tier boundary, and "high/medium/low"
   split needs a source: data-driven (quantile, clustering, changepoint), literature, or
   an explicitly labelled modeling choice tested for sensitivity. A round number chosen for
   convenience is a modeling choice — label it.
8. **Robustness to a reasonable alternative.** Swap the proxy or the functional form for a
   defensible alternative and re-run. If the qualitative conclusion flips, the conclusion
   belongs to the choice, not to the data — disclose that prominently.

## How to report it

Every construct that fails an item above gets one of:

- a **fix** (use a defensible measure instead), or
- an **explicit assumption** in the assumptions section, referenced where it is used, with
  a sensitivity test showing how much the conclusion depends on it, or
- a **stated limitation** that names the specific threat to validity.

Silence is the only unacceptable option. Judges reward honesty about a weak proxy far more
than they punish having one; they punish presenting a weak proxy as if it were a measurement.

Related: [[modeling_methods]] for the mechanical error checklist, `judge_rubric.md` for how
this feeds the `modeling_quality` and `data_evidence` scores.
