const sessionButtons = [
  document.querySelector("#new-session"),
  document.querySelector("#new-session-main"),
];
const sessionStatus = document.querySelector("#session-status");
const sessionLabel = document.querySelector("#session-label");
const topbarSession = document.querySelector("#topbar-session");
const fileInput = document.querySelector("#file-input");
const dropzone = document.querySelector("#dropzone");
const uploadTitle = document.querySelector("#upload-title-text");
const uploadHelp = document.querySelector("#upload-help");
const uploadedFilesList = document.querySelector("#uploaded-files-list");
const uploadFeedback = document.querySelector("#upload-feedback");
const chatCard = document.querySelector("#chat-card");
const chatSubtitle = document.querySelector("#chat-subtitle");
const pillsContainer = document.querySelector("#pills-container");
const filePill = document.querySelector("#file-pill");
const conversation = document.querySelector("#conversation");
const emptyChat = document.querySelector("#empty-chat");
const chatForm = document.querySelector("#chat-form");
const messageInput = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const API_BASE_URL = (window.APP_CONFIG?.API_BASE_URL || window.location.origin).replace(/\/+$/, "");

let sessionId = null;
const uploadedFiles = new Map(); // key: filename -> { file, name, status, error }
let socket = null;
let waitingForReply = false;
let currentPendingMessage = null;

function setFeedback(message, kind = "") {
  uploadFeedback.textContent = message;
  uploadFeedback.className = `feedback${message ? " is-visible" : ""}${kind ? ` is-${kind}` : ""}`;
}

function formatError(error) {
  if (error instanceof TypeError) {
    const origin = window.location.origin;
    return `Could not reach API at ${API_BASE_URL}. Ensure the backend is running and ${origin} is in FRONTEND_ORIGINS.`;
  }
  return error.message || "An unexpected error occurred. Please try again.";
}

function getResponseText(content) {
  let text = "";

  if (typeof content === "string") {
    text = content;
  } else if (Array.isArray(content)) {
    text = content
      .map((part) => {
        if (typeof part === "string") return part;
        if (part && typeof part.text === "string") return part.text;
        return "";
      })
      .filter(Boolean)
      .join("\n");
  } else if (content && typeof content.text === "string") {
    text = content.text;
  }

  return text.replace(/<thinking>[\s\S]*?<\/thinking>/gi, "").trim();
}

function getReadyFiles() {
  return Array.from(uploadedFiles.values()).filter((f) => f.status === "ready");
}

function hasReadyFiles() {
  return getReadyFiles().length > 0;
}

function closeSocket() {
  if (socket && socket.readyState < WebSocket.CLOSING) {
    socket.close();
  }
  socket = null;
  waitingForReply = false;
  currentPendingMessage = null;
  updateSendButton();
}

function updateSendButton() {
  const ready = hasReadyFiles() && messageInput.value.trim() && !waitingForReply;
  sendButton.disabled = !ready;
}

function showMessage(text, kind) {
  emptyChat.hidden = true;
  const message = document.createElement("div");
  message.className = `message message-${kind}`;
  message.textContent = text;
  conversation.append(message);
  conversation.scrollTop = conversation.scrollHeight;
  return message;
}

function renderPills() {
  if (!pillsContainer) return;
  pillsContainer.innerHTML = "";
  const readyFiles = getReadyFiles();

  if (readyFiles.length === 0) {
    if (filePill) filePill.hidden = true;
    return;
  }

  if (readyFiles.length <= 3) {
    for (const file of readyFiles) {
      const pill = document.createElement("span");
      pill.className = "ready-pill";
      pill.textContent = file.name;
      pill.title = file.name;
      pillsContainer.append(pill);
    }
  } else {
    for (const file of readyFiles.slice(0, 2)) {
      const pill = document.createElement("span");
      pill.className = "ready-pill";
      pill.textContent = file.name;
      pill.title = file.name;
      pillsContainer.append(pill);
    }
    const morePill = document.createElement("span");
    morePill.className = "ready-pill";
    morePill.textContent = `+${readyFiles.length - 2} more`;
    morePill.title = readyFiles.slice(2).map((f) => f.name).join(", ");
    pillsContainer.append(morePill);
  }
}

