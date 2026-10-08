# AMON Interaction Language

Status: AUTHORITATIVE SUPPORTING SPEC
Parent authority: AMON Design Constitution v2

---

## 1. Principle

AMON should reveal depth progressively.

The product should respond to human intent without turning every surface into a button.

General model:

REST
→ HOVER / FOCUS
→ SELECT
→ INSPECT
→ MANAGE
→ CONFIRM

Not every object requires every state.

When a state is omitted, the decision should be intentional.

---

## 2. KPI

### Rest

Show:

- metric name;
- primary value;
- essential comparison or context.

### Hover / Focus

When useful, expose:

- comparison basis;
- explanation;
- secondary context.

### Select

If meaningful, reveal deeper information such as:

- current period;
- previous period;
- absolute difference;
- relative difference;
- contributing records;
- trend.

Do not make KPIs clickable without meaningful depth.

---

## 3. Analytical chart

### Rest

Communicate the global pattern clearly.

### Hover / Focus

Highlight the datum being inspected.

Show contextual information relevant to the graph.

For financial comparisons this may include:

- date / period;
- income;
- expense;
- result;
- variance.

Avoid generic framework tooltips when an AMON contextual surface can communicate the information better.

### Select

When useful:

- persist the selected point/segment;
- de-emphasize unrelated data;
- reveal related information.

### Drill-down

Where business records exist behind a point, selection may expose those records.

---

## 4. Doughnut / composition chart

### Rest

Show the overall composition.

### Hover / Focus

- emphasize the active segment;
- reduce emphasis of non-active segments;
- update contextual text;
- expose label, amount and share.

When a center area exists, prefer using it for contextual information rather than leaving it permanently decorative.

### Leave / Blur

Restore total/default state.

### Select

Where meaningful, allow persistent selection and related record inspection.

---

## 5. Financial record row

### Rest

Readable record with the essential fields.

### Hover

Provide subtle affordance.

The row should feel inspectable, not animated for decoration.

### Focus

Visible focus equivalent to hover intent.

### Select

Open contextual record detail when meaningful.

Avoid showing every secondary action permanently in the row.

---

## 6. Detail Drawer

Use when the human should inspect something without losing the surrounding context.

### Desktop

Prefer side drawer.

### Mobile

Prefer bottom sheet or focused full-height surface depending on information density.

Required behavior:

- visible title;
- explicit close;
- Escape closes;
- backdrop closes only when safe;
- focus moves into the surface;
- focus returns to invoker on close;
- background interaction is blocked while modal;
- reduced-motion supported.

A drawer should not become a second full application inside the current page.

---

## 7. Popover

Use for small contextual information or actions.

Do not use a popover when:

- the content requires scrolling;
- the user is editing a complex record;
- the task needs substantial context.

Use a drawer or dedicated page instead.

---

## 8. Forms

### View state

Prefer formatted information.

### Manage state

Expose edit controls after explicit intent.

### Save

Communicate success without disorienting navigation.

### Error

Keep the human in the context where correction is possible.

---

## 9. Destructive action

A destructive action must never become easier merely for visual simplicity.

Required:

- explicit intent;
- clear object identity;
- clear consequence;
- appropriate confirmation.

Soft-delete/restoration semantics must remain consistent with ERP domain rules.

---

## 10. Smart Input

Smart Input is an ingestion mode, not necessarily a separate module.

Canonical states:

### IDLE

Offer a calm entry surface.

Possible inputs:

- text;
- paste;
- TXT;
- CSV;
- PDF;
- image;
- external event.

### INGESTING

Communicate that input was received.

### UNDERSTANDING

Communicate progress while parsing/classifying.

Do not imply certainty before classification is complete.

### REVIEW

Present normalized draft records.

Show:

- interpreted type;
- values;
- warnings;
- ambiguity;
- confidence when useful;
- source relationship.

### CORRECT

Allow the human to fix interpretation.

### CONFIRM

Human explicitly decides what becomes ERP truth.

### COMMITTED

Confirm successful persistence and preserve traceability.

---

## 11. Loading

Loading must preserve context.

Avoid replacing an entire operational surface with a blank spinner when partial continuity can be retained.

Prefer:

- inline progress;
- skeleton where useful;
- state-specific copy.

---

## 12. Success

Success feedback should be:

- immediate;
- concise;
- located near the action or resulting state.

Avoid celebratory animation for routine financial operations.

---

## 13. Error

Errors must communicate:

- what failed;
- what was preserved;
- what the human should do next.

Never silently discard human input.

---

## 14. Theme behavior

Interaction states must work in both Snow and Space.

Do not implement hover/focus exclusively through subtle color changes that disappear in one theme.

---

## 15. Motion

Default transition range:

120–220 ms.

Motion should favor:

- opacity;
- subtle transform;
- spatial continuity.

Avoid:

- large travel distances;
- spring/bounce defaults;
- decorative looping motion.

---

## 16. Interaction completeness

For every interactive surface, implementation notes should explicitly answer:

- What happens at rest?
- What happens on hover?
- What happens on keyboard focus?
- What happens on click/select?
- What happens on Escape?
- What happens on mobile?
- What happens with reduced motion?
- What happens when there is no data?
- What happens on error?
