(() => {
  const API_BASE = '';

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const state = {
    sessionId: localStorage.getItem('car_helper_session') || '',
    messages: [],
    reasoningBuffer: '',
    contentBuffer: '',
    currentTool: null,
    toolsUsed: [],
    isStreaming: false,
    abortController: null,
  };

  // ─── DOM refs ──────────────────────────────────────────
  const els = {
    connIndicator: $('#conn-indicator'),
    connText: $('#conn-text'),
    sessionDisplay: $('#session-display'),
    latencyDisplay: $('#latency-display'),
    sessionList: $('#session-list'),
    messages: $('#messages'),
    input: $('#input-field'),
    sendBtn: $('#send-btn'),
    newSessionBtn: $('#new-session-btn'),
  };

  // ─── Utils ─────────────────────────────────────────────
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function renderMarkdown(text) {
    // 1. Escape HTML
    let html = escapeHtml(text);

    // 2. Split into lines for block-level parsing
    const lines = html.split('\n');
    const blocks = [];
    let tableLines = [];

    function flushTable() {
      if (tableLines.length < 2) {
        // Not a real table, push as plain lines
        tableLines.forEach(l => blocks.push({ type: 'text', content: l }));
        tableLines = [];
        return;
      }
      // Filter out separator line (|---|---|)
      const dataLines = tableLines.filter(l => !l.match(/^\|[\s\-:|]+\|$/));
      if (dataLines.length === 0) {
        tableLines = [];
        return;
      }
      const headerCells = dataLines[0].split('|').filter(c => c.trim() !== '');
      const bodyRows = dataLines.slice(1).map(row =>
        row.split('|').filter(c => c.trim() !== '')
      );
      blocks.push({ type: 'table', headers: headerCells, rows: bodyRows });
      tableLines = [];
    }

    for (const line of lines) {
      if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
        tableLines.push(line.trim());
      } else {
        flushTable();
        blocks.push({ type: 'text', content: line });
      }
    }
    flushTable();

    // 3. Render blocks
    let result = '';
    let listBuffer = [];

    function flushList() {
      if (listBuffer.length === 0) return;
      result += '<ul>' + listBuffer.map(i => `<li>${inlineFormat(i)}</li>`).join('') + '</ul>';
      listBuffer = [];
    }

    for (const block of blocks) {
      if (block.type === 'table') {
        flushList();
        let tbl = '<div class="md-table-wrap"><table class="md-table"><thead><tr>';
        block.headers.forEach(h => { tbl += `<th>${inlineFormat(h.trim())}</th>`; });
        tbl += '</tr></thead><tbody>';
        block.rows.forEach(row => {
          tbl += '<tr>';
          row.forEach(c => { tbl += `<td>${inlineFormat(c.trim())}</td>`; });
          // Pad if row has fewer cells than header
          for (let i = row.length; i < block.headers.length; i++) tbl += '<td></td>';
          tbl += '</tr>';
        });
        tbl += '</tbody></table></div>';
        result += tbl;
        continue;
      }

      const line = block.content;
      const trimmed = line.trim();

      // Headings
      if (trimmed.startsWith('### ')) {
        flushList();
        result += `<h4>${inlineFormat(trimmed.slice(4))}</h4>`;
        continue;
      }
      if (trimmed.startsWith('## ')) {
        flushList();
        result += `<h3>${inlineFormat(trimmed.slice(3))}</h3>`;
        continue;
      }

      // Horizontal rule
      if (trimmed === '---' || trimmed === '***') {
        flushList();
        result += '<hr class="md-hr">';
        continue;
      }

      // List item
      if (trimmed.startsWith('- ')) {
        listBuffer.push(trimmed.slice(2));
        continue;
      }

      // Empty line = paragraph break
      if (trimmed === '') {
        flushList();
        result += '<div class="md-spacer"></div>';
        continue;
      }

      // Regular text
      flushList();
      result += `<p>${inlineFormat(trimmed)}</p>`;
    }
    flushList();

    return result;
  }

  function inlineFormat(text) {
    return text
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');
  }

  function formatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts.replace(/-/g, '/'));
    return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function generateId() {
    return Math.random().toString(36).substring(2, 10).toUpperCase();
  }

  // ─── Session ───────────────────────────────────────────
  function setSession(id) {
    state.sessionId = id;
    localStorage.setItem('car_helper_session', id);
    els.sessionDisplay.textContent = `SESSION: ${id.slice(0, 6).toUpperCase()}`;
  }

  async function loadSessionMessages(sessionId) {
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages`);
      const data = await res.json();
      if (data.messages && data.messages.length > 0) {
        state.messages = data.messages.map((m, i) => ({
          role: m.role,
          content: m.content,
          time: Date.now() - (data.messages.length - i) * 60000,
        }));
      } else {
        state.messages = [];
      }
    } catch (e) {
      console.error('load session messages failed', e);
      state.messages = [];
    }
  }

  function newSession() {
    setSession(generateId());
    state.messages = [];
    state.reasoningBuffer = '';
    state.contentBuffer = '';
    state.currentTool = null;
    state.isStreaming = false;
    renderMessages();
    loadSessions();
    els.input.focus();
  }

  async function loadSessions() {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`);
      const data = await res.json();
      const sessions = data.sessions || [];
      renderSessionList(sessions);
      return sessions;
    } catch (e) {
      console.error('load sessions failed', e);
      return [];
    }
  }

  function renderSessionList(sessions = []) {
    els.sessionList.innerHTML = '';
    sessions.forEach(s => {
      const item = document.createElement('div');
      item.className = `session-item${s.id === state.sessionId ? ' active' : ''}`;
      item.innerHTML = `
        <div class="session-item-header">
          <div class="session-id">${s.id.slice(0, 8).toUpperCase()}</div>
          <button class="session-delete-btn" title="删除会话">&times;</button>
        </div>
        <div class="session-query">${escapeHtml(s.last_query || '(无标题)')}</div>
        <div class="session-time">${formatTime(s.update_time)}</div>
      `;
      item.addEventListener('click', async (e) => {
        if (e.target.closest('.session-delete-btn')) return;
        if (s.id === state.sessionId && state.messages.length > 0) return;
        setSession(s.id);
        renderSessionList(sessions);
        await loadSessionMessages(s.id);
        renderMessages();
      });
      item.querySelector('.session-delete-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        deleteSession(s.id, sessions);
      });
      els.sessionList.appendChild(item);
    });
  }

  async function deleteSession(sessionId, sessions) {
    if (!confirm('确定删除这个会话？')) return;
    try {
      await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: 'DELETE' });
    } catch (e) {
      console.error('delete session failed', e);
    }
    if (sessionId === state.sessionId) {
      newSession();
    }
    const updated = await loadSessions();
    renderSessionList(updated);
  }

  // ─── Message Rendering ─────────────────────────────────
  function renderMessages() {
    els.messages.innerHTML = '';

    if (state.messages.length === 0) {
      els.messages.innerHTML = `
        <div class="welcome-message">
          <h2 class="welcome-title">智能选车助手</h2>
          <p class="welcome-desc">基于 40,000+ 车型知识图谱，通过自然语言帮你找到最合适的座驾。</p>
          <div class="suggestions">
            <button class="suggestion-chip" data-text="20万以内纯电SUV推荐">20万以内纯电SUV</button>
            <button class="suggestion-chip" data-text="比亚迪和特斯拉怎么选">比亚迪 vs 特斯拉</button>
            <button class="suggestion-chip" data-text="10万以内保养成本低的车">低保养成本车型</button>
            <button class="suggestion-chip" data-text="纯电动车续航最长的有哪些">续航最长纯电车</button>
          </div>
        </div>`;
      bindSuggestions();
      return;
    }

    state.messages.forEach((msg, idx) => {
      const div = document.createElement('div');
      div.className = `message message-${msg.role}`;

      if (msg.role === 'user') {
        div.innerHTML = `
          <div class="message-header">USER // ${new Date(msg.time).toLocaleTimeString()}</div>
          <div class="message-body">${escapeHtml(msg.content)}</div>
        `;
      } else {
        let html = `<div class="message-header">AGENT // ${new Date(msg.time).toLocaleTimeString()}</div>`;

        if (msg.reasoning) {
          html += `
            <div class="reasoning-block" id="reasoning-${idx}">
              <div class="reasoning-toggle" onclick="this.parentElement.classList.toggle('expanded')">
                REASONING PROCESS
              </div>
              <div class="reasoning-content">
                <div class="reasoning-text">${escapeHtml(msg.reasoning)}</div>
              </div>
            </div>`;
        }

        if (msg.tools && msg.tools.length) {
          msg.tools.forEach(t => {
            html += `
              <div class="tool-indicator">
                <div class="tool-dots"><div class="tool-dot"></div><div class="tool-dot"></div><div class="tool-dot"></div></div>
                <span class="tool-name">${escapeHtml(t.name)}</span>
              </div>`;
          });
        }

        html += `<div class="message-body">${renderMarkdown(msg.content)}</div>`;
        div.innerHTML = html;
      }

      els.messages.appendChild(div);
    });

    scrollToBottom();
  }

  function bindSuggestions() {
    $$('.suggestion-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        els.input.value = btn.dataset.text;
        els.input.dispatchEvent(new Event('input'));
        sendMessage();
      });
    });
  }

  function scrollToBottom() {
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  // ─── Streaming UI ──────────────────────────────────────
  function createAgentMessage() {
    const id = `msg-${Date.now()}`;
    const div = document.createElement('div');
    div.className = 'message message-agent';
    div.id = id;
    div.innerHTML = `
      <div class="message-header">AGENT // ${new Date().toLocaleTimeString()}</div>
      <div class="reasoning-block expanded live-reasoning" id="${id}-reasoning" style="display:none">
        <div class="reasoning-toggle" onclick="this.parentElement.classList.toggle('expanded')">
          REASONING PROCESS
        </div>
        <div class="reasoning-content">
          <div class="reasoning-text" id="${id}-reasoning-text"></div>
        </div>
      </div>
      <div class="message-body" id="${id}-body"><span class="typing-cursor"></span></div>
    `;

    // Remove welcome if present
    const welcome = $('.welcome-message');
    if (welcome) welcome.remove();

    els.messages.appendChild(div);
    scrollToBottom();
    return id;
  }

  function updateLiveReasoning(id) {
    const block = $(`#${id}-reasoning`);
    const text = $(`#${id}-reasoning-text`);
    if (!block || !text) return;
    if (state.reasoningBuffer && block.style.display === 'none') {
      block.style.display = '';
    }
    text.textContent = state.reasoningBuffer;
    scrollToBottom();
  }

  function updateAgentMessage(id, text, opts = {}) {
    const body = $(`#${id}-body`);
    if (!body) return;

    body.innerHTML = renderMarkdown(text) + (opts.typing ? '<span class="typing-cursor"></span>' : '');
    scrollToBottom();
  }

  function showToolIndicator(id, toolName) {
    const msgEl = $(`#${id}`);
    if (!msgEl) return;
    let indicator = msgEl.querySelector('.tool-indicator-live');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.className = 'tool-indicator tool-indicator-live';
      indicator.innerHTML = `
        <div class="tool-dots"><div class="tool-dot"></div><div class="tool-dot"></div><div class="tool-dot"></div></div>
        <span class="tool-name"></span>
      `;
      msgEl.insertBefore(indicator, msgEl.querySelector('.message-body'));
    }
    indicator.querySelector('.tool-name').textContent = `EXECUTING: ${toolName}...`;
    scrollToBottom();
  }

  function hideToolIndicator(id) {
    const msgEl = $(`#${id}`);
    if (!msgEl) return;
    const indicator = msgEl.querySelector('.tool-indicator-live');
    if (indicator) {
      indicator.style.opacity = '0.5';
      setTimeout(() => indicator.remove(), 600);
    }
  }

  // ─── Send ──────────────────────────────────────────────
  async function sendMessage() {
    const text = els.input.value.trim();
    if (!text || state.isStreaming) return;

    // Add user message
    state.messages.push({ role: 'user', content: text, time: Date.now() });
    renderMessages();
    els.input.value = '';
    els.input.style.height = 'auto';
    els.sendBtn.disabled = true;

    state.isStreaming = true;
    state.reasoningBuffer = '';
    state.contentBuffer = '';
    state.currentTool = null;
    state.toolsUsed = [];
    updateConnection('pending');

    const agentMsgId = createAgentMessage();

    try {
      const resp = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: state.sessionId }),
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      if (!resp.body) throw new Error('No response body');

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const chunk of lines) {
          parseSSE(chunk, agentMsgId);
        }
      }

      // Flush remaining
      if (buffer.trim()) parseSSE(buffer, agentMsgId);

      // Save final message (tools already shown as live indicators)
      state.messages.push({
        role: 'agent',
        content: state.contentBuffer,
        reasoning: state.reasoningBuffer,
        tools: [],
        time: Date.now(),
      });
      renderMessages();
      updateConnection('connected');
      loadSessions();

    } catch (err) {
      console.error('Stream error:', err);
      updateAgentMessage(agentMsgId, `连接中断: ${err.message}`, { typing: false });
      updateConnection('error');
      showError(`连接失败: ${err.message}`);
    } finally {
      state.isStreaming = false;
      els.sendBtn.disabled = !els.input.value.trim();
    }
  }

  function parseSSE(raw, agentMsgId) {
    const lines = raw.split('\n');
    let event = 'message';
    let data = '';

    for (const line of lines) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) data += line.slice(5).trim();
    }

    if (!data) return;

    try {
      const payload = JSON.parse(data);
      handleEvent(event, payload, agentMsgId);
    } catch (e) {
      console.warn('SSE parse error:', e, raw);
    }
  }

  function handleEvent(event, payload, agentMsgId) {
    switch (event) {
      case 'connected':
        if (payload.session_id) setSession(payload.session_id);
        updateConnection('connected');
        break;

      case 'tool_start':
        state.currentTool = payload.tool_name;
        state.toolsUsed.push(payload.tool_name);
        showToolIndicator(agentMsgId, payload.tool_name);
        break;

      case 'tool_end':
        state.currentTool = null;
        hideToolIndicator(agentMsgId);
        break;

      case 'reasoning':
        state.reasoningBuffer += payload.text;
        updateLiveReasoning(agentMsgId);
        break;

      case 'content':
        state.contentBuffer += payload.text;
        updateAgentMessage(agentMsgId, state.contentBuffer, { typing: true });
        break;

      case 'done':
        // Clean up any live tool indicator before DOM rebuild
        hideToolIndicator(agentMsgId);
        updateAgentMessage(agentMsgId, state.contentBuffer, { typing: false });
        if (payload.elapsed_ms) {
          els.latencyDisplay.textContent = `${payload.elapsed_ms} ms`;
        }
        break;

      case 'error':
        updateAgentMessage(agentMsgId, payload.message, { typing: false });
        updateConnection('error');
        showError(payload.message);
        break;
    }
  }

  // ─── Connection State ──────────────────────────────────
  function updateConnection(status) {
    els.connIndicator.className = 'status-indicator';
    if (status === 'connected') {
      els.connIndicator.classList.add('connected');
      els.connText.textContent = 'CONNECTED';
      els.connText.style.color = 'var(--accent-teal)';
    } else if (status === 'error') {
      els.connIndicator.classList.add('error');
      els.connText.textContent = 'ERROR';
      els.connText.style.color = 'var(--accent-red)';
    } else {
      els.connText.textContent = 'PENDING';
      els.connText.style.color = 'var(--text-faint)';
    }
  }

  function showError(msg) {
    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }

  // ─── Input Handling ────────────────────────────────────
  function autoResize() {
    els.input.style.height = 'auto';
    els.input.style.height = Math.min(els.input.scrollHeight, 200) + 'px';
  }

  els.input.addEventListener('input', () => {
    autoResize();
    els.sendBtn.disabled = !els.input.value.trim() || state.isStreaming;
  });

  els.input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  els.sendBtn.addEventListener('click', sendMessage);
  els.newSessionBtn.addEventListener('click', newSession);

  // ─── Init ──────────────────────────────────────────────
  async function init() {
    setSession(generateId());
    await loadSessions();
    renderMessages();
    els.input.focus();
  }

  init();
})();
