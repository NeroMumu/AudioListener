const elements = {
  start: document.getElementById("start-btn"),
  clear: document.getElementById("clear-btn"),
  save: document.getElementById("save-btn"),
  openHistory: document.getElementById("open-history-btn"),
  openInput: document.getElementById("open-input-btn"),
  openTrash: document.getElementById("open-trash-btn"),
  recordAudioToggle: document.getElementById("record-audio-toggle"),
  ollamaModelSelects: Array.from(document.querySelectorAll('[data-role="ollama-model-select"]')),
  ollamaStatusNodes: Array.from(document.querySelectorAll('[data-role="ollama-status"]')),
  ollamaModelSelect: document.getElementById("ollama-model-select"),
  ollamaStatus: document.getElementById("ollama-status"),
  formatBtn: document.getElementById("format-btn"),
  rewriteBtn: document.getElementById("rewrite-btn"),
  undoVersionBtn: document.getElementById("undo-version-btn"),
  redoVersionBtn: document.getElementById("redo-version-btn"),
  customTransformBtn: document.getElementById("custom-transform-btn"),
  includeSummaryToggle: document.getElementById("include-summary-toggle"),
  versionLabel: document.getElementById("version-label"),
  editorHint: document.getElementById("editor-hint"),
  aiPrompt: document.getElementById("ai-prompt"),
  summaryOutput: document.getElementById("summary-output"),
  editor: document.getElementById("editor"),
  logsShell: document.getElementById("logs-shell"),
  debugLogWrapper: document.getElementById("debug-log-wrapper"),
  debugLog: document.getElementById("debug-log"),
  statusBadge: document.getElementById("status-badge"),
  lastSave: document.getElementById("last-save"),
  feedback: document.getElementById("feedback"),
  historyPath: document.getElementById("history-path"),
  stats: document.getElementById("stats"),
  documentTitle: document.querySelector(".document-title"),
  recordingCard: document.querySelector(".recording-card"),
  recordingOrb: document.querySelector(".recording-orb"),
  recordingTimer: document.getElementById("recording-timer"),
  recordingHint: document.querySelector(".recording-hint"),
  versionTimeline: document.getElementById("version-timeline"),
  rightTabs: Array.from(document.querySelectorAll(".right-tab")),
  panelStacks: Array.from(document.querySelectorAll(".panel-stack")),
  waveformBars: Array.from(document.querySelectorAll(".recording-waveform span")),
  transcriptLists: Array.from(document.querySelectorAll('[data-role="transcript-list"]')),
  transcriptList: document.getElementById("transcript-list"),
  batchDropZone: document.getElementById("batch-drop-zone"),
  batchFileInput: document.getElementById("batch-file-input"),
  batchQueue: document.getElementById("batch-queue"),
};

const state = {
  ws: null,
  wsReady: null,
  logsWs: null,
  logsReconnectTimer: null,
  stream: null,
  audioContext: null,
  source: null,
  workletNode: null,
  silentGain: null,
  mediaRecorder: null,
  recordingMimeType: "",
  audioSessionId: null,
  currentRecordingBaseName: null,
  audioUploadChain: Promise.resolve(),
  isListening: false,
  isStarting: false,
  isApplyingWorkbench: false,
  batchJobs: [],
  batchActiveJobId: null,
  transcriptEntries: [],
  currentTranscriptFileName: null,
  workbenchVersions: [],
  workbenchIndex: -1,
  isCurrentTranscriptDirty: false,
  workbenchModelName: null,
  editorSnapshotTimer: null,
  lastEditorSnapshotAt: 0,
  partialNode: null,
  historyPath: "Output",
  pendingStart: null,
  lastBufferedLogAt: 0,
  activePanelTab: "recording",
  recordingStartedAt: null,
  recordingTimerId: null,
  waveformTimerId: null,
  sandboxWorkbenchVersions: [{ label: "Sandbox", operation: "sandbox", content: "" }],
  sandboxWorkbenchIndex: 0,
  sandboxIsDirty: false,
  sandboxRecordingBaseName: null,
};

const AI_SUMMARY_START_MARKER = "[[[AI_SUMMARY_START]]]";
const AI_SUMMARY_END_MARKER = "[[[AI_SUMMARY_END]]]";
const AI_BODY_START_MARKER = "[[[AI_BODY_START]]]";
const AI_BODY_END_MARKER = "[[[AI_BODY_END]]]";

function setFeedback(message) {
  elements.feedback.textContent = message;
}

function getSelectedTranscriptionModel() {
  return elements.ollamaModelSelect?.value || "";
}

function syncOllamaModelSelects(selectedValue = "") {
  const primarySelect = elements.ollamaModelSelect;
  if (!primarySelect) {
    return;
  }

  for (const select of elements.ollamaModelSelects) {
    if (select !== primarySelect) {
      select.innerHTML = primarySelect.innerHTML;
    }

    select.disabled = primarySelect.disabled;

    if (selectedValue && Array.from(select.options).some((option) => option.value === selectedValue)) {
      select.value = selectedValue;
    } else if (select.options.length) {
      select.value = select.options[0].value;
    }
  }
}

function setActivePanelTab(tabName) {
  state.activePanelTab = tabName;
  for (const button of elements.rightTabs) {
    const isActive = button.dataset.panelTab === tabName;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  }
  for (const panel of elements.panelStacks) {
    panel.classList.toggle("panel-stack--active", panel.dataset.panel === tabName);
  }
}

function updateRecordingTimer() {
  if (!elements.recordingTimer) {
    return;
  }

  if (!state.recordingStartedAt) {
    elements.recordingTimer.textContent = "00:00";
    return;
  }

  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - state.recordingStartedAt) / 1000));
  const minutes = String(Math.floor(elapsedSeconds / 60)).padStart(2, "0");
  const seconds = String(elapsedSeconds % 60).padStart(2, "0");
  elements.recordingTimer.textContent = `${minutes}:${seconds}`;
}

function randomizeWaveformBars() {
  if (!elements.waveformBars?.length) {
    return;
  }

  for (const bar of elements.waveformBars) {
    const height = 8 + Math.round(Math.random() * (state.isListening ? 18 : 10));
    bar.style.height = `${height}px`;
    bar.style.background = state.isListening ? "var(--accent)" : "var(--border2)";
  }
}

function startRecordingVisuals() {
  if (!state.recordingStartedAt) {
    state.recordingStartedAt = Date.now();
  }
  if (state.recordingTimerId) {
    window.clearInterval(state.recordingTimerId);
  }
  state.recordingTimerId = window.setInterval(updateRecordingTimer, 1000);
  if (state.waveformTimerId) {
    window.clearInterval(state.waveformTimerId);
  }
  state.waveformTimerId = window.setInterval(randomizeWaveformBars, 1000);
  updateRecordingTimer();
  randomizeWaveformBars();
}

function stopRecordingVisuals() {
  if (state.recordingTimerId) {
    window.clearInterval(state.recordingTimerId);
    state.recordingTimerId = null;
  }
  if (state.waveformTimerId) {
    window.clearInterval(state.waveformTimerId);
    state.waveformTimerId = null;
  }
  state.recordingStartedAt = null;
  updateRecordingTimer();
  randomizeWaveformBars();
}

function updateRecordingVisualState() {
  const isLive = state.isListening || state.isStarting;
  elements.recordingCard?.classList.toggle("is-live", isLive);
  elements.recordingOrb?.classList.toggle("is-live", isLive);
  if (elements.recordingHint) {
    elements.recordingHint.textContent = isLive ? "Enregistrement en cours…" : "Cliquer pour démarrer";
  }
}

function updateDocumentHeader() {
  if (elements.documentTitle) {
    elements.documentTitle.textContent = state.currentTranscriptFileName || "Sandbox";
  }
  if (elements.feedback) {
    // no-op: feedback remains in footer; document metadata is handled via #editor-hint + #stats
  }
  if (elements.editorHint) {
    const nowLabel = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" }).format(new Date());
    elements.editorHint.textContent = state.currentTranscriptFileName ? `Fichier actif · ${nowLabel}` : `Sandbox local · ${nowLabel}`;
  }
}

