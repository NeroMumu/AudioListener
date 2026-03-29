# Zero-based UI concept proposal

## 1. Start from zero

Forget the current interface entirely.

Do not think in terms of:

- where to move existing cards
- how to compress the current header
- how to salvage the current layout

Those questions come too late.

The right question is:

> what is this product actually for, and what should the interface feel like if designed cleanly from scratch

## 2. Product purpose

This application is not mainly:

- a dashboard
- a log viewer
- a systray mirror
- a collection of widgets

It is mainly:

- a **document production tool**
- fed by transcription sources
- enriched by transformations
- backed by an archive

So the conceptual metaphor should not be `control center`.

It should be:

## 3. Core metaphor

### `Desk + stack + utility drawer`

The cleanest expert concept is:

- a **desk** for the active document
- a **stack** of saved transcripts on the side
- a **utility drawer** for queue and diagnostics

This is much more natural than the current multi-panel dashboard logic.

## 4. Essential jobs the UI must support

If we design from zero, the interface only needs to support five essential jobs.

### Job 1 — open or receive a transcript

The user must be able to:

- load an existing transcript
- receive a batch result
- receive a live result

### Job 2 — work on one active document

The user must be able to:

- read
- edit
- format
- reformulate
- prompt-transform
- add/remove summary

### Job 3 — navigate states of that document

The user must be able to:

- undo
- redo
- understand what version is visible

### Job 4 — persist or manage archived files

The user must be able to:

- save current work
- update current transcript file
- delete a transcript file

### Job 5 — stay aware of background processing without losing focus

The user must be able to:

- know if batch is running
- know if live is running
- inspect logs if needed

But these background concerns must remain secondary.

## 5. Therefore: the correct product structure

From those jobs, the product should be split into only three conceptual areas.

### Area A — The active document desk

This is the main screen.

Contains:

- active document title or source name
- transform toolbar
- editable document
- version navigation

This area must dominate the screen.

### Area B — The archive stack

This is the saved transcript list.

Contains:

- saved transcripts
- active item highlight
- update current file action
- delete file action

This area is not a workspace. It is navigation and file management.

### Area C — The utility drawer

Contains:

- batch queue
- transcription config
- diagnostics

This area must not compete visually with the active document.

## 6. Recommended screen concept

### Concept: `Single document studio`

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Journal audio                          [status] [save state] [quick actions]│
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ Active document toolbar                                                     │
│ [Mise en forme] [Reformulation] [x Résumé] [prompt libre.................]  │
│ [Appliquer] [Retour] [Avancer] [Sauvegarder] [Effacer]                     │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┬───────────────────────┐
│ ACTIVE DOCUMENT DESK                                │ ARCHIVE STACK          │
│                                                      │                       │
│ [very large document editor]                         │ saved transcripts      │
│                                                      │ active file            │
│                                                      │ update/delete          │
└──────────────────────────────────────────────────────┴───────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ Utility drawer                                                              │
│ batch queue · transcription config · diagnostics                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 7. Why this is better than a right-rail-only design

Because the current problems show that the utility blocks are too numerous and too tall to sit permanently as first-class right-side content.

If everything stays visible in one right rail, the interface tends to:

- overflow vertically
- fragment attention
- reduce the main document height

A true zero-based solution accepts this:

> not all secondary widgets deserve persistent equal visibility

## 8. Recommended visibility hierarchy

### Always visible

- active document toolbar
- active document editor
- saved transcript list

### Visible but compact

- status
- save state
- version indicator

### Secondary, grouped together

- batch queue
- transcription config
- diagnostics

## 9. Proposed UI composition from scratch

### Top strip

A single thin strip containing:

- app title
- live state badge
- save state
- Output / Input / Trash

Very compact.

### Toolbar strip

Immediately under the title strip.

Contains all document actions.

This strip is wide and horizontal.

### Main body split

Only two columns:

- left: active document
- right: archive stack

No batch queue there.
No diagnostics there.

### Bottom drawer

One horizontal band below the main body.

Contains tabs or stacked compact sections:

- `Batch`
- `Transcription`
- `Diagnostics`

This is the correct place for system-level widgets.

## 10. Key conceptual decision

### The archive stays right

The transcript library belongs on the side because it directly changes the active document.

### The system tools go down

Batch, transcription settings, and diagnostics are support systems.

They should not live at the same editorial level as the archive.

This is probably the most important correction to prior attempts.

## 11. Resulting proportions

### Desktop

- left document desk: `78%`
- right archive stack: `22%`

### Bottom drawer height

- compact by default
- expandable internally by scroll

### Main editor height

- should visually dominate the screen
- should receive the maximum remaining viewport height

## 12. Interaction model

### Opening a transcript

- right archive stack
- click loads it into active document desk

### Working the transcript

- all transformations happen in the toolbar above the editor

### Inspecting batch and logs

- done in the bottom utility drawer

This separation is cognitively much cleaner.

## 13. What must disappear from the current mental model

The following must be dropped conceptually:

- many stacked equal cards in the right rail
- diagnostics mixed with archive
- transcription settings mixed with version state
- page as a grid of peer widgets

## 14. Expert recommendation

If rebuilding from zero, the best design is:

### `Document studio + archive rail + utility drawer`

Not:

- dashboard
- console
- right rail overloaded with every feature

## 15. Visual direction

The concept should also change visual tone, not only layout.

### Selected color direction

- softer, premium dark palette
- deep slate background
- warm off-white text
- subtle teal accent
- lower-contrast borders

### Intended effect

- calmer and more editorial
- less aggressive than a typical developer dashboard
- more comfortable for long reading and rewriting sessions

### Visual principles

- document area slightly lighter than page background
- right rail and utility drawer visually quieter than the document
- accent used mostly for focus, active states, and main actions
- borders should separate, not dominate

### What to avoid

- high-contrast neon cyan everywhere
- heavy glowing borders
- overly segmented card stacks with equally strong outlines
- harsh pure white text on every surface

## 16. Final recommendation

The interface should now be rebuilt conceptually as:

- **Top**: compact status and quick actions
- **Middle-left**: huge active document desk
- **Middle-right**: transcript archive only
- **Bottom**: batch + transcription config + diagnostics

This is the strongest clean-slate UX structure for your product.
