# Unified transcript workbench proposal

## 1. Goal

Replace the split model where:

- one panel shows the transcription
- another panel shows the AI result

with a **single workbench panel** that always displays the current working document.

The user can then apply transformations on that document and move backward or forward through versions.

## 2. Why this is better than automatic paragraph reconstruction alone

Your feedback is important: a deterministic paragraphing algorithm alone is not enough because the real need is broader.

The real need is:

- one canonical text panel
- several transformation tools above it
- reversible history
- the ability to try a formatting or reformulation pass without losing the previous state

So the correct abstraction is not just `paragraph reconstruction`.

It is a **versioned transcript workbench**.

## 3. Recommended UX model

### One main panel only

Keep a single main editor panel that always shows the **current document version**.

This panel can display:

- raw transcript
- paragraph-formatted transcript
- reformulated transcript
- transcript prefixed with summary
- transcript transformed by a free custom prompt

The panel is therefore not `transcription` or `AI result`.

It is the **current working text**.

## 4. Top toolbar actions

Recommended controls above the main panel:

- `Reformulation`
- `Mise en forme`
- checkbox `Résumé`
- free prompt line
- `Appliquer`
- `Retour`
- `Avancer`
- optional `Réinitialiser à la transcription source`

### Meaning of each action

#### [`Reformulation`](../static/index.html)

- asks the AI to rewrite the current or source transcript in a cleaner written form

#### [`Mise en forme`](../static/index.html)

- does **not** mean heavy rewriting
- it means turning the source transcript into readable paragraphs with minimal semantic change
- this can be AI-assisted or deterministic

#### `Résumé` checkbox

- if checked, prepend a summary block before the main transcript result
- this should be applied on the produced version, not replace the transcript itself

#### Free prompt line

- custom transformation request
- example:
  - simplify
  - make more formal
  - remove repetitions
  - rewrite as a complaint letter

#### `Retour` and `Avancer`

- navigate the version stack
- exactly like undo and redo on generated document states

## 5. Core architectural idea

### Source document vs derived versions

The important design decision is to separate:

- **source transcript**
- **derived versions**

#### Source transcript

Immutable base text produced by live or batch transcription.

This is the anchor version.

#### Derived versions

Each transformation creates a new version:

- formatted
- reformulated
- summary+formatted
- custom prompt result

This means the user can always return to the original transcript.

## 6. Recommended version model

Each transcript loaded into the workbench should maintain:

- `document_id`
- `source_content`
- `current_version_index`
- `versions[]`

Each version object should contain:

- `version_id`
- `parent_version_id`
- `created_at`
- `operation_type`
- `operation_label`
- `include_summary`
- `prompt`
- `content`

### Example version chain

```text
v0 source transcript
v1 mise en forme
v2 reformulation of v1
v3 reformulation of v1 + summary
```

If the user goes back from `v2` to `v1`, then applies a new custom prompt, the redo branch after `v2` should be discarded for a simple first version.

That is standard editor behavior.

## 7. Three possible solution options

### Option A — fully deterministic formatting, AI only for reformulation

#### Behavior

- `Mise en forme` uses local deterministic paragraphing rules
- `Reformulation` uses AI
- `Résumé` uses AI only when checked
- custom prompt uses AI

#### Advantages

- fast
- stable
- no hallucination for formatting
- preserves fidelity of transcription

#### Limits

- paragraph quality may remain weaker than a good LLM on messy oral speech

### Option B — AI for mise en forme and reformulation, but with versioning

#### Behavior

- `Mise en forme` is an AI call with a strict prompt: preserve meaning, only structure and punctuation
- `Reformulation` is an AI call with a freer prompt
- all outputs are versioned

#### Advantages

- highest readability potential
- handles long oral monologues better

#### Limits

- slower
- possible drift from original wording
- depends more on model quality

### Option C — hybrid recommended solution

#### Behavior

- `Mise en forme` has two internal steps
  - first deterministic cleanup and paragraph segmentation
  - optional AI refinement pass if needed
- `Reformulation` is pure AI
- summary prepend is separate and optional
- all states are versioned

