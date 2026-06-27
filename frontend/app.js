// ════════════════════════════════════════════════════════════
// H-RAG Chat Interface — App Logic
// ════════════════════════════════════════════════════════════

const chatMessages = document.getElementById("chatMessages");
const queryInput = document.getElementById("queryInput");
const sendBtn = document.getElementById("sendBtn");
const chatForm = document.getElementById("chatForm");

let isLoading = false;
let defaultSystemPrompt = ""; // Store the original prompt for reset

// ── Initialize ──────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    loadSystemPrompt();
});

// ── Auto-resize textarea ────────────────────────────────────

queryInput.addEventListener("input", () => {
    queryInput.style.height = "auto";
    queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + "px";
});

queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event("submit"));
    }
});

// ── System Prompt Management ────────────────────────────────

function togglePromptEditor() {
    const panel = document.getElementById("promptPanel");
    const toggle = document.getElementById("promptToggle");
    panel.classList.toggle("open");
    toggle.classList.toggle("open");
}

async function loadSystemPrompt() {
    try {
        const res = await fetch("/api/system-prompt");
        const data = await res.json();
        const textarea = document.getElementById("systemPromptInput");
        textarea.value = data.prompt || "";
        defaultSystemPrompt = data.prompt || "";
    } catch (err) {
        console.error("Failed to load system prompt:", err);
    }
}

async function saveSystemPrompt() {
    const textarea = document.getElementById("systemPromptInput");
    const statusEl = document.getElementById("promptStatus");
    const btn = document.getElementById("savePromptBtn");
    const prompt = textarea.value.trim();

    if (!prompt) {
        showPromptStatus("Prompt cannot be empty", "error");
        return;
    }

    btn.disabled = true;
    btn.textContent = "Saving...";

    try {
        const res = await fetch("/api/system-prompt", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt }),
        });

        const data = await res.json();
        if (data.status === "ok") {
            showPromptStatus("Saved successfully", "success");
            defaultSystemPrompt = prompt;
        } else {
            showPromptStatus(data.error || "Save failed", "error");
        }
    } catch (err) {
        showPromptStatus("Connection error", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Save";
    }
}

function resetSystemPrompt() {
    const textarea = document.getElementById("systemPromptInput");
    textarea.value = defaultSystemPrompt;
    showPromptStatus("Reset to last saved version", "info");
}

function showPromptStatus(msg, type) {
    const el = document.getElementById("promptStatus");
    el.textContent = msg;
    el.className = "prompt-status " + type;
    setTimeout(() => {
        el.textContent = "";
        el.className = "prompt-status";
    }, 3000);
}

// ── Suggestion chips ────────────────────────────────────────

function askSuggestion(el) {
    if (isLoading) return;
    queryInput.value = el.textContent;
    chatForm.dispatchEvent(new Event("submit"));
}

// ── Submit handler ──────────────────────────────────────────

async function handleSubmit(e) {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query || isLoading) return;

    // Clear welcome message on first query
    const welcome = document.querySelector(".welcome-message");
    if (welcome) welcome.remove();

    // Add user message
    addMessage(query, "user");

    // Clear input
    queryInput.value = "";
    queryInput.style.height = "auto";

    // Show typing indicator
    const typingId = showTyping();

    // Disable input
    setLoading(true);

    try {
        const response = await fetch("/api/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                query,
                nodes: ["anthropic", "projects"]
            }),
        });

        const data = await response.json();
        removeTyping(typingId);

        if (data.error) {
            addMessage("Sorry, something went wrong: " + data.error, "bot");
        } else {
            addBotMessage(data);
        }
    } catch (err) {
        removeTyping(typingId);
        addMessage("Failed to connect to the server. Make sure the API is running.", "bot");
    } finally {
        setLoading(false);
        queryInput.focus();
    }
}

// ── Message rendering ───────────────────────────────────────

function addMessage(text, role) {
    const msg = document.createElement("div");
    msg.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";

    if (role === "user") {
        avatar.textContent = "U";
    } else {
        avatar.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="currentColor" opacity="0.9"/>
            <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" fill="none" opacity="0.5"/>
            <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" fill="none" opacity="0.7"/>
        </svg>`;
    }

    const content = document.createElement("div");
    content.className = "message-content";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    if (role === "user") {
        bubble.textContent = text;
    } else {
        bubble.innerHTML = formatMarkdown(text);
    }

    content.appendChild(bubble);
    msg.appendChild(avatar);
    msg.appendChild(content);
    chatMessages.appendChild(msg);
    scrollToBottom();
}

function addBotMessage(data) {
    const msg = document.createElement("div");
    msg.className = "message bot";

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="currentColor" opacity="0.9"/>
        <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" fill="none" opacity="0.5"/>
        <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" fill="none" opacity="0.7"/>
    </svg>`;

    const content = document.createElement("div");
    content.className = "message-content";

    // Answer bubble
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = formatMarkdown(data.answer);
    content.appendChild(bubble);

    // Sources
    if (data.sources && data.sources.length > 0) {
        const sources = document.createElement("div");
        sources.className = "sources";

        data.sources.forEach((src) => {
            const badge = document.createElement("span");
            badge.className = "source-badge";
            badge.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
            </svg>${src.file}`;
            sources.appendChild(badge);
        });

        content.appendChild(sources);
    }

    // Retrieval path
    if (data.retrieval_path) {
        const path = document.createElement("div");
        path.className = "retrieval-path";
        path.innerHTML = `
            <span>F ${data.retrieval_path.folders} folders</span>
            <span>-></span>
            <span>D ${data.retrieval_path.documents} docs</span>
            <span>-></span>
            <span>C ${data.retrieval_path.chunks} chunks</span>
        `;
        content.appendChild(path);
    }

    msg.appendChild(avatar);
    msg.appendChild(content);
    chatMessages.appendChild(msg);
    scrollToBottom();
}

// ── Typing indicator ────────────────────────────────────────

let typingCounter = 0;

function showTyping() {
    const id = `typing-${++typingCounter}`;
    const msg = document.createElement("div");
    msg.className = "message bot";
    msg.id = id;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="currentColor" opacity="0.9"/>
        <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" fill="none" opacity="0.5"/>
        <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" fill="none" opacity="0.7"/>
    </svg>`;

    const content = document.createElement("div");
    content.className = "message-content";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble typing-indicator";
    bubble.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;

    content.appendChild(bubble);
    msg.appendChild(avatar);
    msg.appendChild(content);
    chatMessages.appendChild(msg);
    scrollToBottom();

    return id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ── Utilities ───────────────────────────────────────────────

function setLoading(loading) {
    isLoading = loading;
    sendBtn.disabled = loading;
    queryInput.disabled = loading;
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

function formatMarkdown(text) {
    // Simple markdown-to-HTML conversion
    let html = text
        // Code blocks
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Source citations — highlight them
        .replace(/\[Source:\s*([^\]]+)\]/g, '<span class="citation">[Source: $1]</span>')
        // Unordered lists
        .replace(/^\s*[-]\s+(.+)/gm, '<li>$1</li>')
        // Ordered lists
        .replace(/^\s*\d+\.\s+(.+)/gm, '<li>$1</li>')
        // Wrap consecutive <li> in <ul>
        .replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
        // Paragraphs (double newline)
        .replace(/\n\n/g, '</p><p>')
        // Single newline
        .replace(/\n/g, '<br>');

    // Wrap in paragraph if not already wrapped
    if (!html.startsWith('<')) {
        html = '<p>' + html + '</p>';
    }

    return html;
}