function renderVersionTimeline() {
  if (!elements.versionTimeline) {
    return;
  }

  elements.versionTimeline.innerHTML = "";
  const versions = state.workbenchVersions?.length ? state.workbenchVersions : [{ label: "Source", operation: "source", content: "" }];

  versions.forEach((version, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `timeline-node ${index === state.workbenchIndex ? "is-active" : ""}`.trim();

    const dot = document.createElement("span");
    dot.className = "timeline-node__dot";

    const label = document.createElement("span");
    label.className = "timeline-node__label";
    label.textContent = (version.label || `v${index + 1}`).slice(0, 22);

    button.append(dot, label);
    button.addEventListener("click", () => {
      applyWorkbenchVersion(index);
    });
    elements.versionTimeline.appendChild(button);
  });
}

function setSummaryOutput(message, isPlaceholder = false) {
  if (!elements.summaryOutput) {
    return;
  }
  elements.summaryOutput.textContent = message;
  elements.summaryOutput.dataset.placeholder = String(isPlaceholder);
}

function getCurrentWorkbenchVersion() {
  if (state.workbenchIndex < 0 || state.workbenchIndex >= state.workbenchVersions.length) {
    return null;
  }
  return state.workbenchVersions[state.workbenchIndex];
}

function cloneWorkbenchVersions(versions) {
  return (versions || []).map((version) => ({ ...version }));
}

function resetSandboxState() {
  state.sandboxWorkbenchVersions = [{ label: "Sandbox", operation: "sandbox", content: "" }];
  state.sandboxWorkbenchIndex = 0;
  state.sandboxIsDirty = false;
  state.sandboxRecordingBaseName = null;
}

function getSandboxCurrentVersion() {
  const versions = state.sandboxWorkbenchVersions?.length
    ? state.sandboxWorkbenchVersions
    : [{ label: "Sandbox", operation: "sandbox", content: "" }];
  const index = Math.min(Math.max(state.sandboxWorkbenchIndex, 0), versions.length - 1);
  return versions[index] || versions[0];
}

function syncSandboxStateFromCurrentWorkbench() {
  if (state.currentTranscriptFileName !== null) {
    return;
  }

  const versions = state.workbenchVersions?.length
    ? cloneWorkbenchVersions(state.workbenchVersions)
    : [{ label: "Sandbox", operation: "sandbox", content: getEditorText() || "" }];

  state.sandboxWorkbenchVersions = versions;
  state.sandboxWorkbenchIndex = Math.min(Math.max(state.workbenchIndex, 0), versions.length - 1);
  state.sandboxIsDirty = state.isCurrentTranscriptDirty;
  state.sandboxRecordingBaseName = state.currentRecordingBaseName;
}

function restoreSandboxWorkbench() {
  const versions = state.sandboxWorkbenchVersions?.length
    ? cloneWorkbenchVersions(state.sandboxWorkbenchVersions)
    : [{ label: "Sandbox", operation: "sandbox", content: "" }];

  state.currentTranscriptFileName = null;
  state.currentRecordingBaseName = state.sandboxRecordingBaseName;
  state.workbenchVersions = versions;
  state.workbenchIndex = Math.min(Math.max(state.sandboxWorkbenchIndex, 0), versions.length - 1);
  state.isCurrentTranscriptDirty = state.sandboxIsDirty;
  setEditorContent(versions[state.workbenchIndex]?.content || "");
  updateWorkbenchIndicators();
}

function getSandboxSummary() {
  const currentVersion = getCurrentWorkbenchVersion();
  const content = getEditorText().trim();
  const characterCount = content.length;
  const wordCount = content ? content.split(/\s+/).filter(Boolean).length : 0;
  const sourceLabel = state.currentTranscriptFileName ? state.currentTranscriptFileName : "Sandbox local (sans fichier)";
  const modeLabel = state.currentTranscriptFileName ? "Document lié à un fichier" : "Brouillon libre";
  const versionLabel = currentVersion
    ? `${state.workbenchIndex + 1}/${state.workbenchVersions.length}`
    : "Aucune version";
  const operationLabel = currentVersion?.operation || "sandbox";
  const statusLabel = state.isCurrentTranscriptDirty ? "Modifié" : "Stable";

  return [
    `Source : ${sourceLabel}`,
    `Mode : ${modeLabel}`,
    `Version : ${versionLabel}`,
    `Opération : ${operationLabel}`,
    `Statut : ${statusLabel}`,
    `Contenu : ${characterCount} caractère${characterCount > 1 ? "s" : ""} · ${wordCount} mot${wordCount > 1 ? "s" : ""}`,
  ].join("\n");
}

function updateWorkbenchIndicators() {
  const currentVersion = getCurrentWorkbenchVersion();
  const hasVisibleSummary = splitEditorSummaryContent(currentVersion?.content || getEditorText()).hasSummary;
  if (elements.versionLabel) {
    elements.versionLabel.value = currentVersion?.label || "Sandbox";
  }
  if (elements.includeSummaryToggle && !state.isApplyingWorkbench) {
    elements.includeSummaryToggle.checked = hasVisibleSummary;
  }
  if (elements.undoVersionBtn) {
    elements.undoVersionBtn.disabled = state.workbenchIndex <= 0 || state.isApplyingWorkbench;
  }
  if (elements.redoVersionBtn) {
    elements.redoVersionBtn.disabled =
      state.workbenchIndex < 0 || state.workbenchIndex >= state.workbenchVersions.length - 1 || state.isApplyingWorkbench;
  }

  setSummaryOutput(getSandboxSummary(), false);
  updateDocumentHeader();
  renderVersionTimeline();
  syncSandboxStateFromCurrentWorkbench();
}

function resetWorkbench(content, label = "Sandbox", operation = "sandbox") {
  state.workbenchVersions = [{ label, operation, content: content || "" }];
  state.workbenchIndex = 0;
  state.isCurrentTranscriptDirty = false;
  setEditorContent(content || "");
  updateWorkbenchIndicators();
}

function pushWorkbenchVersion(content, label, operation) {
  const normalizedContent = content || "";
  if (state.workbenchIndex < state.workbenchVersions.length - 1) {
    state.workbenchVersions = state.workbenchVersions.slice(0, state.workbenchIndex + 1);
  }
  state.workbenchVersions.push({ label, operation, content: normalizedContent });
  state.workbenchIndex = state.workbenchVersions.length - 1;
  state.isCurrentTranscriptDirty = false;
  setEditorContent(normalizedContent);
  updateWorkbenchIndicators();
}

function applyWorkbenchVersion(index) {
  if (index < 0 || index >= state.workbenchVersions.length) {
    return;
  }
  state.workbenchIndex = index;
  setEditorContent(state.workbenchVersions[index].content || "");
  updateWorkbenchIndicators();
}

function scheduleEditorSnapshot() {
  if (state.workbenchIndex < 0) {
    return;
  }

  if (state.editorSnapshotTimer) {
    window.clearTimeout(state.editorSnapshotTimer);
  }

  state.editorSnapshotTimer = window.setTimeout(() => {
    const content = getEditorText();
    const currentVersion = getCurrentWorkbenchVersion();
    if (!content || !currentVersion || content === currentVersion.content) {
      return;
    }

    const now = Date.now();
    const lastVersion = state.workbenchVersions[state.workbenchVersions.length - 1];
    if (lastVersion && lastVersion.operation === "manual-edit" && now - state.lastEditorSnapshotAt <= 1500) {
      lastVersion.content = content;
      lastVersion.label = "Édition manuelle";
      state.workbenchIndex = state.workbenchVersions.length - 1;
    } else {
      pushWorkbenchVersion(content, "Édition manuelle", "manual-edit");
    }

    state.lastEditorSnapshotAt = now;
    updateWorkbenchIndicators();
  }, 900);
}

function setEditorContent(content) {
  elements.editor.textContent = content || "";
  removePartial();
  updateStats();
  refreshButtons();
}

