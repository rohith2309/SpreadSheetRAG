const sessionButtons = [
  document.querySelector("#new-session"),
  document.querySelector("#new-session-main"),
];
const sessionStatus = document.querySelector("#session-status");
const sessionLabel = document.querySelector("#session-label");
const fileInput = document.querySelector("#file-input");
const dropzone = document.querySelector("#dropzone");
const uploadTitle = document.querySelector("#upload-title-text");
const uploadHelp = document.querySelector("#upload-help");
const uploadFeedback = document.querySelector("#upload-feedback");
const chatCard = document.querySelector("#chat-card");
const chatSubtitle = document.querySelector("#chat-subtitle");
const filePill = document.querySelector("#file-pill");
const conversation = document.querySelector("#conversation");
const emptyChat = document.querySelector("#empty-chat");
const chatForm = document.querySelector("#chat-form");
const messageInput = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const API_BASE_URL = (window.APP_CONFIG?.API_BASE_URL || window.location.origin).replace(/\/+$/, "");

let sessionId = null;
let uploadedFile = false;
let socket = null;
let waitingForReply = false;

function setFeedback(message, kind = "") {
  uploadFeedback.textContent = message;
  uploadFeedback.className = `feedback${message ? " is-visible" : ""}${kind ? ` is-${kind}` : ""}`;
}

function formatError(error) {
  if (error instanceof TypeError) {
    const origin = window.location.origin;
    return `Could not reach the API at ${API_BASE_URL}. If the browser blocked the response, add this frontend origin to the backend's FRONTEND_ORIGINS setting: ${origin}`;
  }
  return error.message || "Something went wrong. Please try again.";
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

function closeSocket() {
  if (socket && socket.readyState < WebSocket.CLOSING) {
    socket.close();
  }
  socket = null;
  waitingForReply = false;
  updateSendButton();
}

function updateSendButton() {
  const ready = uploadedFile && messageInput.value.trim() && !waitingForReply;
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

function setSession(session) {
  closeSocket();
  sessionId = session;
  uploadedFile = false;
  fileInput.disabled = false;
  fileInput.value = "";
  dropzone.classList.remove("is-disabled");
  sessionStatus.classList.add("is-active");
  sessionLabel.textContent = `Session ${session.slice(0, 8)}`;
  uploadTitle.textContent = "Choose a spreadsheet to upload";
  uploadHelp.textContent = "Excel files · .xlsx or .xls";
  chatCard.classList.add("is-locked");
  chatSubtitle.textContent = "Upload a spreadsheet to start a conversation.";
  filePill.hidden = true;
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
      "This page is opened as a local file, which browsers block from calling the API. Serve the frontend over HTTP (for example, http://localhost:3000) and allow that origin in the backend's FRONTEND_ORIGINS setting.",
      "error",
    );
    return;
  }

  const buttons = sessionButtons.filter(Boolean);
  buttons.forEach((button) => {
    button.disabled = true;
    button.dataset.originalText ??= button.textContent;
    button.textContent = "Creating...";
  });
  setFeedback("");

  try {
    const response = await fetch(`${API_BASE_URL}/sessions`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.msg || "Could not create a session.");
    }
    if (!data.session_id) {
      throw new Error("The API did not return a session ID.");
    }
    setSession(data.session_id);
  } catch (error) {
    setFeedback(formatError(error), "error");
  } finally {
    buttons.forEach((button) => {
      button.disabled = false;
      button.innerHTML = button.id === "new-session"
        ? '<span aria-hidden="true">+</span> New analysis'
        : 'Create session <span aria-hidden="true">→</span>';
    });
  }
}

async function uploadFile(file) {
  if (!sessionId || !file) return;

  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!["xlsx", "xls"].includes(extension)) {
    setFeedback("Choose an Excel spreadsheet (.xlsx or .xls).", "error");
    fileInput.value = "";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  fileInput.disabled = true;
  uploadTitle.textContent = "Uploading your spreadsheet...";
  setFeedback("");

  try {
    const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "The spreadsheet could not be uploaded.");
    }

    uploadedFile = true;
    uploadTitle.textContent = file.name;
    uploadHelp.textContent = "Uploaded and ready to explore";
    chatCard.classList.remove("is-locked");
    chatSubtitle.textContent = "Ask a question and get an answer grounded in your spreadsheet.";
    filePill.textContent = file.name;
    filePill.hidden = false;
    messageInput.disabled = false;
    messageInput.focus();
    setFeedback(data.message || "Spreadsheet uploaded successfully.", "success");
  } catch (error) {
    uploadTitle.textContent = "Choose a spreadsheet to upload";
    uploadHelp.textContent = "Excel files · .xlsx or .xls";
    fileInput.disabled = false;
    fileInput.value = "";
    setFeedback(formatError(error), "error");
  }
}

function connectAndSend(message) {
  if (!sessionId || !uploadedFile || waitingForReply) return;

  showMessage(message, "user");
  messageInput.value = "";
  waitingForReply = true;
  updateSendButton();
  const pendingMessage = showMessage("Thinking...", "assistant");

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
      pendingMessage.textContent = "The server returned an unreadable response.";
      pendingMessage.classList.add("message-error");
      return;
    }

    const responseText = getResponseText(data.error || data.message);
    pendingMessage.textContent = responseText || "The workflow returned no readable text response.";
    if (data.error) pendingMessage.classList.add("message-error");
    waitingForReply = false;
    updateSendButton();
    messageInput.focus();
  });

  activeSocket.addEventListener("error", () => {
    if (socket !== activeSocket) return;
    pendingMessage.textContent = "Could not connect to the workflow. Check that the backend is running.";
    pendingMessage.classList.add("message-error");
  });

  activeSocket.addEventListener("close", () => {
    if (socket !== activeSocket) return;
    if (waitingForReply) {
      pendingMessage.textContent = "The connection closed before a response arrived. Please try again.";
      pendingMessage.classList.add("message-error");
      waitingForReply = false;
      updateSendButton();
    }
    socket = null;
  });
}

sessionButtons.forEach((button) => button?.addEventListener("click", createSession));
fileInput.addEventListener("change", () => uploadFile(fileInput.files[0]));
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
  const [file] = event.dataTransfer.files;
  if (file) uploadFile(file);
});