#### Advantages

- best balance between fidelity and readability
- robust on poor transcripts
- future-proof

#### Limits

- slightly more complex to implement

## 8. Recommended solution

I recommend **Option C simplified**.

### First implementation target

#### `Mise en forme`

- AI-assisted but with a strict prompt
- goal: punctuation, paragraphing, readability
- constraint: do not invent, do not summarize, do not omit

Reason:

- your example shows that the LLM is already good at turning a raw oral block into readable paragraphs
- trying to fully emulate that with deterministic rules only will likely remain below your expectation

#### `Reformulation`

- separate AI action
- more freedom in style

#### `Résumé`

- if checked, prepend a summary block before the transformed text

#### Free prompt

- applied to the current visible version or optionally the source transcript depending on chosen mode

## 9. Very important prompt distinction

To prevent confusion, `Mise en forme` and `Reformulation` must have different prompts.

### Prompt for `Mise en forme`

Strict prompt intent:

- preserve wording as much as possible
- restore punctuation
- split into readable paragraphs
- light grammar cleanup allowed
- no summary
- no shortening
- no adding information

### Prompt for `Reformulation`

Freer prompt intent:

- rewrite more cleanly
- improve style and fluency
- preserve meaning
- small lexical substitutions allowed

This separation is essential.

## 10. Undo and redo design

Recommended simple model:

- every action pushes a new version
- `Retour` decrements `current_version_index`
- `Avancer` increments `current_version_index`
- if user is not at the end of history and creates a new version, truncate the forward history

This is enough for v1.

## 11. Save behavior

Recommended save behavior for transcript files:

- user saves the **currently visible version** into the selected transcript file
- original source transcript should remain accessible in version history even after save

Optional later improvement:

- `Save as new versioned file`
- `Overwrite existing file`

## 12. Backend contract proposal

### Session-oriented document model

Introduce a document workbench API.

Suggested endpoints:

- `POST /api/workbench/load-transcript`
- `POST /api/workbench/load-batch-result`
- `GET /api/workbench/state`
- `POST /api/workbench/transform`
- `POST /api/workbench/undo`
- `POST /api/workbench/redo`
- `POST /api/workbench/save`

### Transform payload

Suggested fields:

- `operation`
  - `format`
  - `rewrite`
  - `custom`
- `include_summary`
- `prompt`
- `base`
  - `current`
  - `source`

## 13. Frontend proposal

### Main workbench area

- one editor only
- toolbar above editor
- version status strip below toolbar

### Version status strip

Show:

- source file name
- current version label
- version number like `v3 / 7`
- base mode used: `source` or `current`

### Right-side transcript library

Keep the library, but when clicking a transcript:

- it becomes the active source document in the workbench
- editor loads version `v0`

## 14. Recommended labels

Suggested UI labels:

- `Mise en forme`
- `Reformulation`
- `Résumé`
- `Consigne libre`
- `Appliquer`
- `Retour`
- `Avancer`
- `Réinitialiser`

## 15. Risk management

### Risk 1 — user loses trust because formatting changes the meaning

Mitigation:

- preserve `v0` immutable source transcript
- always allow undo

### Risk 2 — too many AI calls become slow

Mitigation:

- only run AI when button is explicitly pressed
- no automatic transformation after transcription

### Risk 3 — confusion about what is saved

Mitigation:

- always display current version label before save
- explicit save target in the UI

## 16. Recommended implementation order

1. unify the main panel and remove the separate AI-result mental model
2. add version history state in frontend first
3. add backend workbench session state
4. implement `Mise en forme` action
5. implement `Reformulation` action
6. implement summary prepend option
7. implement custom prompt action
8. connect save and transcript library actions to the current version

## 17. Final recommendation

The best solution is:

- **one main workbench panel**
- **versioned transformations**
- `Mise en forme` and `Reformulation` as distinct operations
- optional `Résumé` prepend
- free custom prompt
- undo and redo over generated versions

This solves your real need much better than trying only to improve paragraph reconstruction in isolation.