function splitEditorSummaryContent(content) {
  const marker = "\n\n---\n\n";
  if (!content || !content.startsWith("Résumé\n\n") || !content.includes(marker)) {
    return {
      hasSummary: false,
      summary: "",
      body: content || "",
    };
  }

  const markerIndex = content.indexOf(marker);
  if (markerIndex === -1) {
    return {
      hasSummary: false,
      summary: "",
      body: content || "",
    };
  }

  return {
    hasSummary: true,
    summary: content.slice("Résumé\n\n".length, markerIndex).trim(),
    body: content.slice(markerIndex + marker.length),
  };
}

function extractWorkbenchBaseContent(content) {
  return splitEditorSummaryContent(content).body.trim();
}

function formatEditorSummaryContent(summary, body) {
  if (!summary?.trim()) {
    return body || "";
  }

  return `Résumé\n\n${summary.trim()}\n\n---\n\n${body || ""}`;
}

function parsePersistedWorkbenchContent(content) {
  const rawContent = content || "";
  const summaryStart = rawContent.indexOf(AI_SUMMARY_START_MARKER);
  const summaryEnd = rawContent.indexOf(AI_SUMMARY_END_MARKER);
  const bodyStart = rawContent.indexOf(AI_BODY_START_MARKER);
  const bodyEnd = rawContent.indexOf(AI_BODY_END_MARKER);

  if (summaryStart !== -1 && summaryEnd !== -1 && bodyStart !== -1 && bodyEnd !== -1) {
    return {
      hasSummary: true,
      summary: rawContent.slice(summaryStart + AI_SUMMARY_START_MARKER.length, summaryEnd).trim(),
      body: rawContent.slice(bodyStart + AI_BODY_START_MARKER.length, bodyEnd).trim(),
    };
  }

  return splitEditorSummaryContent(rawContent);
}

function serializeWorkbenchContentForStorage(content) {
  const parsedContent = splitEditorSummaryContent(content);
  if (!parsedContent.hasSummary) {
    return parsedContent.body;
  }

  return [
    AI_SUMMARY_START_MARKER,
    parsedContent.summary.trim(),
    AI_SUMMARY_END_MARKER,
    AI_BODY_START_MARKER,
    parsedContent.body.trim(),
    AI_BODY_END_MARKER,
  ].join("\n");
}

function resolveLoadedTranscriptContent(content, keepSummary) {
  const parsedContent = parsePersistedWorkbenchContent(content);
  return {
    hasSummary: parsedContent.hasSummary,
    editorContent:
      parsedContent.hasSummary && keepSummary
        ? formatEditorSummaryContent(parsedContent.summary, parsedContent.body)
        : parsedContent.body,
  };
}

function markCurrentTranscriptDirty(isDirty) {
  state.isCurrentTranscriptDirty = Boolean(isDirty);
}

function formatDateTime(value) {
  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(parsedDate);
}

function setOllamaStatus(message) {
  for (const node of elements.ollamaStatusNodes) {
    node.textContent = message;
  }
}

function setLogsCollapsed(collapsed) {
  elements.logsShell?.classList.toggle("is-collapsed", collapsed);
  if (!collapsed) {
    requestAnimationFrame(() => {
      elements.debugLog.scrollTop = elements.debugLog.scrollHeight;
    });
  }
}

function resetAudioSessionState() {
  state.audioSessionId = null;
  state.audioUploadChain = Promise.resolve();
}

function formatLogTimestamp(value) {
  if (!value) {
    return new Date().toLocaleTimeString("fr-FR");
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return value;
  }

  return parsedDate.toLocaleTimeString("fr-FR");
}

function appendDebugLog(message, options = {}) {
  const { timestamp = new Date().toLocaleTimeString("fr-FR"), source = "browser", level = "INFO" } = options;
  const line = document.createElement("div");
  line.className = "debug-line";
  line.dataset.level = level;
  line.dataset.source = source;
  line.textContent = source ? `[${timestamp}] [${source}] ${message}` : `[${timestamp}] ${message}`;
  elements.debugLog.appendChild(line);
  requestAnimationFrame(() => {
    elements.debugLog.scrollTop = elements.debugLog.scrollHeight;
  });
}

function appendServerLogEvent(event) {
  if (!event || !event.message) {
    return;
  }

  appendDebugLog(event.message, {
    timestamp: formatLogTimestamp(event.timestamp),
    source: event.source || "server",
    level: event.level || "INFO",
  });
}

function formatBatchStatus(status) {
  const labels = {
    queued: "En file",
    processing: "Traitement",
    completed: "Terminé",
    failed: "Échec",
  };
  return labels[status] || status;
}

function renderBatchQueue(payload) {
  const jobs = payload?.jobs || [];
  state.batchJobs = jobs;
  state.batchActiveJobId = payload?.active_job_id || null;
  elements.batchQueue.innerHTML = "";

  for (const job of jobs.slice(0, 8)) {
    const item = document.createElement("article");
    item.className = "batch-job";

    const header = document.createElement("div");
    header.className = "batch-job-header";

    const name = document.createElement("div");
    name.className = "batch-job-name";
    name.textContent = job.file_name;

    const badge = document.createElement("span");
    badge.className = `batch-job-status ${job.status}`;
    badge.textContent = formatBatchStatus(job.status);

    header.append(name, badge);

    const meta = document.createElement("div");
    meta.className = "batch-job-meta";
    const details = [];
    if (job.output_file_name) {
      details.push(`Sortie: ${job.output_file_name}`);
    }
    if (job.error) {
      details.push(`Erreur: ${job.error}`);
    }
    if (!details.length) {
      details.push(`Source: ${job.source}`);
    }
    meta.textContent = details.join(" · ");

    item.append(header, meta);
    elements.batchQueue.appendChild(item);
  }
}

