# AMON Visual Acceptance

Status: REQUIRED GATE
Parent authority: AMON Design Constitution v2

---

## 1. Principle

Automated QA cannot approve visual quality.

A feature may be technically correct and visually unacceptable.

The following are separate gates:

- Functional PASS
- Data Safety PASS
- Interaction PASS
- Accessibility PASS
- Responsive PASS
- Visual PASS

Only a human may issue Visual PASS.

---

## 2. Agent language

Agents MAY say:

- implementation complete;
- automated QA passed;
- interaction contract verified;
- screenshots captured;
- ready for human visual acceptance.

Agents MAY NOT say:

- premium achieved;
- visually approved;
- design approved;
- AMON quality achieved;
- final visual pass;

unless explicitly quoting a human approval from the current work cycle.

---

## 3. Required visual evidence

For a visual ticket, provide evidence for applicable states.

Minimum:

- rest;
- hover/focus;
- selected/expanded;
- loading if relevant;
- empty if relevant;
- error if relevant.

For interactive records:

- closed;
- opening/active;
- detail surface;
- closing/restored focus.

---

## 4. Required themes

Every affected visual surface must be inspected in:

- AMON Snow;
- AMON Space.

Theme correctness includes:

- contrast;
- borders;
- hierarchy;
- hover;
- focus;
- selected states;
- disabled states;
- charts.

---

## 5. Required viewports

Unless a ticket explicitly says otherwise:

### Desktop

1440 × 1000 approximate target.

### Tablet

834 × 1112 approximate target.

### Mobile

390 × 844 approximate target.

Exact device emulation is not required unless relevant.

The goal is to inspect information hierarchy across the three layout classes.

---

## 6. Visual rejection conditions

Any of these may fail Visual Acceptance even when tests are green:

- looks like a generic admin template;
- feels like an HTML form;
- feels like Excel with styling;
- feels like a static PowerPoint;
- no perceptible interaction where exploration is expected;
- excessive cards;
- excessive border nesting;
- weak hierarchy;
- poor spacing rhythm;
- inaccessible contrast;
- controls dominate the information;
- mobile feels like compressed desktop;
- Snow and Space feel like different products;
- animations distract rather than explain;
- technical implementation is exposed as UI.

---

## 7. Interaction rejection conditions

Fail Interaction Acceptance when applicable behavior is absent or misleading, including:

- chart has meaningful data but no inspectable values;
- hover has no response where hover behavior was required;
- keyboard cannot reach an equivalent state;
- row appears clickable but does nothing;
- clickable element has no useful depth;
- selection state is unclear;
- drawer loses focus;
- Escape behavior is broken;
- reduced-motion is ignored;
- the UI changes without communicating why.

---

## 8. Evidence package

Visual QA should produce, where applicable:

artifacts/visual-qa/<ticket>/

Recommended contents:

- snow-desktop-rest.png
- snow-desktop-hover.png
- snow-desktop-selected.png
- space-desktop-rest.png
- space-desktop-hover.png
- space-desktop-selected.png
- tablet.png
- mobile.png
- interaction-report.md
- console-report.txt
- trace.zip

File names may vary, but states must be obvious.

---

## 9. Human acceptance

The human reviewer may answer:

PASS

or:

FAIL — <reason>

or:

PASS WITH DEBT — <explicitly accepted debt>

Silence is not approval.

Automated green tests are not approval.

Previous approval of another surface is not approval.

---

## 10. Release requirement

Visual work must not pass the Release Gate until Human Visual Acceptance exists for the ticket.

If a visual ticket is merged without such acceptance, it must be recorded explicitly as visual debt rather than treated as completed design work.