function renderFilesList() {
  if (!uploadedFilesList) return;

  if (uploadedFiles.size === 0) {
    uploadedFilesList.hidden = true;
    uploadedFilesList.innerHTML = "";
    return;
  }

  uploadedFilesList.hidden = false;
  uploadedFilesList.innerHTML = "";

  for (const fileInfo of uploadedFiles.values()) {
    const item = document.createElement("div");
    item.className = "file-item";

    const info = document.createElement("div");
    info.className = "file-item-info";

    const icon = document.createElement("span");
    icon.className = "file-item-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <rect x="3" y="3" width="18" height="18" rx="3"/>
        <path d="M3 9h18M9 9v12M15 9v12M3 15h18"/>
      </svg>
    `;

    const name = document.createElement("span");
    name.className = "file-item-name";
    name.textContent = fileInfo.name;
    name.title = fileInfo.name;

    info.append(icon, name);

    const status = document.createElement("span");
    status.className = `file-item-status is-${fileInfo.status}`;

    if (fileInfo.status === "uploading") {
      status.innerHTML = `<span class="spinner" aria-hidden="true"></span> Uploading`;
    } else if (fileInfo.status === "ready") {
      status.innerHTML = `✓ Ready`;
    } else if (fileInfo.status === "error") {
      status.textContent = "✕ Failed";
      status.title = fileInfo.error || "Failed to upload";
    }

    item.append(info, status);
    uploadedFilesList.append(item);
  }
}

function updateUIState() {
  const readyFiles = getReadyFiles();
  const hasFiles = readyFiles.length > 0;
  const isAnyUploading = Array.from(uploadedFiles.values()).some((f) => f.status === "uploading");

  if (isAnyUploading) {
    uploadTitle.textContent = "Uploading spreadsheets...";
    uploadHelp.textContent = "Processing and indexing sheets...";
  } else if (hasFiles) {
    uploadTitle.textContent = "Add more spreadsheets";
    uploadHelp.textContent = `${readyFiles.length} spreadsheet${readyFiles.length > 1 ? "s" : ""} active · Click or drop files to add`;
  } else {
    uploadTitle.textContent = "Choose spreadsheets to upload";
    uploadHelp.textContent = "Drop .xlsx or .xls files here, or click to browse";
  }

  if (hasFiles) {
    chatCard.classList.remove("is-locked");
    chatSubtitle.textContent = readyFiles.length === 1
      ? "Query your spreadsheet with natural language."
      : `Query across ${readyFiles.length} active spreadsheets.`;
    messageInput.disabled = false;
  } else {
    chatCard.classList.add("is-locked");
    chatSubtitle.textContent = "Upload spreadsheets to begin interactive queries.";
    messageInput.disabled = true;
  }

  renderPills();
  updateSendButton();
}

function setSession(session) {
  closeSocket();
  sessionId = session;
  uploadedFiles.clear();
  renderFilesList();
  renderPills();

  fileInput.disabled = false;
  fileInput.value = "";
  dropzone.classList.remove("is-disabled");
  sessionStatus.classList.add("is-active");
  sessionLabel.textContent = `Session: ${session.slice(0, 8)}`;
  if (topbarSession) topbarSession.textContent = `Session ${session.slice(0, 8)}`;
  uploadTitle.textContent = "Choose spreadsheets to upload";
  uploadHelp.textContent = "Drop .xlsx or .xls files here, or click to browse";
  chatCard.classList.add("is-locked");
  chatSubtitle.textContent = "Upload spreadsheets to begin interactive queries.";
  if (filePill) filePill.hidden = true;
  messageInput.value = "";
  messageInput.disabled = true;
  conversation.replaceChildren(emptyChat);
  emptyChat.hidden = false;
  setFeedback("");
  updateSendButton();
}

async function createSession() {
  if (window.location.protocol === "file:") {
    setFeedback(
      "Served over local file protocol. Please serve via HTTP (e.g., http://localhost:3000) and allow origin in FRONTEND_ORIGINS.",
      "error",
    );
    return;
  }

  const buttons = sessionButtons.filter(Boolean);
  buttons.forEach((button) => {
    button.disabled = true;
    button.dataset.originalText ??= button.textContent;
    button.textContent = "Initializing...";
  });
  setFeedback("");

  try {
    const response = await fetch(`${API_BASE_URL}/sessions`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.msg || "Could not initialize session.");
    }
    if (!data.session_id) {
      throw new Error("No session ID returned from API.");
    }
    setSession(data.session_id);
  } catch (error) {
    setFeedback(formatError(error), "error");
  } finally {
    buttons.forEach((button) => {
      button.disabled = false;
      button.innerHTML = button.id === "new-session"
        ? '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg><span>New analysis</span><kbd class="shortcut">N</kbd>'
        : '<span>Initialize session</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="arrow-icon"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';
    });
  }
}

async function uploadFiles(filesList) {
  if (!sessionId || !filesList || !filesList.length) return;

  const validFiles = [];
  const invalidFiles = [];

  for (const file of filesList) {
    const extension = file.name.split(".").pop()?.toLowerCase();
    if (["xlsx", "xls"].includes(extension)) {
      validFiles.push(file);
    } else {
      invalidFiles.push(file.name);
    }
  }

  if (invalidFiles.length > 0) {
    setFeedback(`Unsupported format skipped: ${invalidFiles.join(", ")}. Use .xlsx or .xls files.`, "error");
  } else {
    setFeedback("");
  }

  if (validFiles.length === 0) {
    fileInput.value = "";
    return;
  }

  for (const file of validFiles) {
    uploadedFiles.set(file.name, {
      file,
      name: file.name,
      status: "uploading",
      error: null,
    });
  }
  renderFilesList();
  updateUIState();

  await Promise.all(
    validFiles.map(async (file) => {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}/upload`, {
          method: "POST",
          body: formData,
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || data.msg || "Spreadsheet upload failed.");
        }
        uploadedFiles.set(file.name, {
          file,
          name: file.name,
          status: "ready",
          error: null,
        });
      } catch (error) {
        uploadedFiles.set(file.name, {
          file,
          name: file.name,
          status: "error",
          error: formatError(error),
        });
      }
      renderFilesList();
      updateUIState();
    })
  );

  fileInput.value = "";
  fileInput.disabled = false;

  const readyFiles = getReadyFiles();
  const errors = Array.from(uploadedFiles.values()).filter((f) => f.status === "error");

  if (errors.length > 0 && readyFiles.length === 0) {
    setFeedback("Failed to process workbook(s). Check format and try again.", "error");
  } else if (errors.length > 0) {
    setFeedback(`${readyFiles.length} file(s) ready, ${errors.length} failed.`, "error");
  } else {
    setFeedback(
      `${readyFiles.length} workbook${readyFiles.length > 1 ? "s" : ""} indexed and ready for analysis.`,
      "success"
    );
  }
}