function renderTranscriptList(entries) {
  state.transcriptEntries = entries || [];
  for (const transcriptList of elements.transcriptLists) {
    transcriptList.innerHTML = "";

    const sandboxVersion = getSandboxCurrentVersion();
    const sandboxContent = sandboxVersion?.content?.trim() || "";
    const sandboxIsActive = state.currentTranscriptFileName === null;
    const sandboxItem = document.createElement("article");
    sandboxItem.className = `transcript-entry transcript-entry--sandbox ${sandboxIsActive ? "is-active" : ""}`.trim();

    const sandboxHeader = document.createElement("div");
    sandboxHeader.className = "transcript-entry-header";

    const sandboxLoadButton = document.createElement("button");
    sandboxLoadButton.type = "button";
    sandboxLoadButton.className = "transcript-entry-load";

    const sandboxName = document.createElement("span");
    sandboxName.className = "transcript-entry-name";
    sandboxName.textContent = "Sandbox";

    const sandboxMeta = document.createElement("span");
    sandboxMeta.className = "transcript-entry-meta transcript-entry-meta--sandbox";
    const sandboxMetaParts = [sandboxContent ? (state.sandboxIsDirty ? "Modifié" : "Propre") : "Vide"];
    if (sandboxContent) {
      sandboxMetaParts.push(`${sandboxContent.length} caractères`);
    }
    if (state.sandboxRecordingBaseName) {
      sandboxMetaParts.push(state.sandboxRecordingBaseName);
    }
    sandboxMeta.textContent = sandboxMetaParts.join(" · ");

    sandboxLoadButton.append(sandboxName, sandboxMeta);
    sandboxLoadButton.addEventListener("click", async () => {
      restoreSandboxWorkbench();
      setFeedback("Sandbox chargé.");
      await refreshTranscriptList();
    });

    const sandboxActions = document.createElement("div");
    sandboxActions.className = "transcript-entry-actions";

    if (sandboxContent) {
      const sandboxSaveButton = document.createElement("button");
      sandboxSaveButton.type = "button";
      sandboxSaveButton.className = "icon-button is-primary";
      sandboxSaveButton.title = "Sauvegarder le sandbox comme fichier";
      sandboxSaveButton.textContent = "💾";
      sandboxSaveButton.addEventListener("click", async (event) => {
        event.stopPropagation();
        try {
          restoreSandboxWorkbench();
          await saveTranscript();
        } catch (error) {
          setStatus("error");
          setFeedback(error.message || "Impossible de sauvegarder le sandbox.");
        }
      });
      sandboxActions.appendChild(sandboxSaveButton);
    }

    sandboxHeader.append(sandboxLoadButton, sandboxActions);
    sandboxItem.appendChild(sandboxHeader);
    transcriptList.appendChild(sandboxItem);

    for (const entry of state.transcriptEntries) {
      const item = document.createElement("article");
      item.className = `transcript-entry ${state.currentTranscriptFileName === entry.file_name ? "is-active" : ""}`.trim();

      const header = document.createElement("div");
      header.className = "transcript-entry-header";

      const loadButton = document.createElement("button");
      loadButton.type = "button";
      loadButton.className = "transcript-entry-load";

      const name = document.createElement("span");
      name.className = "transcript-entry-name";
      name.textContent = entry.file_name;

      const meta = document.createElement("span");
      meta.className = "transcript-entry-meta";
      meta.textContent = `Mis à jour : ${formatDateTime(entry.updated_at)}`;

      loadButton.append(name, meta);
      loadButton.addEventListener("click", async () => {
        try {
          syncSandboxStateFromCurrentWorkbench();
          const payload = await fetchTranscriptContent(entry.file_name);
          const resolvedContent = resolveLoadedTranscriptContent(
            payload.content || "",
            Boolean(elements.includeSummaryToggle?.checked),
          );
          if (elements.includeSummaryToggle) {
            elements.includeSummaryToggle.checked = Boolean(resolvedContent.hasSummary && elements.includeSummaryToggle.checked);
          }
          state.currentTranscriptFileName = payload.file_name;
          resetWorkbench(resolvedContent.editorContent || "", `Source · ${payload.file_name}`, "source");
          setFeedback(`Transcription chargée : ${payload.file_name}`);
          appendDebugLog(`Transcript chargé dans l'éditeur · ${payload.file_name}`, { source: "library" });
          await refreshTranscriptList();
        } catch (error) {
          setStatus("error");
          setFeedback(error.message || "Impossible de charger cette transcription.");
        }
      });

      const actions = document.createElement("div");
      actions.className = "transcript-entry-actions";

      if (state.currentTranscriptFileName === entry.file_name) {
        const updateButton = document.createElement("button");
        updateButton.type = "button";
        updateButton.className = "icon-button is-primary";
        updateButton.title = "Mettre à jour le fichier avec l'édition en cours";
        updateButton.textContent = "✎";
        updateButton.addEventListener("click", async (event) => {
          event.stopPropagation();
          try {
            const payload = await updateTranscriptContent(entry.file_name, getEditorText());
            const resolvedContent = resolveLoadedTranscriptContent(
              payload.content || "",
              Boolean(elements.includeSummaryToggle?.checked),
            );
            if (elements.includeSummaryToggle) {
              elements.includeSummaryToggle.checked = Boolean(resolvedContent.hasSummary && elements.includeSummaryToggle.checked);
            }
            state.currentTranscriptFileName = payload.file_name;
            resetWorkbench(resolvedContent.editorContent || "", `Source · ${payload.file_name}`, "update");
            setFeedback(`Transcript mis à jour : ${payload.file_name}`);
            appendDebugLog(`Transcript mis à jour · ${payload.file_name}`, { source: "library" });
            await refreshTranscriptList();
          } catch (error) {
            setStatus("error");
            setFeedback(error.message || "Impossible de mettre à jour ce transcript.");
          }
        });
        actions.appendChild(updateButton);
      }

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "icon-button";
      deleteButton.title = "Supprimer la transcription";
      deleteButton.textContent = "🗑";
      deleteButton.addEventListener("click", async (event) => {
        event.stopPropagation();
        try {
          await deleteTranscriptEntry(entry.file_name);
          if (state.currentTranscriptFileName === entry.file_name) {
            restoreSandboxWorkbench();
          }
          setFeedback(`Transcript supprimé : ${entry.file_name}`);
          appendDebugLog(`Transcript supprimé · ${entry.file_name}`, { source: "library" });
          await refreshTranscriptList();
        } catch (error) {
          setStatus("error");
          setFeedback(error.message || "Impossible de supprimer ce transcript.");
        }
      });
      actions.appendChild(deleteButton);

      header.append(loadButton, actions);
      item.appendChild(header);
      transcriptList.appendChild(item);
    }
  }
}

async function refreshTranscriptList() {
  const response = await fetch("/api/transcripts");
  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || "Impossible de charger les transcriptions enregistrées.");
  }

  const payload = await response.json();
  renderTranscriptList(payload.entries || []);
}

async function fetchTranscriptContent(fileName) {
  const response = await fetch(`/api/transcripts/${encodeURIComponent(fileName)}`);
  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || "Impossible de charger le transcript demandé.");
  }

  return response.json();
}

async function updateTranscriptContent(fileName, content) {
  const response = await fetch(`/api/transcripts/${encodeURIComponent(fileName)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: serializeWorkbenchContentForStorage(content) }),
  });
  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || "Impossible de mettre à jour le transcript demandé.");
  }
  return response.json();
}

async function deleteTranscriptEntry(fileName) {
  const response = await fetch(`/api/transcripts/${encodeURIComponent(fileName)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || "Impossible de supprimer le transcript demandé.");
  }
  return response.json();
}

async function refreshBatchJobs() {
  const response = await fetch("/api/batch/jobs");
  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || "Impossible de charger la file batch.");
  }

  const payload = await response.json();
  renderBatchQueue(payload);
}

async function fetchBatchTranscript(jobId) {
  const response = await fetch(`/api/batch/jobs/${encodeURIComponent(jobId)}/transcript`);
  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || "Transcript batch indisponible.");
  }
  return response.json();
}

async function uploadBatchFile(file) {
  const response = await fetch("/api/batch/upload", {
    method: "POST",
    headers: {
      "X-Upload-Filename": file.name,
      "Content-Type": file.type || "application/octet-stream",
    },
    body: file,
  });

  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || `Impossible d'envoyer ${file.name}.`);
  }

  return response.json();
}

async function uploadBatchFiles(fileList) {
  const files = Array.from(fileList || []).filter(Boolean);
  if (!files.length) {
    return;
  }

  for (const file of files) {
    appendDebugLog(`Upload batch demandé · ${file.name}`, { source: "browser" });
    const payload = await uploadBatchFile(file);
    appendDebugLog(`Fichier batch ajouté · ${payload.job.file_name}`, { source: "batch" });
  }

  await refreshBatchJobs();
}

async function openFolder(endpoint, label) {
  const response = await fetch(endpoint, { method: "POST" });
  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || `Impossible d'ouvrir ${label}.`);
  }
}

function formatCounter(value, singular, plural) {
  return `${value} ${value > 1 ? plural : singular}`;
}

function serializeEditorContent() {
  const sections = [];

  for (const node of elements.editor.childNodes) {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent?.replace(/\u00a0/g, " ").replace(/\n{3,}/g, "\n\n").trim();
      if (text) {
        sections.push(text);
      }
      continue;
    }

    if (!(node instanceof HTMLElement)) {
      continue;
    }

    const text = node.innerText.replace(/\u00a0/g, " ").replace(/\n{3,}/g, "\n\n").trim();
    if (text) {
      sections.push(text);
    }
  }

  return sections.join("\n\n").trim();
}

function getEditorText() {
  return serializeEditorContent();
}

function setStatus(status) {
  const labels = {
    inactive: "Inactif",
    listening: "En écoute",
    stopped: "Arrêté",
    error: "Erreur",
  };

  if (elements.statusBadge) {
    elements.statusBadge.textContent = labels[status] ?? status;
    const pill = elements.statusBadge.closest(".model-pill");
    pill?.classList.toggle("model-pill--active", status === "listening");
    pill?.classList.toggle("model-pill--inactive", status !== "listening");
  }
  if (status !== "listening") {
    stopRecordingVisuals();
  }
  updateRecordingVisualState();
  refreshButtons();
}

