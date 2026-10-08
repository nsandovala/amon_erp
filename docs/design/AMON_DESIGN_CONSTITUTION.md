# AMON Design Constitution v2

Status: AUTHORITATIVE
Owner: Human Product Direction
Applies to: AMON ERP and reusable AMON product surfaces

---

## 1. Purpose

This document defines the product-design character of AMON.

It is not a component library.
It is not a CSS guide.
It is not a collection of visual trends.

It defines how AMON must feel, behave and communicate when a human uses it.

Supporting design skills may improve execution, but they may not override this document.

When implementation convenience conflicts with this constitution, the agent must stop and request human direction.

---

## 2. Product character

AMON is:

- calm;
- precise;
- contemporary;
- operational;
- trustworthy;
- intelligent without pretending certainty;
- minimal without feeling empty;
- premium through restraint and detail;
- responsive to human intent.

AMON should feel like an instrument used to understand and operate a business.

It must not feel like:

- an HTML form with styling;
- an Excel sheet with decoration;
- a PowerPoint presentation;
- a generic admin template;
- a static BI export;
- an AI-generated SaaS landing page;
- a collection of unrelated cards.

---

## 3. Core principle

### Data must feel inspectable.

AMON does not merely display information.

When information naturally supports exploration, the interface should allow the human to inspect it through one or more of:

- hover;
- focus;
- selection;
- progressive disclosure;
- drill-down;
- contextual detail;
- related records.

A static representation of explorable data is considered incomplete unless there is a documented product reason for keeping it static.

---

## 4. Minimalism

Minimalism in AMON means reducing cognitive noise.

It does NOT mean:

- removing useful context;
- eliminating interaction;
- hiding important state;
- presenting large empty surfaces;
- replacing information hierarchy with blank space.

Every visible element must justify its presence.

Every removed element must preserve the user's ability to understand and act.

---

## 5. Premium

"Premium" is not a visual effect.

Premium in AMON comes from:

- accurate hierarchy;
- predictable behavior;
- careful spacing;
- typography discipline;
- restrained color;
- meaningful interaction;
- polished state transitions;
- correct empty states;
- clear feedback;
- absence of visual accidents.

An agent may not declare a surface "premium".

Only human visual acceptance can determine whether the result reaches the intended quality.

---

## 6. Themes

AMON has two canonical themes.

### AMON Snow

- warm matte snow-white surfaces;
- graphite typography;
- subtle warm/gold accents;
- restrained depth;
- never sterile pure white.

### AMON Space

- deep graphite / near-black surfaces;
- high-contrast light typography;
- subtle warm/gold accents;
- never gamer/neon.

Both themes represent the same product.

A feature that works visually in only one theme is incomplete.

---

## 7. Gold

Gold is an accent.

It may communicate:

- hierarchy;
- selection;
- brand identity;
- important but non-destructive emphasis.

Gold must not become:

- a dominant surface fill;
- decorative glow;
- visual noise;
- a substitute for hierarchy.

---

## 8. Information hierarchy

AMON follows progressive disclosure.

### Rest

Show the minimum information necessary to understand the current state.

### Hover / Focus

Reveal relevant context or affordance.

### Select

Reveal deeper information when useful.

### Manage

Expose controls only when the user intends to manage the object.

### Confirm

Persist consequential changes only after explicit human intent.

The interface should become deeper as intent increases.

It should not expose every possible control at all times.

---

## 9. Motion

AMON should feel alive because it responds to intent, not because it constantly moves.

Motion exists only to:

- confirm state change;
- preserve spatial continuity;
- reveal hierarchy;
- connect cause and effect;
- explain where content came from or where it went.

Motion must not exist merely to decorate.

Typical interaction duration:

120–220 ms.

Reduced-motion preferences must be respected.

Avoid:

- looping decorative animation;
- gratuitous parallax;
- bouncing UI;
- excessive transforms;
- motion that delays work.

---

## 10. Surface philosophy

Primary operational surfaces remain solid and readable.

