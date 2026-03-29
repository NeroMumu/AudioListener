# UI redesign proposal for Document de travail

## 1. Diagnosis of the current UI

The current interface has accumulated several powerful features, but the visual structure is no longer optimal for intensive editing.

Main pain points:

- the page still reads like an old transcription app with features bolted on
- the `Document de travail` concept is stronger than the current layout suggests
- transcript library, batch queue, transformations, status, and logs compete for attention
- the most important action, editing the current working document, is not dominant enough
- the right column mixes persistent assets and transient context

In short, the UI has good features but weak information hierarchy.

## 2. New design objective

Turn the app into a **real transcript workbench**.

The experience should feel like:

- one main editable document
- one focused transformation toolbar
- one asset rail for saved transcripts and queue state
- one low-noise monitoring layer for logs and system status

## 3. Recommended information architecture

### Layer 1 — command header

Persistent top strip for:

- global status
- selected Whisper model
- selected Ollama model
- save status
- quick open actions for `Input`, `Output`, `Trash`

### Layer 2 — workbench toolbar

Main command bar directly attached to the working document:

- `Mise en forme`
- `Reformulation`
- `Résumé` checkbox
- custom prompt field
- `Appliquer`
- `Retour`
- `Avancer`
- `Sauvegarder`
- `Effacer`

### Layer 3 — central workspace

Two-column layout:

- **left large column**: working document
- **right narrow column**: library and queue

### Layer 4 — secondary diagnostics

- logs
- technical status
- service health

Collapsed by default or visually secondary.

## 4. Recommended layout option

### Option A — Focused workbench with right rail

This is the recommended option.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Header: status · whisper · ollama · save state · open input/output/trash   │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ Toolbar: [Mise en forme] [Reformulation] [x Résumé] [prompt libre......]   │
│          [Appliquer] [Retour] [Avancer] [Sauvegarder] [Effacer]             │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────┬───────────────────────────────┐
│ DOCUMENT DE TRAVAIL                          │ RAIL LATÉRAL                  │
│ Version actuelle · fichier source            │                               │
│                                              │ Transcriptions enregistrées   │
│ [éditeur principal très grand]               │ [liste cliquable]             │
│                                              │ [mise à jour] [poubelle]      │
│                                              │                               │
│                                              │ File batch                    │
│                                              │ [en file / traitement / fini] │
└──────────────────────────────────────────────┴───────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ Logs et détails techniques                                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

Why this is best:

- the editable document becomes the obvious center of gravity
- the transcript library remains visible without stealing focus
- batch processing is visible but does not interrupt writing
- the transformation controls feel attached to the document they modify

## 5. Alternative layout option

### Option B — Three-panel production desk

```text
┌──────────────────────┬──────────────────────────────┬──────────────────────────┐
│ Library              │ Working document             │ Queue and status         │
│                      │                              │                          │
│ transcripts          │ large editor                 │ batch queue              │
│ versions             │ toolbar above                │ logs summary             │
│ actions              │ version strip                │ services                 │
└──────────────────────┴──────────────────────────────┴──────────────────────────┘
```

Why I do not recommend it first:

- denser
- more visually fragmented
- weaker focus on the current document

## 6. Recommended sizing and proportions

For desktop:

- left workbench column: `68%`
- right rail: `32%`

Within the right rail:

- top half: transcript library
- bottom half: batch queue and system cards

For smaller screens:

- toolbar wraps
- right rail moves below the workbench
- logs stay collapsed by default

## 7. Key UX principles

### A. The document is the product

The main editor must dominate visually.

This means:

- largest area
- highest contrast
- clear version label above it
- no competing result panel

### B. Actions must be attached to intent

`Mise en forme`, `Reformulation`, `Résumé`, and custom prompt must sit directly above the editor, not elsewhere.

### C. Saved transcripts are assets, not outputs

The transcript library should feel like a navigation rail, not a second workspace.

### D. Status should be ambient

Batch state and technical status should remain available but discreet.

## 8. Proposed component breakdown

### Header bar

- app title
- current system status badge
- selected Whisper model
- selected Ollama model
- last save info
- quick open buttons

### Workbench toolbar

- formatting controls
- prompt control
- history navigation
- save and clear actions

### Workbench panel

- source file name
- version name
- current version index
- large editor

### Transcript rail

- list of saved transcripts
- active highlight
- update button for active transcript
- trash button on every row

### Batch rail block

- drop zone
- queued items
- current processing item
- completion and failure badges

### Diagnostics drawer

- logs
- service state
- optional metrics

## 9. Interaction model

### Loading a transcript

- click on transcript in right rail
- it becomes active
- row is highlighted
- workbench resets to source version

### Applying a transformation

- click `Mise en forme` or `Reformulation`
- current workbench content is transformed
- a new version is pushed
- version label updates

### Using custom prompt

- user writes instruction
- clicks `Appliquer`
- result becomes next version

### Undo and redo

- `Retour` moves backward in version history
- `Avancer` moves forward
- version strip always shows the current position

### Updating a saved transcript

- available only on active transcript row
- writes the current editor content back to file

### Deleting a transcript

- trash icon on row
- deletes file
- if active, selection is cleared but editor may remain as transient working text

### Batch completion

- batch transcript may auto-load or surface a notification depending on final rule
- visually, the queue item should clearly indicate completion

## 10. Visual priorities

### Priority 1

- large workbench editor
- clearer toolbar
- stronger active transcript highlight

### Priority 2

- structured right rail
- transcript library separated from queue

### Priority 3

- logs converted into a real collapsible diagnostics drawer

## 11. Suggested style direction

- keep dark theme
- reduce card noise
- increase spacing around the main editor
- unify button styles by intent
  - primary transformation
  - neutral navigation
  - destructive delete
- make the active transcript row visually obvious
- make the batch queue more compact and status-oriented

## 12. Proposed implementation strategy

### Step 1

Refactor [`static/index.html`](../static/index.html) into three zones:

- top header
- workbench area
- right rail

### Step 2

Refactor [`static/styles.css`](../static/styles.css) around a clear layout system:

- page shell
- toolbar shell
- workbench shell
- right rail shell
- diagnostics drawer

### Step 3

Adapt [`static/app.js`](../static/app.js) selectors to the new structure without changing core logic first.

### Step 4

Only after layout stabilization, improve microinteractions:

- active row animation
- dirty badge
- compact queue items
- explicit version strip

## 13. Recommended direction

Implement **Option A — Focused workbench with right rail**.

It gives the best balance between:

- readability
- editing comfort
- transcript management
- batch visibility
- technical clarity

## 14. Expected result

After the redesign, the application should feel like:

- a writing desk for one evolving document
- with a visible transcript archive
- a nearby batch queue
- and low-friction transformation tools

That is the right UX framing for `Document de travail`.