function updateStats() {
  const text = getEditorText();
  const characters = text.length;
  const words = text ? text.split(/\s+/).filter(Boolean).length : 0;
  elements.stats.textContent = `${formatCounter(characters, "caractère", "caractères")} · ${formatCounter(words, "mot", "mots")}`;
}

function refreshButtons() {
  const hasContent = getEditorText().trim().length > 0;
  const hasTranscriptionModel = Boolean(getSelectedTranscriptionModel());
  const hasCustomPrompt = Boolean(elements.aiPrompt?.value?.trim());
  elements.start.disabled = state.isStarting || !hasTranscriptionModel;
  elements.start.setAttribute("aria-label", state.isListening ? "Arrêter l'enregistrement" : "Démarrer l'enregistrement");
  elements.clear.disabled = !hasContent;
  elements.save.disabled = !hasContent;
  if (elements.formatBtn) {
    elements.formatBtn.disabled = !hasContent || state.isApplyingWorkbench || state.isStarting;
  }
  if (elements.rewriteBtn) {
    elements.rewriteBtn.disabled = !hasContent || state.isApplyingWorkbench || state.isStarting;
  }
  if (elements.customTransformBtn) {
    elements.customTransformBtn.disabled = !hasContent || !hasCustomPrompt || state.isApplyingWorkbench || state.isStarting;
  }
  elements.formatBtn?.classList.toggle("is-active", currentVersionHasOperation("format"));
  elements.rewriteBtn?.classList.toggle("is-active", currentVersionHasOperation("rewrite"));
  updateWorkbenchIndicators();
  updateRecordingVisualState();
}

function currentVersionHasOperation(operation) {
  const currentVersion = getCurrentWorkbenchVersion();
  return currentVersion?.operation === operation;
}

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((innerResolve, innerReject) => {
    resolve = innerResolve;
    reject = innerReject;
  });
  return { promise, resolve, reject };
}

function resolvePendingStart() {
  if (state.pendingStart) {
    state.pendingStart.resolve();
    state.pendingStart = null;
  }
}

function rejectPendingStart(message) {
  if (state.pendingStart) {
    state.pendingStart.reject(new Error(message));
    state.pendingStart = null;
  }
}

function createBlock(timestamp, text, isPartial = false) {
  const block = document.createElement("div");
  block.className = `editor-block ${isPartial ? "partial" : "final"}`;
  block.dataset.timestamp = timestamp;
  block.dataset.partial = String(isPartial);
  block.textContent = text;
  return block;
}

function scrollEditorToBottom() {
  elements.editor.scrollTop = elements.editor.scrollHeight;
}

function renderPartial(timestamp, text) {
  if (!state.partialNode || !state.partialNode.isConnected) {
    state.partialNode = createBlock(timestamp, text, true);
    elements.editor.appendChild(state.partialNode);
  } else {
    state.partialNode.dataset.timestamp = timestamp;
    state.partialNode.textContent = text;
  }
  scrollEditorToBottom();
  updateStats();
  refreshButtons();
}

function renderFinal(timestamp, text) {
  const finalNode = createBlock(timestamp, text, false);
  if (state.partialNode && state.partialNode.isConnected) {
    state.partialNode.replaceWith(finalNode);
  } else {
    elements.editor.appendChild(finalNode);
  }
  state.partialNode = null;
  scrollEditorToBottom();
  updateStats();
  refreshButtons();
}

function removePartial() {
  if (state.partialNode && state.partialNode.isConnected) {
    state.partialNode.remove();
  }
  state.partialNode = null;
  updateStats();
}

function formatSavedAt(savedAt) {
  const value = new Date(savedAt);
  if (Number.isNaN(value.getTime())) {
    return savedAt;
  }

  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(value);
}

function describeMicrophoneError(error) {
  const errorName = error?.name;

  if (errorName === "NotAllowedError") {
    return "Accès au microphone refusé. Autorisez le micro dans le navigateur puis réessayez.";
  }

  if (errorName === "NotFoundError") {
    return "Aucun microphone n'a été détecté sur cette machine.";
  }

  if (errorName === "NotReadableError") {
    return "Le microphone est déjà utilisé par une autre application ou indisponible.";
  }

  return error?.message || "Impossible d'accéder au microphone.";
}

function float32ToInt16(float32Samples) {
  const pcm = new Int16Array(float32Samples.length);
  for (let index = 0; index < float32Samples.length; index += 1) {
    const value = Math.max(-1, Math.min(1, float32Samples[index]));
    pcm[index] = value < 0 ? value * 32768 : value * 32767;
  }
  return pcm;
}

function encodeChunk(samples, sampleRate) {
  const pcm = float32ToInt16(samples);
  const buffer = new ArrayBuffer(4 + pcm.byteLength);
  const view = new DataView(buffer);
  view.setUint32(0, sampleRate, true);
  new Int16Array(buffer, 4, pcm.length).set(pcm);
  return buffer;
}

function pickRecordingMimeType() {
  if (typeof MediaRecorder === "undefined") {
    return "";
  }

  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
  ];

  if (typeof MediaRecorder.isTypeSupported !== "function") {
    return candidates[0];
  }

  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) ?? "";
}

function guessAudioExtension(mimeType) {
  const baseType = (mimeType || "audio/webm").split(";")[0].trim().toLowerCase();
  const mapping = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mp4": "mp4",
    "audio/mpeg": "mp3",
  };
  return mapping[baseType] || "webm";
}

async function startAudioUploadSession(mimeType) {
  const response = await fetch("/api/audio/start", {
    method: "POST",
    headers: {
      "X-Audio-Extension": guessAudioExtension(mimeType),
    },
  });

  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || "Impossible de démarrer l'enregistrement audio.");
  }

  return response.json();
}

async function uploadAudioChunk(blob) {
  if (!blob || blob.size === 0 || !state.audioSessionId) {
    return null;
  }

  const response = await fetch("/api/audio/chunk", {
    method: "POST",
    headers: {
      "Content-Type": blob.type || "application/octet-stream",
      "X-Audio-Session-Id": state.audioSessionId,
    },
    body: await blob.arrayBuffer(),
  });

  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || "Impossible d'enregistrer le son.");
  }
}

function queueAudioChunkUpload(blob) {
  state.audioUploadChain = state.audioUploadChain
    .catch(() => undefined)
    .then(() => uploadAudioChunk(blob));

  return state.audioUploadChain;
}

async function finalizeUploadedAudio() {
  if (!state.audioSessionId) {
    return null;
  }

  await state.audioUploadChain.catch((error) => {
    throw error;
  });

  const sessionId = state.audioSessionId;
  const response = await fetch("/api/audio/finish", {
    method: "POST",
    headers: {
      "X-Audio-Session-Id": sessionId,
    },
  });

  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || "Impossible de finaliser l'enregistrement audio.");
  }

  const payload = await response.json();
  resetAudioSessionState();
  return payload;
}

async function startAudioRecording() {
  if (!elements.recordAudioToggle.checked || !state.stream) {
    return;
  }

  if (typeof MediaRecorder === "undefined") {
    appendDebugLog("MediaRecorder indisponible dans ce navigateur");
    setFeedback("La transcription continue, mais ce navigateur ne sait pas enregistrer le son.");
    return;
  }

  const mimeType = pickRecordingMimeType();

  try {
    const session = await startAudioUploadSession(mimeType || "audio/webm");
    state.audioSessionId = session.session_id;
    state.currentRecordingBaseName = session.base_name;
    state.audioUploadChain = Promise.resolve();
    state.mediaRecorder = mimeType ? new MediaRecorder(state.stream, { mimeType }) : new MediaRecorder(state.stream);
    state.recordingMimeType = state.mediaRecorder.mimeType || mimeType || "audio/webm";
    state.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        queueAudioChunkUpload(event.data).catch((error) => {
          appendDebugLog(`Échec d'écriture audio continue : ${error.message || error}`);
        });
      }
    };
    state.mediaRecorder.start(1000);
    appendDebugLog(`Enregistrement audio activé · format ${state.recordingMimeType} · base ${state.currentRecordingBaseName}`);
  } catch (error) {
    state.mediaRecorder = null;
    state.recordingMimeType = "";
    resetAudioSessionState();
    appendDebugLog(`Échec du démarrage de l'enregistrement audio : ${error.message || error}`);
    setFeedback("La transcription a démarré, mais l'enregistrement audio n'a pas pu être activé.");
  }
}