Glass may be used only for:

- transient overlays;
- drawers;
- popovers;
- floating controls;
- temporary contextual surfaces.

Do not solve hierarchy by nesting cards inside cards indefinitely.

Do not solve hierarchy by adding more borders.

Structure must come from:

- spacing;
- typography;
- grouping;
- alignment;
- contrast;
- behavior.

---

## 11. Charts

Charts are operational instruments.

Do not choose a chart because it looks attractive.

Charts must:

- communicate a useful relationship;
- expose detail when explored;
- preserve readable values;
- support keyboard-equivalent interaction when practical;
- maintain theme contrast.

A chart that contains explorable financial information but provides no useful interaction should be considered incomplete unless explicitly justified.

Doughnut charts are reserved for parts-of-a-whole relationships.

---

## 12. Tables and records

Tables must not feel like exported spreadsheets.

Rows should behave as records, not inert text.

When meaningful, records should support:

- hover/focus affordance;
- contextual detail;
- progressive actions;
- drill-down.

Permanent rows of edit/delete/action controls should be avoided when those controls can live in a contextual management surface.

---

## 13. Forms

Forms are tools, not the visual identity of AMON.

Operational pages should not default to "form first" presentation when the normal user intent is to read, understand or inspect.

Prefer:

view
→ inspect
→ manage
→ edit

over:

open page
→ immediately see every editable field.

---

## 14. Smart behavior

AMON may reduce the distance between unstructured human input and structured business information.

The design principle is:

> The human provides imperfect input.
> AMON organizes it.
> The human validates the result.
> Only then does it become business truth.

AMON must never disguise uncertainty as certainty.

When inference is involved, the interface must make review possible before consequential persistence.

---

## 15. Error philosophy

Do not expose raw backend, database, provider or infrastructure details as primary UI.

Errors should answer:

1. What happened?
2. What is affected?
3. What can the user do next?

Technical details belong in diagnostics, logs or expandable technical context where appropriate.

---

## 16. Empty states

Never show a bare "No data".

An empty state must explain:

- what is absent;
- whether that is normal;
- what the user can do;
- or what will appear there later.

---

## 17. Responsive design

Desktop, tablet and mobile are not scaled copies of one another.

The same information hierarchy must survive across them.

Desktop may use drawers and multi-column analysis.

Mobile may transform contextual surfaces into bottom sheets or focused full-height views.

No essential action may disappear merely because the viewport is smaller.

---

## 18. Accessibility

Accessibility is part of product quality.

Required considerations include:

- keyboard navigation;
- visible focus;
- meaningful labels;
- contrast;
- reduced motion;
- semantic roles;
- equivalent interaction paths.

Hover-only functionality is prohibited when the same information is needed to operate the product.

---

## 19. Patterns explicitly rejected

Unless specifically approved:

- purple/blue AI gradients;
- neon/glowing borders;
- generic SaaS hero styling;
- enormous border radius everywhere;
- random glassmorphism;
- excessive shadows;
- excessive card nesting;
- decorative dashboards;
- icon-only actions without sufficient clarity;
- permanent edit controls everywhere;
- template-looking admin dashboards;
- marketing visuals inside operational workflows;
- animation without informational purpose.

---

## 20. Design authority

Order of authority:

1. Explicit human product direction.
2. This Constitution.
3. AMON Interaction Language.
4. AMON Visual Acceptance rules.
5. Repository-specific product requirements.
6. Supporting design skills.
7. Generic framework conventions.

A lower layer may never silently override a higher one.

If there is conflict or ambiguity, stop and ask.

---

## 21. Definition of visually complete

Automated tests do not prove visual quality.

A visual feature is complete only after:

- functional QA passes;
- interaction QA passes;
- accessibility checks pass;
- responsive checks pass;
- Snow and Space are inspected;
- human visual acceptance is explicitly given.

Until then the correct state is:

READY FOR HUMAN VISUAL ACCEPTANCE

not:

DONE
PREMIUM
APPROVED
