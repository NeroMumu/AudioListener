# UI regeneration proposal from an expert UX perspective

## 1. Diagnosis of what is currently wrong

The current interface suffers from an issue that often appears after several iterative additions: each new feature found a place, but the whole no longer forms a coherent product experience.

From the screenshot and current structure, the main issues are:

### A. Competing focal points

- the `Document de travail` should dominate clearly
- the right rail is too dense and visually heavy
- the user’s eye does not know where the primary task starts

### B. Too many card boundaries

- too many boxed regions create fragmentation
- visual hierarchy is replaced by border hierarchy
- the result feels technical rather than editorial

### C. Overflow and compression

- the right column contains too many blocks stacked at equal visual weight
- library, version, batch, transcription, and diagnostics all compete vertically
- this creates overflow and cramped controls

### D. Poor editorial ergonomics

- the workbench is supposed to be a writing and revision space
- yet the document area still feels like just one panel among many
- a real workbench should privilege text surface, not surrounding chrome

### E. Status and configuration overload

- some items that should be ambient are too visible
- some items that should be immediately accessible are too dispersed

## 2. Correct product framing

The application should not look like:

- a dashboard of utilities
- a developer console with an editor
- a transcription page plus add-ons

It should look like:

- **a writing desk for one active document**
- with a compact archive on the side
- and low-noise operational utilities around it

That means one rule:

> everything that is not the active document must visually step back.

## 3. Recommended design direction

I recommend a full regeneration around a **single editorial workspace**.

### Guiding principles

- document first
- tools second
- archive third
- diagnostics last

## 4. New information architecture

### Zone 1 — compact command header

Purpose:

- identify the app
- display global state
- expose only the most frequent quick actions

Content:

- application title
- status badge
- save state
- quick open `Output`, `Input`, `Trash`

No descriptive clutter.

### Zone 2 — workbench command bar

Purpose:

- collect all editing and transformation controls in one place

Content:

- `Mise en forme`
- `Reformulation`
- `Résumé`
- free prompt input
- `Appliquer`
- `Retour`
- `Avancer`
- `Sauvegarder`
- `Effacer`

This bar belongs directly above the document.

### Zone 3 — main editorial workspace

Purpose:

- give maximum height and width to the active document

Content:

- version strip
- document title / source context
- large editable surface

### Zone 4 — right archive rail

Purpose:

- host everything secondary but useful

Content order:

1. saved transcripts library
2. current version summary
3. batch queue

Items removed from the right rail:

- diagnostics should not always be there if they create visual noise
- transcription settings should be compacted or moved higher

### Zone 5 — bottom utility strip

Purpose:

- keep technical detail accessible without polluting the editorial space

Content:

- diagnostics log
- optional service details

This strip should be slimmer and secondary.

## 5. Recommended regenerated layout

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Journal audio                         [Statut] [Dernière sauvegarde] [Dirs] │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ [Mise en forme] [Reformulation] [x Résumé] [prompt libre..................] │
│ [Appliquer] [Retour] [Avancer] [Sauvegarder] [Effacer]                     │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┬────────────────────────┐
│ DOCUMENT DE TRAVAIL                                 │ BIBLIOTHÈQUE           │
│ Source · Version · Modèle utile                    │ transcripts saved      │
│                                                     │ active highlight       │
│ [grand éditeur très haut]                           │ update / delete        │
│                                                     │                        │
│                                                     │ VERSION COURANTE       │
│                                                     │ résumé de l’état       │
│                                                     │                        │
│                                                     │ FILE BATCH             │
│                                                     │ queue / upload         │
└─────────────────────────────────────────────────────┴────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ Diagnostics techniques                                                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 6. Visual proportions

### Desktop recommendation

- left workspace: `72%`
- right rail: `28%`

### Vertical proportions

- header: very compact
- command bar: compact but comfortable
- document zone: maximum height
- diagnostics: controlled height with internal scroll

## 7. What must disappear or shrink

### Remove or reduce

- repeated explanatory subtitles everywhere
- large informational cards above the document
- duplicate context blocks that could be expressed as one line
- multiple equal-sized panels

### Keep but compress

- Whisper model selector
- version metadata
- archive actions
- folder shortcuts

## 8. Recommended component behavior

### Document panel

- should occupy the overwhelming majority of visible height
- should never be visually interrupted by secondary cards above it

### Library panel

- compact entries
- active row very obvious
- actions always aligned right
- only one level of metadata per row

### Batch panel

- compact queue rows
- drag-and-drop zone visually lighter
- should not exceed the visual importance of the library

### Diagnostics

- visible but thin
- fixed height with internal scroll
- always anchored to bottom of page layout

## 9. Typography and spacing recommendations

### Titles

- only one strong page title
- one strong workbench title
- secondary cards use smaller headings

### Spacing

- more whitespace around document
- less whitespace around side utilities

### Borders

- fewer visible borders
- softer separators
- stronger contrast only for active states

## 10. Recommended design language

- editorial interface first
- system console second
- less “dashboard”
- more “writing studio”

Meaning:

- the editor should feel calm and central
- the archive should feel functional and subordinate
- diagnostics should feel technical and peripheral

## 11. Concrete implementation recommendations

### A. Flatten the top of the page

Current problem:

- too much vertical stack before reaching the editor

Recommendation:

- merge contextual info into one compact top bar
- move model details into the command bar or rail

### B. Rebuild the rail as two sections only

Recommended order:

1. library
2. utilities block containing version and batch

Or even:

1. library
2. tabs inside rail: `Version` / `Batch`

### C. Move diagnostics to a true footer region

Not into the right rail.

Reason:

- it increases right-rail height too much
- it steals space from archive and queue

### D. Give the editor a stable minimum viewport height

Recommendation:

- editor should target around `78vh` after chrome reduction
- not by simply inflating height, but by removing vertical waste above it

## 12. Best final recommendation

The strongest version is:

- **one compact top header**
- **one compact workbench toolbar**
- **one giant left document zone**
- **one narrow right archive rail**
- **one thin diagnostics footer**

This is the cleanest expert-level UX answer to the current overflow problem.

## 13. Expected user experience after regeneration

The user should immediately feel:

- I am editing one important document
- my tools are right above it
- my saved transcripts are neatly accessible on the side
- my batch queue is present but not invasive
- technical logs exist, but they do not own the interface

That is the right UX posture for `Document de travail`.