async function finalizeAudioRecording() {
  const recorder = state.mediaRecorder;
  if (!recorder) {
    return null;
  }

  if (recorder.state === "inactive") {
    state.mediaRecorder = null;
    state.recordingMimeType = "";
    return finalizeUploadedAudio();
  }

  return new Promise((resolve, reject) => {
    recorder.onstop = async () => {
      try {
        const payload = await finalizeUploadedAudio();
        resolve(payload);
      } catch (error) {
        reject(error);
      } finally {
        state.mediaRecorder = null;
        state.recordingMimeType = "";
      }
    };

    recorder.onerror = (event) => {
      state.mediaRecorder = null;
      state.recordingMimeType = "";
      reject(new Error(event.error?.message || "Erreur MediaRecorder"));
    };

    recorder.stop();
  });
}

function handleServerEvent(payload) {
  if (payload.type === "ready") {
    state.historyPath = payload.historyDir;
    elements.historyPath.textContent = payload.historyDir;
    const languageLabel = payload.language === "fr" ? "français" : payload.language;
    setFeedback(`Backend prêt · modèle de transcription ${payload.model} · langue ${languageLabel}`);
    appendDebugLog(`Connexion WebSocket prête · modèle de transcription ${payload.model} · langue ${languageLabel}`);
    return;
  }

  if (payload.type === "status") {
    if (payload.status === "listening") {
      state.isStarting = false;
      state.isListening = true;
      resolvePendingStart();
    }

    setStatus(payload.status);
    if (payload.status === "stopped") {
      state.isStarting = false;
      state.isListening = false;
      removePartial();
      setFeedback("Capture arrêtée.");
    }
    return;
  }

  if (payload.type === "debug") {
    if (!state.logsWs || state.logsWs.readyState !== WebSocket.OPEN) {
      appendDebugLog(payload.message || "Log vide", { source: "live" });
    }
    return;
  }

  if (payload.type === "partial") {
    renderPartial(payload.timestamp, payload.text);
    setFeedback("Transcription en cours…");
    return;
  }

  if (payload.type === "final") {
    renderFinal(payload.timestamp, payload.text);
    setFeedback("Bloc de transcription ajouté.");
    return;
  }

  if (payload.type === "error") {
    state.isStarting = false;
    setStatus("error");
    rejectPendingStart(payload.message || "Erreur backend.");
    setFeedback(payload.message || "Erreur backend.");
  }
}

function handleLogsEvent(payload) {
  if (payload.type === "snapshot") {
    for (const event of payload.events || []) {
      appendServerLogEvent(event);
    }
    return;
  }

  if (payload.type === "event") {
    appendServerLogEvent(payload.event);
    if (payload.event?.code?.startsWith("batch.")) {
      refreshBatchJobs().catch((error) => {
        appendDebugLog(`Échec de mise à jour batch : ${error.message || error}`, { source: "batch", level: "ERROR" });
      });

      if (payload.event.code === "batch.completed" && payload.event.job_id) {
        fetchBatchTranscript(payload.event.job_id)
          .then((result) => {
            syncSandboxStateFromCurrentWorkbench();
            state.currentTranscriptFileName = result.job.output_file_name || null;
            resetWorkbench(result.transcript || "", `Source · ${result.job.file_name}`, "batch");
            if (elements.includeSummaryToggle?.checked && (result.transcript || "").trim()) {
              toggleSummaryOnCurrentVersion(true).catch(() => {});
            }
            setFeedback(`Transcription batch chargée depuis ${result.job.file_name}.`);
            refreshTranscriptList().catch(() => {});
          })
          .catch((error) => {
            appendDebugLog(`Transcript batch indisponible : ${error.message || error}`, { source: "batch", level: "ERROR" });
          });
      }
    }
  }
}

function connectLogsWebSocket() {
  if (state.logsWs && (state.logsWs.readyState === WebSocket.OPEN || state.logsWs.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const logsSocket = new WebSocket(`${protocol}://${window.location.host}/ws/logs`);
  state.logsWs = logsSocket;

  logsSocket.onopen = () => {
    appendDebugLog("Flux de logs serveur connecté", { source: "system" });
  };

  logsSocket.onmessage = (event) => {
    handleLogsEvent(JSON.parse(event.data));
  };

  logsSocket.onerror = () => {
    appendDebugLog("Erreur sur le flux de logs serveur", { source: "system", level: "ERROR" });
  };

  logsSocket.onclose = () => {
    if (state.logsWs === logsSocket) {
      state.logsWs = null;
    }

    if (state.logsReconnectTimer) {
      window.clearTimeout(state.logsReconnectTimer);
    }

    state.logsReconnectTimer = window.setTimeout(() => {
      connectLogsWebSocket();
    }, 2000);
  };
}

function ensureWebSocket() {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    return Promise.resolve();
  }

  if (state.wsReady) {
    return state.wsReady;
  }

  state.wsReady = new Promise((resolve, reject) => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    state.ws = new WebSocket(`${protocol}://${window.location.host}/ws/transcribe`);

    state.ws.onopen = () => {
      resolve();
      state.wsReady = null;
    };

    state.ws.onmessage = (event) => {
      handleServerEvent(JSON.parse(event.data));
    };

    state.ws.onerror = () => {
      appendDebugLog("Erreur WebSocket détectée côté navigateur");
      rejectPendingStart("WebSocket indisponible");
      reject(new Error("WebSocket indisponible"));
      state.wsReady = null;
    };

    state.ws.onclose = (event) => {
      state.ws = null;
      state.wsReady = null;
      rejectPendingStart(`Connexion interrompue (${event.code || "sans code"}).`);
      appendDebugLog(`WebSocket fermé · code ${event.code || "inconnu"} · raison ${event.reason || "non fournie"}`);
      if (state.isListening || state.isStarting) {
        state.isStarting = false;
        state.isListening = false;
        setStatus("error");
        setFeedback(`Connexion interrompue (${event.code || "sans code"}).`);
      }
      refreshButtons();
    };
  });

  return state.wsReady;
}

async function startMicrophone() {
  await ensureWebSocket();

  state.stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  state.audioContext = new AudioContext();
  await state.audioContext.audioWorklet.addModule("/static/audio-worklet.js");
  await state.audioContext.resume();
  appendDebugLog(`Microphone initialisé · sampleRate ${state.audioContext.sampleRate} Hz`);

  state.source = state.audioContext.createMediaStreamSource(state.stream);
  state.workletNode = new AudioWorkletNode(state.audioContext, "pcm-capture-processor");
  state.silentGain = state.audioContext.createGain();
  state.silentGain.gain.value = 0;

  state.workletNode.port.onmessage = (event) => {
    if (!state.isListening || !state.ws || state.ws.readyState !== WebSocket.OPEN) {
      return;
    }
    if (state.ws.bufferedAmount > 65536) {
      const now = Date.now();
      if (now - state.lastBufferedLogAt >= 2000) {
        appendDebugLog(`Chunk ignoré · bufferedAmount ${state.ws.bufferedAmount}`);
        state.lastBufferedLogAt = now;
      }
      return;
    }
    state.ws.send(encodeChunk(event.data, state.audioContext.sampleRate));
  };

  state.source.connect(state.workletNode);
  state.workletNode.connect(state.silentGain);
  state.silentGain.connect(state.audioContext.destination);

  await startAudioRecording();
}

