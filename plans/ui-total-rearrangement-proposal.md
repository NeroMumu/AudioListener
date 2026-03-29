# Total interface rearrangement proposal

## 1. Target you asked for

The new interface should be built around three very clear zones:

- a **large main work area** for the transcript and document editing
- a **right-side utility rail** for the secondary widgets
- a **bottom status strip** for status and diagnostics

This is the right direction.

It matches a professional editorial tool much better than the current stacked-card approach.

## 2. Core design principle

The application must feel like a **document workstation**, not a page of panels.

That means:

- the text is the product
- the right column supports the product
- the bottom strip informs the product

So the layout rule becomes:

> left = work
> right = support
> bottom = status

## 3. Recommended master layout

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Compact header: app name · start/save/clear · quick folders · models       │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┬────────────────────────┐
│ DOCUMENT DE TRAVAIL                                 │ RIGHT RAIL             │
│                                                     │                        │
│ Toolbar: mise en forme · reformulation · résumé     │ Transcript library     │
│         prompt libre · appliquer · undo · redo      │ Current version        │
│                                                     │ Batch queue            │
│ [very tall editable document zone]                  │ Transcription config   │
│                                                     │                        │
└─────────────────────────────────────────────────────┴────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ Bottom status strip: feedback · logs · technical diagnostics               │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 4. Strong UI recommendation

### A. Merge header and command bar logic

Instead of a decorative header and then another command band, use a **single compact top strip**.

This strip should contain:

- app title
- status badge
- start
- save
- clear
- output/input/trash shortcuts
- Whisper selector
- compact Ollama status text

Why:

- less vertical waste
- faster scanning
- more room for the workbench

## 5. Main work area

### Left zone should be very large

The left zone should consume most of the width.

Recommended proportion:

- `74%` left
- `26%` right

### The editor should be the dominant surface

The editor must:

- be visually calm
- start high on the page
- be tall without overflowing
- have internal scrolling only

Recommended rule:

- fixed viewport-based height with internal scroll
- avoid page-level vertical bloat above it

## 6. Right rail structure

The right side should not be a random pile of equal blocks.

It should be structured in this order:

### 1. Transcriptions enregistrées

- highest-value side widget
- because it changes the working document

### 2. Version courante

- small contextual block
- not too tall
- should summarize version info and active state

### 3. File batch

- medium-size operational block
- enough height to monitor queue
- not oversized

### 4. Transcription config

- compact, almost utility-like
- should be the smallest rail block

## 7. Bottom strip

### What goes there

- feedback line
- diagnostics
- optional service state

### What should not happen

- diagnostics must not compete with the library or the workbench
- diagnostics should not sit mid-page

### Recommended behavior

- fixed-height bottom area
- internal scroll
- always visible
- low visual prominence

This is the right place for logs and state.

## 8. Proposed visual hierarchy

### Primary

- `Document de travail`
- toolbar directly attached to it

### Secondary

- transcript library
- batch queue

### Tertiary

- version metadata
- transcription config
- diagnostics

If everything is equally boxed and equally large, the UX fails.

## 9. Concrete component proposal

### Top strip

- left: title + status
- center: start/save/clear
- right: record audio + Output/Input/Trash + model selector

This top strip should be one horizontal operational row.

### Workbench toolbar

Place immediately above editor:

- `Mise en forme`
- `Reformulation`
- `Résumé`
- prompt field
- `Appliquer`
- `Retour`
- `Avancer`

The toolbar must remain visually linked to the document, not floating elsewhere.

### Editor area

- most height on the page
- one large scrollable writing area
- no extra decorative cards above it

### Right rail widgets

Each rail widget should be:

- compact
- consistent
- fixed-purpose
- visually lighter than the editor

## 10. Overflow prevention rules

### Rule 1

The page should not scroll because of stacked widgets unless content is genuinely long.

### Rule 2

The editor, library, batch queue, and diagnostics should each scroll internally.

### Rule 3

Right rail widgets should have max-heights.

Suggested:

- library: medium scroll panel
- batch queue: medium scroll panel
- diagnostics: short scroll panel in footer

## 11. Proposed expert arrangement in practical terms

### Top

- one compact control bar only

### Middle left

- huge document zone

### Middle right

- three or four small stacked utilities

### Bottom

- thin persistent status/diagnostics strip

This is the strongest answer to your current UX issue.

## 12. Important correction to prior attempts

Previous attempts overused cards and moved too many blocks around without reducing complexity.

The corrected approach is:

- simplify first
- compress the top
- enlarge the editor
- subordinate the rail
- isolate diagnostics at the bottom

## 13. Recommendation for implementation

I recommend the following implementation sequence:

1. rebuild [`static/index.html`](../static/index.html) around this exact layout
2. rebuild [`static/styles.css`](../static/styles.css) from scratch for this composition
3. adapt [`static/app.js`](../static/app.js) only after the DOM is stable

This avoids the current problem of incremental UI drift.

## 14. Final recommendation

The best expert-level arrangement is:

- **one compact top control strip**
- **one dominant left document panel**
- **one narrow right support rail**
- **one thin bottom status/diagnostics strip**

This is the cleanest, most legible, and most scalable structure for your app.
