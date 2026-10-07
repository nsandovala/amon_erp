---
name: amon-design
description: Canonical product design language for AMON applications. Use for any UI, UX, frontend, dashboard, admin, auth, form, table, navigation, responsive, visual polish, or interaction work in AMON products.
---

# AMON Design Language

AMON Design is the visual and interaction authority for AMON products.

External design skills may advise and improve execution, but they must not override this document.

## 1. Product character

AMON must feel:

- premium;
- calm;
- precise;
- modern;
- technological;
- trustworthy;
- intentional.

Reference quality:
Apple-class product discipline, not imitation of Apple.

The interface must feel designed as a product, never as:
- an HTML form;
- an admin template;
- a generic SaaS dashboard;
- an AI-generated landing page.

## 2. Core principles

### Information before decoration

The user must understand:
1. where they are;
2. what matters;
3. what requires attention;
4. what they can do next.

Visual decoration must never compete with business information.

### View first, edit second

Default state:
information.

Editing controls appear only when the user explicitly chooses to edit.

Avoid permanent visible:
- inputs;
- selects;
- destructive buttons;
- configuration controls.

### Progressive disclosure

Secondary and technical information stays hidden until required.

Examples:
- technical IDs;
- advanced settings;
- destructive actions;
- role controls;
- infrastructure details.

### Reduce cognitive noise

Prefer fewer stronger elements over many equal cards.

Use hierarchy through:
- typography;
- spacing;
- grouping;
- alignment;
- contrast.

Do not solve hierarchy by adding more borders.

## 3. AMON visual identity

### AMON Snow

Primary:
- snow white matte surfaces;
- graphite text;
- subtle warm/gold accents;
- soft neutral separators.

Snow is not pure sterile white.
It must feel warm, premium and quiet.

### AMON Space

Primary:
- deep graphite / near-black;
- dark blue-black surfaces where useful;
- high-contrast light typography;
- subtle gold accents;
- restrained cool highlights.

Avoid gamer/neon styling.

### Gold

Gold is an accent, not a fill color.

Use for:
- selected context;
- premium emphasis;
- section eyebrow;
- subtle active state.

Never flood large surfaces with gold.

## 4. Glass

Glass is allowed only for:
- floating controls;
- overlays;
- context selectors;
- transient surfaces;
- lightweight navigation layers.

Do not make every card glass.

Primary ERP information surfaces should remain solid and readable.

## 5. Typography

Typography must establish clear hierarchy.

Prefer:
- strong page title;
- compact section eyebrow;
- readable body;
- restrained metadata;
- tabular numerals where financial data benefits.

Financial figures must be highly scannable.

Avoid:
- excessive uppercase;
- huge marketing typography inside operational screens;
- too many font weights.

## 6. ERP-specific rules

AMON ERP should feel like a business cockpit.

Prioritize:
- current state;
- exceptions;
- trends;
- decisions;
- traceability.

Dashboards should tell a business story, not display a collection of widgets.

Tables:
- dense enough for professional work;
- never cramped;
- align numerical data consistently;
- preserve scan paths.

Forms:
- only visible while creating/editing;
- labels remain explicit;
- error states must explain recovery.

Administration:
- view-first;
- actions secondary;
- technical data tertiary.

## 7. Cards and surfaces

Do not default to cards for every concept.

Use cards when they create meaningful grouping.

Avoid:
- card-inside-card-inside-card;
- repeated rounded containers with equal visual weight;
- excessive borders.

Prefer whitespace and layout first.

## 8. Charts

Charts must answer a question.

Use:
- line/bar for comparison and trend;
- doughnut only for parts of a whole;
- progress only when a meaningful target exists.

Never choose a chart only because it looks attractive.

Always include:
- accessible labels;
- readable values;
- graceful empty states;
- responsive behavior.

## 9. Motion

Motion communicates state.

Typical duration:
120–220 ms.

Longer transitions only when they genuinely communicate system progress.

Never delay the user only to show animation.

Required:
prefers-reduced-motion support.

Good uses:
- panel transition;
- progressive disclosure;
- state confirmation;
- authentication verification;
- context switching.

Avoid:
- gratuitous floating;
- looping animation;
- excessive parallax;
- decorative motion in ERP workflows.

## 10. Interaction quality

Every interaction must have a clear:
- default;
- hover;
- focus;
- active;
- disabled;
- loading;
- error state.

Keyboard navigation must remain functional where applicable.

Focus should not create unwanted scrolling.

## 11. Responsive behavior

Always validate at minimum:

- desktop ~1440px;
- tablet;
- mobile ~375px.

Responsive design means reprioritization, not simply shrinking desktop UI.

Avoid horizontal scrolling unless the domain genuinely requires a data table.

## 12. Empty states

Empty states must explain:

- what is empty;
- why it matters;
- what the user can do next.

Avoid generic:
"No data."

Prefer:
"No hay ventas en el período."
"Registra una venta o selecciona otro período."

## 13. Error and attention states

Use restrained semantic states.

Errors:
clear, actionable, human-readable.

Warnings:
explain risk without creating alarm fatigue.

Never expose raw backend errors, IDs or infrastructure information as primary UI.

## 14. Forbidden generic patterns

Avoid unless explicitly justified:

- purple/blue AI gradients;
- generic SaaS hero styling;
- glowing neon borders;
- enormous border-radius everywhere;
- random glassmorphism;
- excessive shadows;
- excessive cards;
- icon-only actions without clarity;
- permanent edit controls;
- template-looking dashboards;
- marketing visuals inside operational workflows.

## 15. Design workflow

For every visual ticket:

1. Read this skill.
2. Inspect the existing product before proposing change.
3. Preserve the current AMON design language unless a redesign is explicitly requested.
4. Consult ui-styling and design-system for execution quality.
5. Consult ui-ux-pro-max for relevant UX/layout/accessibility/chart patterns.
6. Consult brand/design only when the task materially benefits from them.
7. State which generic patterns will be avoided.
8. Implement the smallest coherent change.
9. Validate Snow and Space.
10. Validate desktop, tablet and mobile.
11. Validate empty/error/loading states.
12. Validate keyboard and reduced-motion behavior.

## 16. Authority rule

A design skill may propose improvements.

It may NOT:
- reduce approved scope;
- remove requested UX;
- replace product requirements;
- redesign unrelated surfaces;
- introduce a new visual language;

without explicit human approval.

Human product direction is authoritative.
