// ==================== CONFIGURATION ====================
const API_BASE = "http://127.0.0.1:8000";
const STORAGE_TOKEN_KEY = "token";
const STORAGE_USER_KEY = "username";
const STORAGE_ROLE_KEY = "role";

// ==================== AUTHENTICATION ====================

function checkAuthentication() {
    const token = localStorage.getItem(STORAGE_TOKEN_KEY);
    if (!token) {
        window.location.href = "login.html";
        return;
    }
    initializeApp();
}

function logout() {
    const token = localStorage.getItem(STORAGE_TOKEN_KEY);
    
    fetch(`${API_BASE}/logout`, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
        }
    }).then(() => {
        localStorage.removeItem(STORAGE_TOKEN_KEY);
        localStorage.removeItem(STORAGE_USER_KEY);
        localStorage.removeItem(STORAGE_ROLE_KEY);
        window.location.href = "login.html";
    });
}

function getAuthHeaders() {
    const token = localStorage.getItem(STORAGE_TOKEN_KEY);
    if (!token) {
        window.location.href = "login.html";
        return null;
    }
    return {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
    };
}

// ==================== INITIALIZATION ====================

function initializeApp() {
    const username = localStorage.getItem(STORAGE_USER_KEY);
    const role = localStorage.getItem(STORAGE_ROLE_KEY);
    
    document.getElementById("userDisplay").textContent = `👤 ${username}`;
    
    // Set role badge with icon
    const roleBadge = document.getElementById("roleBadge");
    const roleIcons = {
        "employee": "👤 Employee",
        "hr": "👥 HR",
        "manager": "🎯 Manager",
        "admin": "⚙️ Admin"
    };
    roleBadge.textContent = roleIcons[role] || role;
    roleBadge.className = `role-badge role-${role}`;
    
    // Setup keyboard shortcut
    document.getElementById("userInput").addEventListener("keypress", function(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    displaySystemMessage("✅ Connected successfully!");
}

// ==================== MESSAGE DISPLAY ====================

function displaySystemMessage(message) {
    const chatBox = document.getElementById("chatBox");
    const messageEl = document.createElement("div");
    messageEl.className = "system-message";
    messageEl.innerHTML = `<p>${message}</p>`;
    chatBox.appendChild(messageEl);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function displayUserMessage(text) {
    const chatBox = document.getElementById("chatBox");
    const messageEl = document.createElement("div");
    messageEl.className = "message user-message";
    messageEl.innerHTML = `<div class="message-content"><strong>You:</strong> ${escapeHtml(text)}</div>`;
    chatBox.appendChild(messageEl);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function displayBotMessage(text, sources = [], confidence = 0, timing = {}) {
    const chatBox = document.getElementById("chatBox");
    const messageEl = document.createElement("div");
    messageEl.className = "message bot-message";
    
    let html = `<div class="message-content">
        <strong>🤖 Assistant:</strong>
        <p>${text}</p>`;
    
    // Add sources
    if (sources && sources.length > 0) {
        html += `<details class="sources-section">
            <summary>📎 Sources (${sources.length})</summary>
            <ul class="sources-list">`;
        
        sources.forEach((source, idx) => {
            html += `<li class="source-item">
                <strong>${source.filename}</strong> (Page ${source.page})
                <p class="source-snippet">${source.snippet}</p>
            </li>`;
        });
        
        html += `</ul></details>`;
    }
    
    // Add metrics
    if (Object.keys(timing).length > 0 || confidence > 0) {
        html += `<div class="message-metrics">`;
        if (confidence > 0) html += `<span>Confidence: ${(confidence * 100).toFixed(0)}%</span>`;
        if (timing.retrieval_time_ms) html += `<span>Retrieval: ${timing.retrieval_time_ms}ms</span>`;
        if (timing.llm_time_ms) html += `<span>LLM: ${timing.llm_time_ms}ms</span>`;
        if (timing.total_time_ms) html += `<span>Total: ${timing.total_time_ms}ms</span>`;
        html += `</div>`;
    }
    
    html += `</div>`;
    messageEl.innerHTML = html;
    chatBox.appendChild(messageEl);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// ==================== MESSAGE SENDING ====================

async function sendMessage() {
    const input = document.getElementById("userInput");
    const question = input.value.trim();
    
    if (!question) return;
    
    // Display user message
    displayUserMessage(question);
    input.value = "";
    
    // Show typing indicator
    document.getElementById("typingIndicator").style.display = "flex";
    
    try {
        const headers = getAuthHeaders();
        if (!headers) return;
        
        const response = await fetch(`${API_BASE}/ask`, {
            method: "POST",
            headers: headers,
            body: JSON.stringify({ question: question })
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                displaySystemMessage("❌ Session expired. Please login again.");
                logout();
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        document.getElementById("typingIndicator").style.display = "none";
        
        displayBotMessage(
            data.answer,
            data.sources,
            data.confidence,
            {
                retrieval_time_ms: data.retrieval_time_ms,
                llm_time_ms: data.llm_time_ms,
                total_time_ms: data.total_time_ms
            }
        );
        
        updateStats(data.total_time_ms);
        
    } catch (error) {
        document.getElementById("typingIndicator").style.display = "none";
        displaySystemMessage(`❌ Error: ${error.message}`);
        console.error("Error:", error);
    }
}

// ==================== STREAMING RESPONSES ====================

async function sendMessageStream() {
    const input = document.getElementById("userInput");
    const question = input.value.trim();
    
    if (!question) return;
    
    // Display user message
    displayUserMessage(question);
    input.value = "";
    
    // Show typing indicator
    document.getElementById("typingIndicator").style.display = "flex";
    
    try {
        const headers = getAuthHeaders();
        if (!headers) return;
        
        // Create message container
        const chatBox = document.getElementById("chatBox");
        const messageEl = document.createElement("div");
        messageEl.className = "message bot-message streaming";
        const contentDiv = document.createElement("div");
        contentDiv.className = "message-content";
        contentDiv.innerHTML = "<strong>🤖 Assistant (Streaming):</strong><p id='streamingContent'></p>";
        messageEl.appendChild(contentDiv);
        chatBox.appendChild(messageEl);
        
        const contentContainer = document.getElementById("streamingContent");
        let fullResponse = "";
        let sources = [];
        
        const response = await fetch(`${API_BASE}/ask-stream`, {
            method: "POST",
            headers: headers,
            body: JSON.stringify({ question: question })
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                displaySystemMessage("❌ Session expired. Please login again.");
                logout();
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        document.getElementById("typingIndicator").style.display = "none";
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n').filter(line => line.startsWith('data: '));
            
            for (const line of lines) {
                try {
                    const jsonStr = line.replace('data: ', '');
                    const data = JSON.parse(jsonStr);
                    
                    if (data.type === "sources") {
                        sources = data.sources;
                    } else if (data.type === "content") {
                        fullResponse += data.content;
                        contentContainer.textContent = fullResponse;
                        chatBox.scrollTop = chatBox.scrollHeight;
                    } else if (data.type === "error") {
                        displaySystemMessage(`❌ Stream error: ${data.error}`);
                    }
                } catch (e) {
                    // Skip invalid JSON
                }
            }
        }
        
        // Add sources after streaming complete
        if (sources.length > 0) {
            let sourcesHtml = `<details class="sources-section">
                <summary>📎 Sources (${sources.length})</summary>
                <ul class="sources-list">`;
            
            sources.forEach((source, idx) => {
                sourcesHtml += `<li class="source-item">
                    <strong>${source.filename}</strong> (Page ${source.page})
                    <p class="source-snippet">${source.snippet}</p>
                </li>`;
            });
            
            sourcesHtml += `</ul></details>`;
            contentDiv.innerHTML += sourcesHtml;
        }
        
        messageEl.classList.remove("streaming");
        
    } catch (error) {
        document.getElementById("typingIndicator").style.display = "none";
        displaySystemMessage(`❌ Stream error: ${error.message}`);
        console.error("Error:", error);
    }
}

// ==================== UTILITY FUNCTIONS ====================

function clearChat() {
    if (confirm("Clear all messages?")) {
        document.getElementById("chatBox").innerHTML = "";
        displaySystemMessage("✨ Chat cleared");
    }
}

function updateStats(timeMs) {
    const statsEl = document.getElementById("statsText");
    const seconds = (timeMs / 1000).toFixed(2);
    statsEl.textContent = `✅ Last response: ${seconds}s | Role: ${localStorage.getItem(STORAGE_ROLE_KEY)}`;
}

// ==================== STARTUP ====================

document.addEventListener("DOMContentLoaded", checkAuthentication);


