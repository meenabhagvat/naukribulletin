/**
 * NaukriBot Chat Widget
 * Inject this script on every page via scraper template
 * Calls the Cloudflare Worker proxy
 */
(function() {
  if (document.getElementById('nb-chat-widget')) return; // already loaded

  const WORKER_URL = 'https://naukri-chat.meenabhagvat.workers.dev'; // update after worker deploy

  // ── Styles ──────────────────────────────────────────────────────────────────
  const style = document.createElement('style');
  style.textContent = `
    #nb-chat-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      width: 56px; height: 56px; border-radius: 50%;
      background: linear-gradient(135deg, #FF6B00, #FF8C33);
      border: none; cursor: pointer; box-shadow: 0 4px 20px rgba(255,107,0,.4);
      display: flex; align-items: center; justify-content: center;
      font-size: 1.4rem; transition: transform .2s, box-shadow .2s;
    }
    #nb-chat-btn:hover { transform: scale(1.1); box-shadow: 0 6px 28px rgba(255,107,0,.5); }
    #nb-chat-btn.open { background: linear-gradient(135deg, #333, #555); }

    #nb-chat-box {
      position: fixed; bottom: 92px; right: 24px; z-index: 9998;
      width: min(380px, calc(100vw - 32px));
      height: min(520px, calc(100vh - 120px));
      background: #0A0A0F; border: 1px solid rgba(255,107,0,.3);
      border-radius: 18px; display: flex; flex-direction: column;
      box-shadow: 0 20px 60px rgba(0,0,0,.6);
      transform: scale(.95) translateY(10px); opacity: 0;
      pointer-events: none; transition: all .2s cubic-bezier(.34,1.56,.64,1);
    }
    #nb-chat-box.open {
      transform: scale(1) translateY(0); opacity: 1; pointer-events: all;
    }

    #nb-chat-header {
      padding: 14px 18px; border-bottom: 1px solid rgba(255,255,255,.08);
      display: flex; align-items: center; gap: 10px; border-radius: 18px 18px 0 0;
      background: rgba(255,107,0,.08);
    }
    .nb-bot-avatar {
      width: 36px; height: 36px; border-radius: 50%;
      background: linear-gradient(135deg, #FF6B00, #FF8C33);
      display: flex; align-items: center; justify-content: center;
      font-size: 1.1rem; flex-shrink: 0;
    }
    #nb-chat-header h3 { margin: 0; font-size: .95rem; color: #fff; font-weight: 700; }
    #nb-chat-header p { margin: 0; font-size: .72rem; color: #63FFDA; }
    #nb-chat-close {
      margin-left: auto; background: none; border: none; color: #888;
      cursor: pointer; font-size: 1.2rem; padding: 4px;
    }

    #nb-chat-messages {
      flex: 1; overflow-y: auto; padding: 16px; display: flex;
      flex-direction: column; gap: 10px;
      scrollbar-width: thin; scrollbar-color: #333 transparent;
    }
    .nb-msg {
      max-width: 85%; padding: 10px 14px; border-radius: 14px;
      font-size: .88rem; line-height: 1.5; animation: nbFadeIn .2s ease;
    }
    .nb-msg.bot {
      background: rgba(255,255,255,.06); color: #E8E8F0;
      border: 1px solid rgba(255,255,255,.08); align-self: flex-start;
      border-radius: 4px 14px 14px 14px;
    }
    .nb-msg.user {
      background: linear-gradient(135deg, #FF6B00, #FF8C33); color: #fff;
      align-self: flex-end; border-radius: 14px 4px 14px 14px;
    }
    .nb-msg.typing { color: #888; font-style: italic; }
    @keyframes nbFadeIn { from { opacity:0; transform: translateY(6px); } to { opacity:1; transform: none; } }

    #nb-chat-suggestions {
      padding: 8px 12px; display: flex; gap: 6px; flex-wrap: wrap;
      border-top: 1px solid rgba(255,255,255,.06);
    }
    .nb-sugg {
      background: rgba(255,107,0,.1); border: 1px solid rgba(255,107,0,.3);
      color: #FF8C33; padding: 5px 10px; border-radius: 20px;
      font-size: .75rem; cursor: pointer; transition: .15s; white-space: nowrap;
    }
    .nb-sugg:hover { background: rgba(255,107,0,.2); }

    #nb-chat-input-area {
      padding: 12px; border-top: 1px solid rgba(255,255,255,.08);
      display: flex; gap: 8px; border-radius: 0 0 18px 18px;
    }
    #nb-chat-input {
      flex: 1; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1);
      border-radius: 10px; padding: 9px 14px; color: #fff; font-size: .88rem;
      font-family: 'DM Sans', sans-serif; outline: none; resize: none;
      max-height: 80px;
    }
    #nb-chat-input:focus { border-color: rgba(255,107,0,.5); }
    #nb-chat-send {
      background: linear-gradient(135deg, #FF6B00, #FF8C33);
      border: none; border-radius: 10px; width: 38px; height: 38px;
      cursor: pointer; color: #fff; font-size: 1rem; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      transition: .15s; align-self: flex-end;
    }
    #nb-chat-send:hover { transform: scale(1.05); }
    #nb-chat-send:disabled { opacity: .5; cursor: not-allowed; }
  `;
  document.head.appendChild(style);

  // ── HTML ────────────────────────────────────────────────────────────────────
  const wrap = document.createElement('div');
  wrap.id = 'nb-chat-widget';
  wrap.innerHTML = `
    <button id="nb-chat-btn" title="Ask NaukriBot">🤖</button>
    <div id="nb-chat-box">
      <div id="nb-chat-header">
        <div class="nb-bot-avatar">🤖</div>
        <div>
          <h3>NaukriBot</h3>
          <p>● Online — Govt Exam AI</p>
        </div>
        <button id="nb-chat-close">✕</button>
      </div>
      <div id="nb-chat-messages">
        <div class="nb-msg bot">
          Namaste! 👋 I'm <strong>NaukriBot</strong>, your govt exam assistant.<br><br>
          Ask me about <strong>SSC, UPSC, Banking, Railway</strong> exams — eligibility, syllabus, salary, cut-offs, or how to apply for any job on this site.
        </div>
      </div>
      <div id="nb-chat-suggestions">
        <button class="nb-sugg" data-q="SSC CGL 2026 eligibility and syllabus">SSC CGL syllabus</button>
        <button class="nb-sugg" data-q="IBPS PO salary in hand 2026">IBPS PO salary</button>
        <button class="nb-sugg" data-q="Am I eligible for UPSC CSE? My DOB is ">UPSC eligibility</button>
        <button class="nb-sugg" data-q="Best books for SSC CGL preparation">Best books SSC</button>
      </div>
      <div id="nb-chat-input-area">
        <textarea id="nb-chat-input" placeholder="Ask about any govt exam…" rows="1"></textarea>
        <button id="nb-chat-send">➤</button>
      </div>
    </div>
  `;
  document.body.appendChild(wrap);

  // ── Logic ───────────────────────────────────────────────────────────────────
  const btn    = document.getElementById('nb-chat-btn');
  const box    = document.getElementById('nb-chat-box');
  const msgs   = document.getElementById('nb-chat-messages');
  const input  = document.getElementById('nb-chat-input');
  const send   = document.getElementById('nb-chat-send');
  const close  = document.getElementById('nb-chat-close');
  const suggWrap = document.getElementById('nb-chat-suggestions');
  let history  = [];
  let isOpen   = false;

  function toggleChat() {
    isOpen = !isOpen;
    box.classList.toggle('open', isOpen);
    btn.classList.toggle('open', isOpen);
    btn.textContent = isOpen ? '✕' : '🤖';
    if (isOpen) { input.focus(); suggWrap.style.display = 'flex'; }
  }

  btn.addEventListener('click', toggleChat);
  close.addEventListener('click', toggleChat);

  function addMsg(text, role) {
    const d = document.createElement('div');
    d.className = 'nb-msg ' + role;
    d.innerHTML = text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>');
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
    return d;
  }

  async function sendMessage(text) {
    if (!text.trim() || send.disabled) return;
    suggWrap.style.display = 'none';
    addMsg(text, 'user');
    history.push({ role: 'user', content: text });
    input.value = '';
    input.style.height = 'auto';
    send.disabled = true;

    const typing = addMsg('NaukriBot is thinking…', 'bot typing');

    try {
      const res = await fetch(WORKER_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history }),
      });
      const data = await res.json();
      const reply = data.reply || data.error || 'Sorry, something went wrong.';
      typing.remove();
      addMsg(reply, 'bot');
      history.push({ role: 'assistant', content: reply });
      if (history.length > 12) history = history.slice(-12);
    } catch (e) {
      typing.remove();
      addMsg('Network error. Please check your connection and try again.', 'bot');
    }
    send.disabled = false;
    input.focus();
  }

  send.addEventListener('click', () => sendMessage(input.value));
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input.value); }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 80) + 'px';
  });
  document.querySelectorAll('.nb-sugg').forEach(b => {
    b.addEventListener('click', () => sendMessage(b.dataset.q));
  });
})();
