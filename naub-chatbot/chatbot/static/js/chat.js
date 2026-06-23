/**
 * NAUB Chatbot — Chat UI Controller
 * Handles messaging, typing indicators, suggestions, quick chips,
 * auto-resize textarea, session persistence, and chat clearing.
 */
(function () {
  'use strict';

  // ── DOM References ────────────────────────────────────────────────────
  const chatBody      = document.getElementById('chatBody');
  const userInput     = document.getElementById('userInput');
  const sendBtn       = document.getElementById('sendBtn');
  const clearBtn      = document.getElementById('clearChat');
  const sugBar        = document.getElementById('suggestionsBar');
  const topicChips    = document.querySelectorAll('.topic-chip');

  // ── State ─────────────────────────────────────────────────────────────
  let isWaiting = false;
  let suggestTimer = null;
  const SESSION_KEY = 'naub_chat_history';

  // ── Helpers ───────────────────────────────────────────────────────────
  function now() {
    return new Date().toLocaleTimeString('en-NG', { hour: '2-digit', minute: '2-digit' });
  }

  function scrollBottom(smooth = true) {
    chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: smooth ? 'smooth' : 'instant' });
  }

  function renderMarkdown(text) {
    if (window.MarkdownRenderer) return MarkdownRenderer.render(text);
    // Fallback: just escape and wrap in <p>
    return '<p>' + text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</p>';
  }

  // ── Save / Load history ───────────────────────────────────────────────
  function saveHistory(userMsg, botMsg) {
    try {
      const hist = JSON.parse(sessionStorage.getItem(SESSION_KEY) || '[]');
      hist.push({ role: 'user', text: userMsg, time: now() });
      hist.push({ role: 'bot',  text: botMsg,  time: now() });
      if (hist.length > 80) hist.splice(0, hist.length - 80);
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(hist));
    } catch (_) {}
  }

  function loadHistory() {
    try {
      return JSON.parse(sessionStorage.getItem(SESSION_KEY) || '[]');
    } catch (_) { return []; }
  }

  // ── Welcome Message ───────────────────────────────────────────────────
  function showWelcome() {
    const el = document.createElement('div');
    el.className = 'welcome-card';
    el.innerHTML = `
      <span class="welcome-emoji">🎓</span>
      <h3>Welcome to NAUB Assistant!</h3>
      <p>
        I'm your AI-powered guide to Nigerian Army University Biu. Ask me anything about
        admissions, fees, courses, hostel, academic calendar, and more.
      </p>`;
    chatBody.appendChild(el);
    scrollBottom(false);
  }

  // ── Append Messages ───────────────────────────────────────────────────
  function appendUserMsg(text) {
    const group = document.createElement('div');
    group.className = 'msg-group';

    const row = document.createElement('div');
    row.className = 'msg-row msg-row--user';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar msg-avatar--user';
    avatar.textContent = '👤';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble msg-bubble--user';
    bubble.textContent = text;

    row.appendChild(avatar);
    row.appendChild(bubble);

    const timeEl = document.createElement('div');
    timeEl.className = 'msg-time';
    timeEl.textContent = now();

    group.appendChild(row);
    group.appendChild(timeEl);
    chatBody.appendChild(group);
    scrollBottom();
  }

  function appendBotMsg(text, animate = true) {
    const group = document.createElement('div');
    group.className = 'msg-group';
    if (animate) group.style.animation = 'fadeSlideIn 0.3s ease both';

    const row = document.createElement('div');
    row.className = 'msg-row msg-row--bot';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar msg-avatar--bot';
    avatar.textContent = '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble msg-bubble--bot';
    bubble.innerHTML = renderMarkdown(text);

    row.appendChild(avatar);
    row.appendChild(bubble);

    const timeEl = document.createElement('div');
    timeEl.className = 'msg-time';
    timeEl.textContent = now();

    group.appendChild(row);
    group.appendChild(timeEl);
    chatBody.appendChild(group);
    scrollBottom();
    return group;
  }

  // ── Typing Indicator ──────────────────────────────────────────────────
  function showTyping() {
    const wrap = document.createElement('div');
    wrap.className = 'typing-indicator';
    wrap.id = 'typingIndicator';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar msg-avatar--bot';
    avatar.textContent = '🤖';

    const dots = document.createElement('div');
    dots.className = 'typing-dots';
    dots.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;

    wrap.appendChild(avatar);
    wrap.appendChild(dots);
    chatBody.appendChild(wrap);
    scrollBottom();
    return wrap;
  }

  function removeTyping() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
  }

  // ── Suggestions ───────────────────────────────────────────────────────
  function hideSuggestions() {
    sugBar.style.display = 'none';
    sugBar.innerHTML = '';
  }

  async function fetchSuggestions(partial) {
    if (!partial || partial.length < 3) { hideSuggestions(); return; }
    try {
      const res = await fetch('/api/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ partial })
      });
      const data = await res.json();
      const suggestions = data.suggestions || [];
      if (!suggestions.length) { hideSuggestions(); return; }

      sugBar.innerHTML = suggestions.map(s =>
        `<button class="suggestion-pill" role="option" aria-selected="false">${s}</button>`
      ).join('');
      sugBar.style.display = 'flex';

      sugBar.querySelectorAll('.suggestion-pill').forEach(pill => {
        pill.addEventListener('click', () => {
          userInput.value = pill.textContent;
          hideSuggestions();
          userInput.focus();
          autoResize();
        });
      });
    } catch (_) { hideSuggestions(); }
  }

  // ── Send Message ──────────────────────────────────────────────────────
  async function sendMessage(text) {
    text = (text || userInput.value).trim();
    if (!text || isWaiting) return;

    isWaiting = true;
    sendBtn.disabled = true;
    userInput.value = '';
    autoResize();
    hideSuggestions();

    appendUserMsg(text);

    // Simulate a small "reading" delay before typing indicator
    await delay(120);
    const typingEl = showTyping();

    // Random typing delay: 600ms–1400ms (feels natural)
    await delay(600 + Math.random() * 800);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      removeTyping();

      if (data.error) {
        appendBotMsg('⚠️ Sorry, something went wrong. Please try again.');
      } else {
        appendBotMsg(data.response);
        saveHistory(text, data.response);
      }
    } catch (_) {
      removeTyping();
      appendBotMsg('⚠️ I\'m having trouble connecting. Please check your internet and try again.');
    }

    isWaiting = false;
    sendBtn.disabled = false;
    userInput.focus();
  }

  function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ── Auto-resize Textarea ──────────────────────────────────────────────
  function autoResize() {
    userInput.style.height = 'auto';
    const maxH = 140;
    userInput.style.height = Math.min(userInput.scrollHeight, maxH) + 'px';
  }

  // ── Restore Session History ───────────────────────────────────────────
  function restoreHistory() {
    const hist = loadHistory();
    if (!hist.length) { showWelcome(); return; }

    // Show last 20 messages from history
    const recent = hist.slice(-20);
    recent.forEach(item => {
      if (item.role === 'user') appendUserMsg(item.text);
      else appendBotMsg(item.text, false);
    });
    scrollBottom(false);
  }

  // ── Event Listeners ───────────────────────────────────────────────────

  // Send button
  sendBtn.addEventListener('click', () => sendMessage());

  // Enter to send (Shift+Enter = newline)
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize + suggestions on input
  userInput.addEventListener('input', () => {
    autoResize();
    clearTimeout(suggestTimer);
    suggestTimer = setTimeout(() => fetchSuggestions(userInput.value.trim()), 300);
  });

  // Hide suggestions on blur (delay to allow click)
  userInput.addEventListener('blur', () => {
    setTimeout(hideSuggestions, 200);
  });

  // Clear chat
  clearBtn.addEventListener('click', () => {
    if (!confirm('Clear conversation? This cannot be undone.')) return;
    chatBody.innerHTML = '';
    sessionStorage.removeItem(SESSION_KEY);
    showWelcome();
  });

  // Quick topic chips in sidebar
  topicChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const question = chip.dataset.q;
      if (question) sendMessage(question);
    });
  });

  // ── Init ──────────────────────────────────────────────────────────────
  restoreHistory();
  userInput.focus();

})();