function connectAndSend(message) {
  if (!sessionId || !hasReadyFiles() || waitingForReply) return;

  showMessage(message, "user");
  messageInput.value = "";
  waitingForReply = true;
  updateSendButton();
  currentPendingMessage = showMessage("Running Pandas analysis...", "assistant");

  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ message }));
    return;
  }

  if (socket) {
    try {
      socket.close();
    } catch {
      // ignore
    }
    socket = null;
  }

  const url = new URL(`/ws/${encodeURIComponent(sessionId)}`, API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const activeSocket = new WebSocket(url);
  socket = activeSocket;

  activeSocket.addEventListener("open", () => {
    if (socket !== activeSocket) return;
    activeSocket.send(JSON.stringify({ message }));
  });

  activeSocket.addEventListener("message", (event) => {
    if (socket !== activeSocket) return;
    let data;
    try {
      data = JSON.parse(event.data);
    } catch {
      if (currentPendingMessage) {
        currentPendingMessage.textContent = "Received invalid response from workflow.";
        currentPendingMessage.classList.add("message-error");
        currentPendingMessage = null;
      }
      waitingForReply = false;
      updateSendButton();
      return;
    }

    const responseText = getResponseText(data.error || data.message);
    if (currentPendingMessage) {
      currentPendingMessage.textContent = responseText || "Workflow returned no output.";
      if (data.error) currentPendingMessage.classList.add("message-error");
      currentPendingMessage = null;
    }
    waitingForReply = false;
    updateSendButton();
    messageInput.focus();
  });

  activeSocket.addEventListener("error", () => {
    if (socket !== activeSocket) return;
    if (currentPendingMessage) {
      currentPendingMessage.textContent = "Workflow connection error. Verify backend status.";
      currentPendingMessage.classList.add("message-error");
      currentPendingMessage = null;
    }
    waitingForReply = false;
    updateSendButton();
  });

  activeSocket.addEventListener("close", () => {
    if (socket !== activeSocket) return;
    if (waitingForReply && currentPendingMessage) {
      currentPendingMessage.textContent = "Connection closed before query finished. Please retry.";
      currentPendingMessage.classList.add("message-error");
      currentPendingMessage = null;
      waitingForReply = false;
      updateSendButton();
    }
    socket = null;
  });
}

// Click suggestion chip to fill input
emptyChat?.addEventListener("click", (e) => {
  const chip = e.target.closest(".prompt-chip");
  if (chip && !messageInput.disabled) {
    messageInput.value = chip.dataset.prompt || chip.textContent.trim();
    messageInput.focus();
    updateSendButton();
  }
});

// Shortcut 'N' for new analysis
window.addEventListener("keydown", (e) => {
  if (
    (e.key === "n" || e.key === "N") &&
    !e.ctrlKey &&
    !e.metaKey &&
    !["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)
  ) {
    e.preventDefault();
    createSession();
  }
});

sessionButtons.forEach((button) => button?.addEventListener("click", createSession));

fileInput.addEventListener("change", () => {
  const files = Array.from(fileInput.files || []);
  if (files.length) uploadFiles(files);
});

fileInput.addEventListener("cancel", () => setFeedback(""));

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (message) connectAndSend(message);
});

messageInput.addEventListener("input", updateSendButton);

dropzone.addEventListener("dragover", (event) => {
  if (!sessionId) return;
  event.preventDefault();
  dropzone.classList.add("is-dragging");
});

dropzone.addEventListener("dragleave", () => dropzone.classList.remove("is-dragging"));

dropzone.addEventListener("drop", (event) => {
  dropzone.classList.remove("is-dragging");
  if (!sessionId) return;
  event.preventDefault();
  const files = Array.from(event.dataTransfer.files || []);
  if (files.length) uploadFiles(files);
});