async function stopMicrophone() {
  appendDebugLog("Arrêt du microphone demandé");
  let finalizedAudio = null;

  try {
    finalizedAudio = await finalizeAudioRecording();
    if (finalizedAudio?.file_name) {
      appendDebugLog(`Audio enregistré dans ${finalizedAudio.file_name}`);
    }
  } finally {
    if (state.workletNode) {
      state.workletNode.port.onmessage = null;
      state.workletNode.disconnect();
    }
    if (state.source) {
      state.source.disconnect();
    }
    if (state.silentGain) {
      state.silentGain.disconnect();
    }
    if (state.stream) {
      state.stream.getTracks().forEach((track) => track.stop());
    }
    if (state.audioContext) {
      await state.audioContext.close();
    }

    state.stream = null;
    state.audioContext = null;
    state.source = null;
    state.workletNode = null;
    state.silentGain = null;
  }

  return finalizedAudio;
}

async function loadOllamaModels() {
  elements.ollamaModelSelect.disabled = true;
  syncOllamaModelSelects();
  setOllamaStatus("Chargement des modèles de transcription…");

  try {
    const response = await fetch("/api/transcription/models");
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Impossible de charger les modèles de transcription.");
    }

    const payload = await response.json();
    elements.ollamaModelSelect.innerHTML = "";

    if (!payload.models.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "Aucun modèle disponible";
      elements.ollamaModelSelect.appendChild(option);
      elements.ollamaModelSelect.disabled = true;
      syncOllamaModelSelects();
      setOllamaStatus("Aucun modèle de transcription disponible.");
      appendDebugLog("Aucun modèle de transcription détecté par le backend");
      refreshButtons();
      return;
    }

    for (const modelName of payload.models) {
      const option = document.createElement("option");
      option.value = modelName;
      option.textContent = modelName;
      elements.ollamaModelSelect.appendChild(option);
    }

    elements.ollamaModelSelect.value = payload.current_model || payload.models[0];
    elements.ollamaModelSelect.disabled = false;
    syncOllamaModelSelects(elements.ollamaModelSelect.value);
    try {
      const ollamaResponse = await fetch("/api/ollama/models");
      if (!ollamaResponse.ok) {
        const ollamaPayload = await ollamaResponse.json();
        throw new Error(ollamaPayload.detail || "Modèles Ollama indisponibles.");
      }
      const ollamaPayload = await ollamaResponse.json();
      state.workbenchModelName = ollamaPayload.default_model || null;
      setOllamaStatus(
        `Whisper : ${getSelectedTranscriptionModel()} · Ollama : ${state.workbenchModelName || "aucun modèle local"}`
      );
    } catch (error) {
      state.workbenchModelName = null;
      setOllamaStatus(`Whisper : ${getSelectedTranscriptionModel()} · Ollama indisponible`);
      appendDebugLog(`Échec du chargement des modèles Ollama : ${error.message || error}`, { source: "ollama", level: "ERROR" });
    }
    appendDebugLog(`Modèles de transcription chargés · ${payload.models.join(", ")}`);
  } catch (error) {
    elements.ollamaModelSelect.innerHTML = "";
    const option = document.createElement("option");
      option.value = "";
    option.textContent = "Modèles indisponibles";
    elements.ollamaModelSelect.appendChild(option);
    elements.ollamaModelSelect.disabled = true;
    syncOllamaModelSelects();
    setOllamaStatus(error.message || "Modèles de transcription indisponibles.");
    appendDebugLog(`Échec du chargement des modèles de transcription : ${error.message || error}`);
  }

  refreshButtons();
}

async function startListening() {
  if (state.isListening || state.isStarting) {
    return;
  }

  try {
    const selectedModel = getSelectedTranscriptionModel();
    state.isStarting = true;
    state.isListening = false;
    updateRecordingVisualState();
    refreshButtons();
    setStatus("inactive");
    setFeedback(`Préparation du modèle ${selectedModel}…`);
    appendDebugLog(`Démarrage demandé · chargement du modèle ${selectedModel}`);

    await startMicrophone();
    removePartial();
    state.pendingStart = createDeferred();
    state.ws.send(JSON.stringify({ type: "start", model: selectedModel || undefined }));
    await state.pendingStart.promise;
    setFeedback(
      elements.recordAudioToggle.checked
        ? `Microphone actif, modèle ${selectedModel}, et son enregistré.`
        : `Microphone actif avec le modèle ${selectedModel}.`
    );
    startRecordingVisuals();
    refreshButtons();
  } catch (error) {
    rejectPendingStart(error.message || "Impossible de démarrer la capture.");
    state.isStarting = false;
    state.isListening = false;

    try {
      await stopMicrophone();
    } catch {
      // no-op: best effort cleanup only
    }

    setStatus("error");
    setFeedback(describeMicrophoneError(error));
    appendDebugLog(`Échec du démarrage : ${error.message || error}`);
    refreshButtons();
  }
}

async function stopListening() {
  if (!state.isListening && !state.isStarting) {
    return;
  }

  state.isStarting = false;
  state.isListening = false;
  updateRecordingVisualState();
  rejectPendingStart("Démarrage interrompu par l'utilisateur.");

  try {
    const savedAudio = await stopMicrophone();
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
      state.ws.send(JSON.stringify({ type: "stop" }));
    }
    setStatus("stopped");
    setFeedback(
      savedAudio?.file_name
        ? `Arrêt demandé, finalisation du dernier bloc… Son sauvegardé dans ${savedAudio.file_name}.`
        : "Arrêt demandé, finalisation du dernier bloc…"
    );
  } catch (error) {
    appendDebugLog(`Erreur lors de l'arrêt du microphone : ${error.message || error}`);
    setStatus("error");
    setFeedback(error.message || "Erreur lors de l'arrêt de la capture audio.");
  }

  refreshButtons();
}

async function saveTranscript() {
  const content = getEditorText();
  const savingFromSandbox = state.currentTranscriptFileName === null;
  if (!content) {
    setFeedback("Rien à sauvegarder.");
    refreshButtons();
    return;
  }

  appendDebugLog(`Sauvegarde demandée · ${content.length} caractères`);

  const response = await fetch("/api/save", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      content: serializeWorkbenchContentForStorage(content),
      base_name: state.currentRecordingBaseName,
    }),
  });

  if (!response.ok) {
    const payload = await response.json();
    throw new Error(payload.detail || "Échec de sauvegarde");
  }

  const payload = await response.json();
  if (savingFromSandbox) {
    resetSandboxState();
  }
  elements.lastSave.textContent = `Dernière sauvegarde : ${formatSavedAt(payload.saved_at)} · ${payload.file_name}`;
  state.currentTranscriptFileName = payload.file_name;
  resetWorkbench(getEditorText(), `Source · ${payload.file_name}`, "save");
  setFeedback(`Sauvegarde réussie dans ${payload.file_name}`);
  updateStats();
  await refreshTranscriptList();
}

async function runWorkbenchAction(operation, instruction = "") {
  const content = extractWorkbenchBaseContent(getEditorText());
  if (!content) {
    setFeedback("Aucune transcription à envoyer à l'IA.");
    refreshButtons();
    return;
  }

  state.isApplyingWorkbench = true;
  setSummaryOutput("Transformation du document en cours…", true);
  setFeedback("Transformation du document via IA locale…");
  appendDebugLog(`Transformation demandée · ${operation} · ${content.length} caractères`, { source: "workbench" });
  refreshButtons();

  try {
    const response = await fetch("/api/workbench/transform", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        content,
        operation,
        prompt: instruction || null,
        include_summary: Boolean(elements.includeSummaryToggle?.checked),
        model: state.workbenchModelName,
      }),
    });

    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Impossible de générer la réponse IA.");
    }

    const payload = await response.json();
    pushWorkbenchVersion(payload.output, payload.version_label || operation, operation);
    setFeedback(`Version générée avec ${payload.model || "IA locale"}.`);
  } catch (error) {
    setSummaryOutput("La transformation n'a pas pu être générée.", true);
    setFeedback(error.message || "Impossible de générer la transformation.");
    appendDebugLog(`Échec de transformation : ${error.message || error}`, { source: "workbench", level: "ERROR" });
  } finally {
    state.isApplyingWorkbench = false;
    refreshButtons();
  }
}

