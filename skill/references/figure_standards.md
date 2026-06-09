# Figure Standards

## First Workflow/Model Figure

The first conceptual figure is a scoring-critical artifact. It should be information-dense and elegant. Do not create a simple chain of boxes unless the problem is genuinely simple.

A strong first figure often includes these layers:

- problem inputs and raw data;
- cleaning, feature construction, or parameter estimation;
- model states and decision variables;
- governing equations or rule blocks;
- numerical solver or optimization loop;
- validation, diagnostics, uncertainty, and sensitivity;
- outputs, policy recommendations, or contest deliverables;
- feedback arrows where the workflow iterates.

Design expectations:

- Use grouped bands or columns, not floating boxes scattered on a blank canvas.
- Use color to encode roles, not decoration.
- Include short formulas or variable names inside the diagram where useful.
- Use icons sparingly only when they clarify inputs/outputs.
- Make the figure legible at the final paper width.
- Store editable source such as JSON/SVG/PPTX/diagram code alongside PNG/PDF.

## Figure Planning

Before rendering, write a figure plan:

- figure id and paper location;
- question answered;
- data source;
- visual encoding;
- key caption message;
- failure mode to avoid.

## Visual QA

After generating figures and PDF pages, inspect them visually. Check:

- text is legible;
- no overlapping labels;
- axes and units are present;
- colors are distinguishable when printed;
- captions state the interpretation;
- the figure adds evidence, not decoration.

A diagram checker that only checks file existence and dimensions is insufficient.
