// ===== AUTH =====

function getToken()    { return localStorage.getItem("token"); }
function getUsername() { return localStorage.getItem("username"); }
function getRole()     { return localStorage.getItem("role"); }

function checkAuth() {
    if (!getToken()) { window.location.href = "login.html"; return false; }
    return true;
}

function getHeaders() {
    return { "Authorization": `Bearer ${getToken()}`, "Content-Type": "application/json" };
}

async function logout() {
    try {
        await fetch(`${API_BASE}/logout`, { method: "POST", headers: getHeaders() });
    } catch {}
    localStorage.clear();
    window.location.href = "login.html";
}

// ===== INIT =====

const QUICK_QUESTIONS = {
    employee: ["What is the leave policy?", "How many sick days do I get?", "What is the WFH policy?", "What is the code of conduct?"],
    hr:       ["What is the recruitment process?", "How is payroll calculated?", "What are the selection criteria?"],
    manager:  ["What is the performance review process?", "What are the promotion criteria?", "How do I evaluate an employee?"],
    admin:    ["Show me all user stats", "What are the system metrics?", "Summarise all policies"],
};

function initApp() {
    if (!checkAuth()) return;

    const username = getUsername();
    const role     = getRole();

    document.getElementById("userName").textContent    = username;
    document.getElementById("userAvatar").textContent  = username.charAt(0).toUpperCase();
    document.getElementById("userRoleBadge").textContent = role.charAt(0).toUpperCase() + role.slice(1);

    // Quick questions
    const qqEl = document.getElementById("quickQuestions");
    (QUICK_QUESTIONS[role] || []).forEach(q => {
        const btn = document.createElement("button");
        btn.className = "quick-q-btn";
        btn.textContent = q;
        btn.onclick = () => { fillInput(q); switchView("chat"); sendMessage(); };
        qqEl.appendChild(btn);
    });

    // Auto-expand textarea
    const ta = document.getElementById("userInput");
    ta.addEventListener("input", () => { ta.style.height = "auto"; ta.style.height = ta.scrollHeight + "px"; });
    ta.addEventListener("keydown", e => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
}

function fillInput(text) {
    const ta = document.getElementById("userInput");
    ta.value = text;
    ta.style.height = "auto";
    ta.style.height = ta.scrollHeight + "px";
    ta.focus();
}

// ===== VIEW SWITCHING =====

const VIEW_TITLES = { chat: "Chat", history: "History", documents: "Documents", metrics: "Metrics" };

function switchView(view) {
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

    const el = document.getElementById(`view-${view}`);
    if (el) el.classList.add("active");

    const nav = document.querySelector(`[data-view="${view}"]`);
    if (nav) nav.classList.add("active");

    document.getElementById("viewTitle").textContent = VIEW_TITLES[view] || view;

    // Show/hide topbar buttons relevant to view
    const exportBtn = document.getElementById("exportBtn");
    const clearBtn  = document.getElementById("clearBtn");
    exportBtn.style.display = view === "chat" ? "" : "none";
    clearBtn.style.display  = view === "chat" ? "" : "none";

    if (view === "history")   loadHistory();
    if (view === "documents") loadDocuments();
    if (view === "metrics")   loadMetrics();
}

// ===== MESSAGES =====

function msgBox() { return document.getElementById("messages"); }

function appendMsg(type, content) {
    const box = msgBox();
    const welcome = box.querySelector(".welcome-msg");
    if (welcome) welcome.remove();

    const row  = document.createElement("div");
    row.className = `msg-row ${type}`;

    const avatarText = type === "user" ? getUsername().charAt(0).toUpperCase()
                     : type === "bot"  ? "🤖"
                     : "ℹ";
    row.innerHTML = `<div class="msg-avatar">${avatarText}</div><div class="msg-bubble">${content}</div>`;
    box.appendChild(row);
    box.scrollTop = box.scrollHeight;
    return row.querySelector(".msg-bubble");
}

function appendSystem(text) {
    appendMsg("system", escapeHtml(text));
}

function appendTyping() {
    const box = msgBox();
    const row = document.createElement("div");
    row.className = "msg-row bot";
    row.id = "typingRow";
    row.innerHTML = `<div class="msg-avatar">🤖</div><div class="msg-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
    box.appendChild(row);
    box.scrollTop = box.scrollHeight;
}

function removeTyping() {
    const el = document.getElementById("typingRow");
    if (el) el.remove();
}

// ===== RENDER BOT MESSAGE =====

function renderBotMessage(answer, sources, confidence, timing, queryId) {
    const bubble = appendMsg("bot", "");

    // Answer text
    const answerEl = document.createElement("div");
    answerEl.style.whiteSpace = "pre-wrap";
    answerEl.style.lineHeight = "1.65";
    answerEl.textContent = answer;
    bubble.appendChild(answerEl);

    // Confidence bar
    if (confidence > 0) {
        const pct = Math.round(confidence * 100);
        const cls = confidence >= 0.75 ? "conf-high" : confidence >= 0.5 ? "conf-medium" : "conf-low";
        const confEl = document.createElement("div");
        confEl.className = "confidence-bar";
        confEl.innerHTML = `
            <div class="confidence-label">
                <span>Confidence</span>
                <span style="color:${confidence >= 0.75 ? '#10b981' : confidence >= 0.5 ? '#f59e0b' : '#ef4444'}">${pct}%</span>
            </div>
            <div class="confidence-track">
                <div class="confidence-fill ${cls}" style="width:${pct}%"></div>
            </div>`;
        bubble.appendChild(confEl);
    }

    // Timing chips
    if (timing && timing.total_time_ms) {
        const timingEl = document.createElement("div");
        timingEl.className = "timing-row";
        timingEl.innerHTML = `
            <span class="timing-chip">⏱ Total: ${(timing.total_time_ms / 1000).toFixed(2)}s</span>
            ${timing.retrieval_time_ms ? `<span class="timing-chip">🔍 Retrieval: ${timing.retrieval_time_ms}ms</span>` : ""}
            ${timing.llm_time_ms ? `<span class="timing-chip">🤖 LLM: ${timing.llm_time_ms}ms</span>` : ""}`;
        bubble.appendChild(timingEl);
    }

    // Sources
    if (sources && sources.length > 0) {
        const toggle = document.createElement("button");
        toggle.className = "sources-toggle";
        toggle.innerHTML = `📎 ${sources.length} source${sources.length > 1 ? "s" : ""} — click to expand`;
        toggle.setAttribute("aria-expanded", "false");

        const listEl = document.createElement("div");
        listEl.className = "sources-list";
        listEl.style.display = "none";

        sources.forEach(src => {
            const viewUrl = src.doc_url ? `${API_BASE}/documents/${encodeDocUrl(src.doc_url)}` : null;
            const dlUrl   = viewUrl ? viewUrl + "?download=1" : null;

            const card = document.createElement("div");
            card.className = "source-card";
            card.innerHTML = `
                <div class="source-header">
                    <span class="source-name">📄 ${escapeHtml(src.filename)}</span>
                    <span class="source-page">Page ${src.page + 1}</span>
                    <div class="source-actions">
                        ${viewUrl ? `<a class="btn-source btn-view" href="${viewUrl}" target="_blank">View</a>` : ""}
                        ${viewUrl ? `<a class="btn-source btn-download" href="${viewUrl}" download="${escapeHtml(src.filename)}">Download</a>` : ""}
                    </div>
                </div>
                <div class="source-snippet">${escapeHtml(src.snippet)}</div>`;
            listEl.appendChild(card);
        });

        toggle.onclick = () => {
            const open = listEl.style.display !== "none";
            listEl.style.display = open ? "none" : "flex";
            toggle.setAttribute("aria-expanded", String(!open));
            toggle.innerHTML = open
                ? `📎 ${sources.length} source${sources.length > 1 ? "s" : ""} — click to expand`
                : `📎 ${sources.length} source${sources.length > 1 ? "s" : ""} — click to collapse`;
        };

        bubble.appendChild(toggle);
        bubble.appendChild(listEl);
    }

    // Feedback
    if (queryId) {
        const fbRow = document.createElement("div");
        fbRow.className = "feedback-row";
        fbRow.innerHTML = `<span>Was this helpful?</span>`;

        const btnUp   = document.createElement("button");
        const btnDown = document.createElement("button");
        btnUp.className   = "btn-feedback";
        btnDown.className = "btn-feedback";
        btnUp.textContent   = "👍";
        btnDown.textContent = "👎";

        btnUp.onclick = () => { sendFeedback(queryId, 1, btnUp, btnDown); };
        btnDown.onclick = () => { sendFeedback(queryId, -1, btnUp, btnDown); };

        fbRow.appendChild(btnUp);
        fbRow.appendChild(btnDown);
        bubble.appendChild(fbRow);
    }

    // Suggestions (async fetch)
    const suggestionsContainer = document.createElement("div");
    bubble.appendChild(suggestionsContainer);
    fetchSuggestions(answer.length > 10 ? suggestionsContainer : null, answerEl.textContent.slice(0, 120));

    msgBox().scrollTop = msgBox().scrollHeight;
}

// ===== SEND MESSAGE =====

let isSending = false;

async function sendMessage() {
    if (isSending) return;
    const ta       = document.getElementById("userInput");
    const question = ta.value.trim();
    if (!question) return;

    isSending = true;
    ta.value = "";
    ta.style.height = "auto";
    document.getElementById("userInput").disabled = true;
    document.querySelector(".btn-send").disabled  = true;

    appendMsg("user", escapeHtml(question));
    appendTyping();

    try {
        const res = await fetch(`${API_BASE}/ask`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ question }),
        });

        removeTyping();

        if (res.status === 401) { logout(); return; }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        renderBotMessage(
            data.answer,
            data.sources || [],
            data.confidence || 0,
            { retrieval_time_ms: data.retrieval_time_ms, llm_time_ms: data.llm_time_ms, total_time_ms: data.total_time_ms },
            data.query_id,
        );
    } catch (err) {
        removeTyping();
        appendSystem(`Error: ${err.message}`);
    } finally {
        isSending = false;
        document.getElementById("userInput").disabled = false;
        document.querySelector(".btn-send").disabled  = false;
        document.getElementById("userInput").focus();
    }
}

// ===== SUGGESTIONS =====

const lastQuestion = { text: "" };

async function fetchSuggestions(container, questionHint) {
    if (!container) return;
    // Use the last user question for context
    const q = lastQuestion.text || questionHint;
    if (!q || q.length < 5) return;

    try {
        const res = await fetch(`${API_BASE}/suggestions`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ question: q }),
        });
        if (!res.ok) return;
        const data = await res.json();
        if (!data.suggestions || data.suggestions.length === 0) return;

        container.className = "suggestions-row";
        container.innerHTML = `<span class="suggestion-label">💡 You might also ask</span>`;
        data.suggestions.forEach(s => {
            const btn = document.createElement("button");
            btn.className = "btn-suggestion";
            btn.textContent = s;
            btn.onclick = () => { fillInput(s); sendMessage(); };
            container.appendChild(btn);
        });
    } catch {}
}

// ===== FEEDBACK =====

async function sendFeedback(queryId, value, btnUp, btnDown) {
    try {
        await fetch(`${API_BASE}/feedback`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ query_id: queryId, feedback: value }),
        });
        btnUp.classList.toggle("active-up",   value === 1);
        btnDown.classList.toggle("active-down", value === -1);
        btnUp.disabled   = true;
        btnDown.disabled = true;
    } catch {}
}

// ===== VOICE INPUT =====

let recognition = null;
let listeningActive = false;

function toggleVoice() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { alert("Voice input not supported in this browser. Try Chrome."); return; }

    const voiceBtn = document.getElementById("voiceBtn");

    if (listeningActive) {
        recognition && recognition.stop();
        listeningActive = false;
        voiceBtn.classList.remove("listening");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => { listeningActive = true; voiceBtn.classList.add("listening"); };
    recognition.onend   = () => { listeningActive = false; voiceBtn.classList.remove("listening"); };
    recognition.onerror = () => { listeningActive = false; voiceBtn.classList.remove("listening"); };

    recognition.onresult = e => {
        const transcript = e.results[0][0].transcript;
        fillInput(transcript);
    };

    recognition.start();
}

// ===== CHAT HISTORY VIEW =====

async function loadHistory() {
    const el = document.getElementById("historyContent");
    el.innerHTML = '<div class="loading-state">Loading history…</div>';
    try {
        const res = await fetch(`${API_BASE}/chat/history?limit=50`, { headers: getHeaders() });
        if (!res.ok) throw new Error();
        const data = await res.json();
        renderHistory(el, data.history);
    } catch {
        el.innerHTML = '<div class="loading-state">Could not load history.</div>';
    }
}

function renderHistory(el, items) {
    if (!items || items.length === 0) {
        el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🕐</div><p>No chat history yet. Start asking questions!</p></div>`;
        return;
    }
    el.innerHTML = `<div class="section-header"><span class="section-title">Your Chat History</span></div>`;
    items.forEach(item => {
        const card = document.createElement("div");
        card.className = "history-item";
        const conf = item.confidence ? Math.round(item.confidence * 100) + "%" : "-";
        const time = item.timestamp ? new Date(item.timestamp).toLocaleString() : "";
        card.innerHTML = `
            <div class="history-q">Q: ${escapeHtml(item.question)}</div>
            <div class="history-a">${escapeHtml(item.answer)}</div>
            <div class="history-meta">
                <span>🕐 ${time}</span>
                <span>Confidence: ${conf}</span>
                <span>⏱ ${item.response_time_ms || 0}ms</span>
            </div>`;
        card.onclick = () => {
            fillInput(item.question);
            switchView("chat");
        };
        el.appendChild(card);
    });
}