async function toggleSummaryOnCurrentVersion(enabled) {
  const currentVersion = getCurrentWorkbenchVersion();
  const currentContent = getEditorText();
  const baseContent = extractWorkbenchBaseContent(currentContent);
  if (!currentVersion || !baseContent.trim()) {
    return;
  }

  if (!enabled) {
    if (baseContent !== currentContent) {
      pushWorkbenchVersion(baseContent, `${currentVersion.label} sans résumé`, "summary-removed");
      setFeedback("Résumé retiré de la version courante.");
    }
    return;
  }

  if (baseContent !== currentContent) {
    return;
  }

  state.isApplyingWorkbench = true;
  setSummaryOutput("Ajout du résumé en cours…", true);
  refreshButtons();

  try {
    const response = await fetch("/api/workbench/transform", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        content: baseContent,
        operation: "summarize",
        include_summary: false,
        model: state.workbenchModelName,
      }),
    });

    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Impossible de générer le résumé.");
    }

    const payload = await response.json();
    const output = `Résumé\n\n${payload.output.trim()}\n\n---\n\n${baseContent}`;
    pushWorkbenchVersion(output, `${currentVersion.label} + résumé`, "summary-toggle");
    setFeedback(`Résumé ajouté avec ${payload.model || "IA locale"}.`);
  } catch (error) {
    elements.includeSummaryToggle.checked = false;
    setSummaryOutput("Le résumé n'a pas pu être ajouté.", true);
    setFeedback(error.message || "Impossible d'ajouter le résumé.");
    appendDebugLog(`Échec du résumé instantané : ${error.message || error}`, { source: "workbench", level: "ERROR" });
  } finally {
    state.isApplyingWorkbench = false;
    refreshButtons();
  }
}

async function openHistoryFolder() {
  await openFolder("/api/history/open", "Output");
  setFeedback(`Dossier ouvert : ${state.historyPath}`);
}

elements.start.addEventListener("click", () => {
  if (state.isListening) {
    stopListening();
    return;
  }

  startListening();
});

elements.clear.addEventListener("click", () => {
  if (!getEditorText()) {
    return;
  }
  elements.editor.innerHTML = "";
  removePartial();
  state.currentRecordingBaseName = null;
  state.currentTranscriptFileName = null;
  resetSandboxState();
  resetWorkbench("", "Sandbox", "sandbox");
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify({ type: "reset" }));
  }
  setFeedback("Transcription effacée.");
  appendDebugLog("Effacement immédiat de la transcription demandé");
  updateStats();
  refreshButtons();
});

elements.save.addEventListener("click", async () => {
  try {
    await saveTranscript();
  } catch (error) {
    setStatus("error");
    setFeedback(error.message || "Erreur de sauvegarde.");
  }
});

elements.formatBtn?.addEventListener("click", async () => {
  await runWorkbenchAction("format");
});

elements.rewriteBtn?.addEventListener("click", async () => {
  await runWorkbenchAction("rewrite");
});

elements.customTransformBtn?.addEventListener("click", async () => {
  await runWorkbenchAction("custom", elements.aiPrompt.value);
});

elements.undoVersionBtn?.addEventListener("click", () => {
  applyWorkbenchVersion(state.workbenchIndex - 1);
});

elements.redoVersionBtn?.addEventListener("click", () => {
  applyWorkbenchVersion(state.workbenchIndex + 1);
});

elements.includeSummaryToggle?.addEventListener("change", async () => {
  await toggleSummaryOnCurrentVersion(elements.includeSummaryToggle.checked);
});

elements.openHistory.addEventListener("click", async () => {
  try {
    await openHistoryFolder();
  } catch (error) {
    setStatus("error");
    setFeedback(error.message || "Impossible d'ouvrir le dossier Output.");
  }
});

elements.openInput?.addEventListener("click", async () => {
  try {
    await openFolder("/api/input/open", "Input");
    setFeedback("Dossier Input ouvert.");
  } catch (error) {
    setStatus("error");
    setFeedback(error.message || "Impossible d'ouvrir le dossier Input.");
  }
});

elements.openTrash?.addEventListener("click", async () => {
  try {
    await openFolder("/api/trash/open", "Trash");
    setFeedback("Dossier Trash ouvert.");
  } catch (error) {
    setStatus("error");
    setFeedback(error.message || "Impossible d'ouvrir le dossier Trash.");
  }
});

elements.batchDropZone?.addEventListener("click", () => {
  elements.batchFileInput?.click();
});

elements.batchFileInput?.addEventListener("change", async (event) => {
  const files = event.target.files;
  try {
    await uploadBatchFiles(files);
    setFeedback(`${files?.length || 0} fichier(s) ajouté(s) à la file batch.`);
  } catch (error) {
    setStatus("error");
    setFeedback(error.message || "Impossible d'ajouter les fichiers batch.");
  } finally {
    event.target.value = "";
  }
});

for (const eventName of ["dragenter", "dragover"]) {
  elements.batchDropZone?.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.batchDropZone.classList.add("is-dragover");
  });
}

for (const eventName of ["dragleave", "dragend", "drop"]) {
  elements.batchDropZone?.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.batchDropZone.classList.remove("is-dragover");
  });
}

elements.batchDropZone?.addEventListener("drop", async (event) => {
  const files = event.dataTransfer?.files;
  try {
    await uploadBatchFiles(files);
    setFeedback(`${files?.length || 0} fichier(s) ajouté(s) à la file batch.`);
  } catch (error) {
    setStatus("error");
    setFeedback(error.message || "Impossible d'ajouter les fichiers batch.");
  }
});

for (const select of elements.ollamaModelSelects) {
  select.addEventListener("change", (event) => {
    const selectedValue = event.currentTarget.value || "";
    if (elements.ollamaModelSelect && event.currentTarget !== elements.ollamaModelSelect) {
      elements.ollamaModelSelect.value = selectedValue;
    }
    syncOllamaModelSelects(selectedValue);
    if (selectedValue) {
      setOllamaStatus(`Whisper : ${selectedValue} · Ollama : ${state.workbenchModelName || "inconnu"}`);
      appendDebugLog(`Modèle de transcription sélectionné : ${selectedValue}`);
    }
    refreshButtons();
  });
}

elements.recordAudioToggle.addEventListener("change", () => {
  appendDebugLog(
    elements.recordAudioToggle.checked ? "Option d'enregistrement audio activée" : "Option d'enregistrement audio désactivée"
  );
});

for (const button of elements.rightTabs) {
  button.addEventListener("click", () => {
    setActivePanelTab(button.dataset.panelTab || "recording");
  });
}

elements.editor.addEventListener("input", () => {
  state.isCurrentTranscriptDirty = true;
  scheduleEditorSnapshot();
  updateStats();
  refreshButtons();
});

elements.aiPrompt.addEventListener("input", () => {
  refreshButtons();
});

window.addEventListener("beforeunload", () => {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.close();
  }

  if (state.logsWs && state.logsWs.readyState === WebSocket.OPEN) {
    state.logsWs.close();
  }
});

// Sort hotwords alphabetically on startup
const hotwordsEl = document.getElementById("hotwords");
if (hotwordsEl) {
  hotwordsEl.value = hotwordsEl.value
    .split("\n")
    .map((w) => w.trim())
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, "fr", { sensitivity: "base" }))
    .join("\n");
}

setStatus("inactive");
setActivePanelTab("recording");
randomizeWaveformBars();
setSummaryOutput("Les informations sur la version courante apparaitront ici.", true);
setLogsCollapsed(false);
updateStats();
appendDebugLog("Interface chargée");
resetWorkbench("", "Sandbox", "sandbox");
refreshButtons();
connectLogsWebSocket();
loadOllamaModels();
refreshBatchJobs().catch((error) => {
  appendDebugLog(`Échec du chargement batch : ${error.message || error}`, { source: "batch", level: "ERROR" });
});
refreshTranscriptList().catch((error) => {
  appendDebugLog(`Échec du chargement des transcriptions : ${error.message || error}`, { source: "library", level: "ERROR" });
});
