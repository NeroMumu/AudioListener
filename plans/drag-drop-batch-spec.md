# Drag and drop batch transcription spec

## Goal

Add a first browser-based batch workflow that reunifies the current project with the folder-processing spirit of [`../2026-02-01 Whisper by Gemini/main.py`](../2026-02-01%20Whisper%20by%20Gemini/main.py) while keeping the current browser-first architecture.

## Requested scope restated

- add a drag-and-drop zone in the browser
- accept audio and video files
- upload them from the browser
- copy them into `Input`
- process them one by one
- no `Traitement` directory for this first version
- move source files into `Trash` after processing
- generate a plain text transcription result based on Whisper + Pyannote
- no AI stage yet
- no HTML report yet
- when a file finishes, the resulting text replaces the editor content

## Proposed first-version workflow

1. User drops one or more files into a new batch drop zone in the browser
2. Browser uploads each file to a dedicated backend endpoint
3. Backend stores the original uploaded file in `Input`
4. Backend creates a queue item for each uploaded file
5. A single worker consumes the queue strictly one file at a time
6. Worker reads directly from `Input` without moving the file to a temporary processing directory
7. Worker converts media as needed for transcription and diarization
8. Worker produces a plain text output with speaker segments
9. Worker writes the text transcript into `Trash` with the same logical base name as the source media
10. Worker moves the source media file into `Trash`
11. Backend publishes completion event to the browser
12. Browser overwrites the editor with the finished transcript of the last completed job

## Recommended refinements and clarifications

### 1. Input and Trash folders

Recommended clarification:

- create and use explicit `Input/` and `Trash/` directories in the current project root
- do not reuse [`History/`](../History/) for this batch workflow

Reason:

- `History` currently represents saved browser outputs, while `Input` and `Trash` better match the batch mental model inherited from the Gemini project

### 2. Queue semantics

Recommended clarification:

- queue order should be FIFO based on upload completion order
- only one job may be in `processing` state at a time
- additional dropped files stay in `queued` state

Reason:

- this preserves the single-file-at-a-time behavior you explicitly requested

### 3. What overwrites the editor

Recommended clarification:

- when a batch job completes successfully, the editor is fully replaced by the final transcript of that job
- if several files are queued, each completion overwrites the previous content
- the UI should visibly show which file produced the current editor content

Reason:

- without this clarification, users may think the editor should append rather than replace

### 4. Transcript format

Recommended clarification:

- output format should be plain text only for v1
- each segment should include timestamp and speaker label
- example line shape:
  - `[00:01:12 -> 00:01:18] [Interlocuteur 2] texte...`

Reason:

- this keeps compatibility with the current editor and logs while preserving the value of Pyannote

### 5. Supported file types

Recommended clarification:

- accepted extensions in v1:
  - audio: `.mp3`, `.m4a`, `.wav`, `.flac`, `.ogg`, `.amr`, `.webm`
  - video: `.mp4`, `.mov`, `.avi`, `.mkv`, `.mpeg`, `.mpg`, `.m4v`
- all other extensions are rejected at upload time

Reason:

- reject early in the browser and backend instead of copying unsupported files into `Input`

### 6. Copy vs move at upload time

Recommended clarification:

- browser upload creates a new copy in `Input`
- original user file on disk is never modified or moved by the app

Reason:

- in browser mode, the app cannot and should not destructively move the user’s original file from its source location

### 7. Naming in Trash

Recommended clarification:

- after processing, `Trash` contains:
  - the original uploaded source media
  - a `.txt` transcript with the same base name
- if a filename already exists, append an incremented suffix rather than overwrite silently

Reason:

- safer than overwrite for uploaded media workflows

### 8. Failure handling

Recommended clarification:

- if transcription fails:
  - keep the source media in `Trash` with a failure marker in the name or metadata
  - do not overwrite the editor
  - emit an error log and queue status update
- if upload fails:
  - do not create queue item

Reason:

- avoids losing operator context in the editor

### 9. Minimal status model

Recommended clarification:

- each job has one of:
  - `uploaded`
  - `queued`
  - `processing`
  - `completed`
  - `failed`
- UI also shows:
  - current file
  - queue length
  - last completed file

Reason:

- gives enough visibility without rebuilding the full Gemini monitoring system yet

### 10. No processing directory

Recommended clarification:

- no persistent `Traitement/` folder in v1
- temporary conversion files may still exist in system temp or a hidden temp path and are deleted automatically

Reason:

- this respects your intent while remaining technically practical for FFmpeg and diarization steps

### 11. No AI and no HTML in v1

Recommended clarification:

- disable all AI post-processing for jobs submitted through the batch drop zone
- disable HTML report generation for these jobs
- only plain transcript text is produced

Reason:

- narrows the first milestone and reduces latency and complexity

### 12. Logs

Recommended clarification:

- log these stages for each dropped file:
  - upload received
  - copied to `Input`
  - queued
  - processing started
  - Whisper done
  - Pyannote done
  - transcript written to `Trash`
  - source moved to `Trash`
  - editor updated

Reason:

- makes the new workflow traceable in the existing browser log panel

## Proposed backend components

- `batch upload endpoint`
- `input and trash path configuration`
- `batch queue service` with FIFO and single active worker
- `batch transcription service` using Whisper + Pyannote only
- `batch job event publisher` for browser status updates
- `plain text transcript writer`

## Proposed frontend components

- new drag-and-drop upload zone above or near the editor
- accepted file list preview before upload completes
- current queue status strip
- current job indicator
- overwrite-editor-on-completion behavior
- per-file success or failure feedback in logs

## Recommended non-obvious improvements

### A. Add manual queue clear for pending items only

- allows user to cancel files that are queued but not yet processing

### B. Add explicit `Replace editor on completion` behavior label

- avoids surprise when manual text disappears after a batch job completes

### C. Add `Open Input` and `Open Trash` buttons in the browser

- keeps parity with the folder-oriented workflow you want

### D. Add upload size and duration guardrails in logs only

- not as a hard rejection initially, but useful diagnostic information

### E. Keep live microphone and batch upload as separate modes in the UI

- avoids mixing real-time capture state with queued file processing state

## Concrete open decisions to confirm before coding

1. Should `Trash` keep successful files forever or is later cleanup acceptable
2. Should failed jobs also move the source media into `Trash`
3. Should the transcript file name be exactly the source base name or timestamp-prefixed
4. Should the editor be overwritten only on success, or also cleared when processing starts
5. Should dropping multiple files start processing immediately after upload, or only after an explicit `Process queue` button

## Recommended default answers for v1

- keep files in `Trash` forever for now
- move failed source files to `Trash` too
- use same base name with suffix if collision
- overwrite editor only on success
- auto-start processing immediately after upload

## Implementation direction

This should be implemented as a new batch lane inside the current app, not as a separate mini-project.

Recommended integration points:

- add batch upload API in [`app/main.py`](../app/main.py)
- add batch queue service under a new service module
- add batch storage helpers near [`app/storage.py`](../app/storage.py)
- add drag-and-drop UI in [`static/index.html`](../static/index.html)
- add upload and queue client logic in [`static/app.js`](../static/app.js)

## Summary recommendation

The specification is good, but it becomes much stronger if clarified as:

- browser upload copies files into `Input`
- backend processes one file at a time in FIFO order
- no persistent `Traitement` directory
- source media and plain transcript both end in `Trash`
- editor is overwritten only when a job succeeds
- no AI and no HTML in this first milestone
- explicit queue status and logs are visible in the browser