// ===== DOCUMENTS VIEW =====

async function loadDocuments() {
    const el = document.getElementById("docsContent");
    el.innerHTML = '<div class="loading-state">Loading documents…</div>';
    try {
        const res = await fetch(`${API_BASE}/documents/list`, { headers: getHeaders() });
        if (!res.ok) throw new Error();
        const data = await res.json();
        renderDocuments(el, data.documents);
    } catch {
        el.innerHTML = '<div class="loading-state">Could not load documents.</div>';
    }
}

function renderDocuments(el, docs) {
    if (!docs || docs.length === 0) {
        el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📁</div><p>No documents found for your role.</p></div>`;
        return;
    }
    el.innerHTML = `<div class="section-header"><span class="section-title">Your Documents (${docs.length})</span></div>`;
    const grid = document.createElement("div");
    grid.className = "docs-grid";

    docs.forEach(doc => {
        const fileUrl  = `${API_BASE}/documents/${encodeDocUrl(doc.doc_url)}`;
        const chipCls  = `chip-${doc.role}`;
        const card = document.createElement("div");
        card.className = "doc-card";
        card.innerHTML = `
            <div class="doc-icon">📄</div>
            <div class="doc-name">${escapeHtml(doc.filename)}</div>
            <span class="doc-role-chip ${chipCls}">${doc.role}</span>
            <div class="doc-actions">
                <a class="doc-btn doc-btn-view" href="${fileUrl}" target="_blank">👁 View</a>
                <a class="doc-btn doc-btn-dl"   href="${fileUrl}" download="${escapeHtml(doc.filename)}">⬇ Download</a>
            </div>`;
        grid.appendChild(card);
    });
    el.appendChild(grid);
}

// ===== METRICS VIEW =====

async function loadMetrics() {
    const el = document.getElementById("metricsContent");
    el.innerHTML = '<div class="loading-state">Loading metrics…</div>';
    try {
        const [evalRes, statsRes] = await Promise.all([
            fetch(`${API_BASE}/metrics/evaluation`, { headers: getHeaders() }),
            fetch(`${API_BASE}/analytics/stats?days=30`,   { headers: getHeaders() }),
        ]);
        if (!evalRes.ok || !statsRes.ok) throw new Error();
        const evalData  = await evalRes.json();
        const statsData = await statsRes.json();
        renderMetrics(el, evalData, statsData);
    } catch {
        el.innerHTML = '<div class="loading-state">Could not load metrics.</div>';
    }
}

function renderMetrics(el, ev, stats) {
    el.innerHTML = "";

    const answerPct   = Math.round((ev.answer_rate || 0) * 100);
    const confPct     = Math.round((ev.avg_confidence || 0) * 100);
    const feedbackPct = Math.round((ev.feedback_score || 0) * 100);
    const avgTimeS    = ((ev.avg_response_time_ms || 0) / 1000).toFixed(2);

    // Stat cards
    const grid = document.createElement("div");
    grid.className = "metrics-grid";
    grid.innerHTML = `
        <div class="metric-card">
            <div class="metric-value">${ev.total_queries || 0}</div>
            <div class="metric-label">Total Queries</div>
            <div class="metric-sub">all time</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:${confPct >= 75 ? '#10b981' : confPct >= 50 ? '#f59e0b' : '#ef4444'}">${confPct}%</div>
            <div class="metric-label">Avg Confidence</div>
            <div class="metric-sub">retrieval quality</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:${answerPct >= 70 ? '#10b981' : '#f59e0b'}">${answerPct}%</div>
            <div class="metric-label">Answer Rate</div>
            <div class="metric-sub">questions answered</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:${feedbackPct >= 70 ? '#10b981' : feedbackPct > 0 ? '#f59e0b' : '#94a3b8'}">${feedbackPct > 0 ? feedbackPct + "%" : "–"}</div>
            <div class="metric-label">Feedback Score</div>
            <div class="metric-sub">${ev.thumbs_up || 0}👍 ${ev.thumbs_down || 0}👎</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="font-size:20px">${avgTimeS}s</div>
            <div class="metric-label">Avg Response</div>
            <div class="metric-sub">end-to-end latency</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="font-size:20px">${stats.total_users || 0}</div>
            <div class="metric-label">Active Users</div>
            <div class="metric-sub">last 30 days</div>
        </div>`;
    el.appendChild(grid);

    // Confidence distribution
    const cd = ev.confidence_distribution || { high: 0, medium: 0, low: 0 };
    const cdTotal = (cd.high + cd.medium + cd.low) || 1;
    const sec1 = document.createElement("div");
    sec1.className = "metrics-section";
    sec1.innerHTML = `
        <div class="metrics-section-title">Confidence Distribution</div>
        <div class="conf-dist">
            <div class="conf-dist-row">
                <span class="conf-dist-label">High</span>
                <div class="conf-dist-bar"><div class="conf-dist-fill conf-high" style="width:${(cd.high/cdTotal*100).toFixed(1)}%"></div></div>
                <span class="conf-dist-count">${cd.high}</span>
            </div>
            <div class="conf-dist-row">
                <span class="conf-dist-label">Medium</span>
                <div class="conf-dist-bar"><div class="conf-dist-fill conf-medium" style="width:${(cd.medium/cdTotal*100).toFixed(1)}%"></div></div>
                <span class="conf-dist-count">${cd.medium}</span>
            </div>
            <div class="conf-dist-row">
                <span class="conf-dist-label">Low</span>
                <div class="conf-dist-bar"><div class="conf-dist-fill conf-low" style="width:${(cd.low/cdTotal*100).toFixed(1)}%"></div></div>
                <span class="conf-dist-count">${cd.low}</span>
            </div>
        </div>`;
    el.appendChild(sec1);

    // Queries by role
    const roles = ev.queries_by_role || {};
    if (Object.keys(roles).length > 0) {
        const sec2 = document.createElement("div");
        sec2.className = "metrics-section";
        let rows = Object.entries(roles).map(([r, n]) =>
            `<tr><td><span class="doc-role-chip chip-${r}">${r}</span></td><td>${n}</td></tr>`
        ).join("");
        sec2.innerHTML = `
            <div class="metrics-section-title">Queries by Role</div>
            <table class="role-table">
                <thead><tr><th>Role</th><th>Queries</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>`;
        el.appendChild(sec2);
    }

    // Top questions
    if (stats.top_questions && stats.top_questions.length > 0) {
        const sec3 = document.createElement("div");
        sec3.className = "metrics-section";
        let rows = stats.top_questions.slice(0, 5).map(q =>
            `<tr><td>${escapeHtml(q.question)}</td><td style="text-align:right;color:#6366f1;font-weight:700">${q.count}</td></tr>`
        ).join("");
        sec3.innerHTML = `
            <div class="metrics-section-title">Top Questions (30 days)</div>
            <table class="role-table">
                <thead><tr><th>Question</th><th>Count</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>`;
        el.appendChild(sec3);
    }
}

// ===== CHAT UTILITIES =====

function clearChat() {
    if (!confirm("Clear all messages?")) return;
    const box = msgBox();
    box.innerHTML = `
        <div class="welcome-msg">
            <div class="welcome-icon">🧠</div>
            <h3>How can I help you today?</h3>
            <p>Ask me anything about your company policies. I'll only answer from your authorised documents.</p>
        </div>`;
}

function exportChat() {
    const rows = msgBox().querySelectorAll(".msg-row");
    if (rows.length === 0) { alert("No messages to export."); return; }

    let text = `Enterprise AI Chat Export\n${new Date().toLocaleString()}\nUser: ${getUsername()} | Role: ${getRole()}\n${"=".repeat(60)}\n\n`;
    rows.forEach(row => {
        const isUser = row.classList.contains("user");
        const bubble = row.querySelector(".msg-bubble");
        if (!bubble) return;
        const content = bubble.firstChild && bubble.firstChild.nodeType === 3
            ? bubble.firstChild.textContent.trim()
            : bubble.querySelector("div")?.textContent?.trim() || "";
        if (content) text += `${isUser ? "You" : "Assistant"}:\n${content}\n\n`;
    });

    const blob = new Blob([text], { type: "text/plain" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `chat-export-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

// ===== HELPERS =====

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function encodeDocUrl(docUrl) {
    if (!docUrl) return "";
    const parts = docUrl.replace("\\", "/").split("/");
    return parts.map((p, i) => i === parts.length - 1 ? encodeURIComponent(p) : p).join("/");
}

// ===== STARTUP =====

document.addEventListener("DOMContentLoaded", () => {
    if (!checkAuth()) return;
    initApp();
    switchView("chat");
    // Set last question tracker
    document.getElementById("userInput").addEventListener("keydown", e => {
        if (e.key === "Enter" && !e.shiftKey) {
            lastQuestion.text = document.getElementById("userInput").value.trim();
        }
    });
    document.querySelector(".btn-send").addEventListener("click", () => {
        lastQuestion.text = document.getElementById("userInput").value.trim();
    });
});
