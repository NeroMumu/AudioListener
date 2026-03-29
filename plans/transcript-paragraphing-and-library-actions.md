# Transcript paragraphing and library actions proposal

## 1. Problem to solve

Current transcripts can still appear as one long uninterrupted block when the raw ASR result lacks natural line breaks.

Example target behavior:

- keep the transcription faithful
- do not depend on LLM post-processing for readability
- rebuild readable paragraphs automatically using deterministic rules inspired by the speaker-buffer logic in [`../2026-02-01 Whisper by Gemini/main.py`](../2026-02-01%20Whisper%20by%20Gemini/main.py:974)

In parallel, the transcript library on the right needs two actions:

- delete a saved transcript
- save the edited content from the main editor back into the currently displayed transcript file

## 2. Proposed solution for paragraph reconstruction

### A. Use deterministic paragraph reconstruction, not AI

Recommended principle:

- the app should generate readable paragraphs itself
- the LLM should remain optional for later rewriting or polishing

Reason:

- fast
- reproducible
- offline
- avoids latency and hallucinations

### B. Paragraph reconstruction rules

For a monologue or same-speaker block, build paragraphs from a sequence of merged segments using these rules.

#### Rule 1 — keep speaker-based grouping

- continue to merge consecutive segments from the same speaker, as already started in [`BatchProcessor._format_transcript_paragraphs()`](../app/batch.py:183)

#### Rule 2 — split by strong punctuation

Within the merged speaker text, create a paragraph boundary when a sentence ends with:

- `.`
- `!`
- `?`
- `…`

and the following sentence begins a new semantic block.

#### Rule 3 — split by discourse markers

Start a new paragraph when a sentence begins with markers such as:

- `Alors`
- `Du coup`
- `Donc`
- `En fait`
- `Par contre`
- `Après`
- `Ensuite`
- `Finalement`
- `Bon`
- `Voilà`
- `Je comprends`
- `Je vais donc`

Reason:

- your example clearly becomes readable when these discourse transitions open new blocks

#### Rule 4 — split by paragraph size

Even without a strong marker, split when a paragraph becomes too dense.

Recommended thresholds:

- target paragraph size: around 350 to 650 characters
- hard split if a paragraph exceeds around 800 characters and a sentence boundary is available

Reason:

- this prevents giant walls of text

#### Rule 5 — preserve timestamps at paragraph level

Each paragraph should keep:

- paragraph start timestamp
- paragraph end timestamp
- speaker label

Suggested format in saved `.txt`:

- `[01:08 -> 01:53] [Interlocuteur 1] ...paragraph...`

with a blank line between paragraphs

#### Rule 6 — editor display can be cleaner than stored raw text

Recommended split between representations:

- stored file: paragraph-based plain text with timestamps and speaker labels
- editor display: same content, but rendered with paragraph spacing

## 3. Proposed formatting pipeline

### Step 1

Whisper produces segments with timestamps.

### Step 2

Pyannote assigns speaker labels.

### Step 3

Merge consecutive same-speaker segments.

### Step 4

Run a new sentence-aware paragraph splitter on the merged text.

### Step 5

Write paragraphs separated by blank lines to the saved transcript.

## 4. Proposed algorithm shape

Recommended new helper in batch formatting layer:

- `split_text_into_paragraphs(text)`
- `format_paragraph_blocks(segments, speakers)`

Pseudo behavior:

1. merge consecutive same-speaker segments
2. tokenize into sentences conservatively
3. accumulate sentences into a current paragraph
4. open a new paragraph when:
   - discourse marker found at sentence start
   - paragraph length threshold exceeded
   - explicit rhetorical shift detected
5. keep paragraph start and end timestamps from the contributing segments

## 5. Why this will match your example better

Your sample naturally contains semantic blocks:

- intro and context
- legal framing
- intervention of municipal police
- children and family concern
- housing and safety argument
- complaint escalation
- lack of proof
- request for mediator

These are recoverable from punctuation plus discourse markers without needing an LLM.

## 6. Proposed transcript library actions

### A. Delete action

Add a trash icon button on each saved transcript entry in the right column.

Behavior:

- delete only the selected saved transcript file from `Output`
- refresh the list immediately
- if the deleted transcript is currently loaded in the editor:
  - keep the editor text unchanged
  - clear the current file selection state

Reason:

- safer than wiping the editor automatically

### B. Save edited content back to current transcript

Add an edit-save action only for the currently loaded transcript.

Recommended UI behavior:

- each entry keeps a trash icon
- the currently active entry also exposes a save icon
- clicking save writes the main editor content back into that file

Reason:

- avoids ambiguity about which file is being overwritten

## 7. Backend endpoints to add

### Delete transcript

- `DELETE /api/transcripts/{file_name}`

Safety rules:

- file name must be normalized to basename only
- only `.txt` inside `Output` may be deleted
- reject path traversal

### Update transcript content

- `PUT /api/transcripts/{file_name}`

Payload:

- edited plain text content

Safety rules:

- same basename restriction
- normalize content before save
- keep UTF-8
- reject empty content if desired, or allow explicit empty overwrite only if you want that behavior

Recommended default:

- reject empty overwrite to avoid accidental data loss

## 8. Frontend behavior to add

### Current selection state

Track:

- `currentTranscriptFileName`
- `isCurrentTranscriptDirty`

### Library row actions

Each row in the right column should support:

- click row → load transcript into editor and set current selection
- trash icon → delete file from library
- save icon visible only on current row → overwrite file with current editor content

### Dirty-state UX

Recommended improvement:

- if user edits the loaded transcript, mark the row as modified
- save icon becomes highlighted

## 9. Edge-case decisions

### Delete current transcript while modified

Recommended behavior:

- ask confirmation in UI
- if confirmed, delete file only
- keep editor text in memory until user changes or clears it

### Load another transcript while current one is modified

Recommended behavior:

- ask confirmation before overwriting unsaved edits

### Batch completion while user edits another loaded transcript

Recommended behavior:

- do not overwrite immediately if editor is dirty
- instead show a notice like:
  - new transcript available, click to load

This is safer than the current unconditional overwrite model.

## 10. Recommended implementation order

1. add deterministic paragraph splitter
2. update batch formatting output
3. add transcript delete endpoint
4. add transcript overwrite endpoint
5. add current selection state in frontend
6. add row actions with icons
7. add dirty-state confirmation logic

## 11. Recommended defaults

- deterministic paragraphing, no AI dependency
- paragraph split by punctuation + discourse markers + max length
- keep timestamps and speaker labels at paragraph level
- delete only file, not editor content
- save icon only on current transcript
- confirm before replacing unsaved editor content

## 12. Summary

The best solution is not to ask the AI to make the text readable.

The better architecture is:

- improve the transcript formatter so it outputs paragraph blocks directly
- then add a real transcript-library editing workflow with:
  - load
  - delete
  - save modifications back to file

This gives readable transcripts by default and turns the right-side library into a real working document panel.
