export function getWebviewContent(webview: any, extensionUri: any) {
  const nonce = Date.now().toString();
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src https: data:; script-src 'nonce-${nonce}'; style-src 'unsafe-inline'; font-src https:;">
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>AlgoDraft</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --purple-900: #0d001f;
    --purple-800: #1a0035;
    --purple-700: #2d0060;
    --purple-600: #450090;
    --purple-500: #6100C2;
    --purple-400: #7a1fd4;
    --purple-300: #9b4de0;
    --purple-200: #bb82eb;
    --purple-100: #d9baef;
    --purple-50:  #f0e4fa;
    --accent:     #c76dff;
    --accent-glow: rgba(97, 0, 194, 0.45);
    --bg-base:    #090018;
    --bg-panel:   #110028;
    --bg-elevated:#220045;
    --code-bg:    rgba(30, 0, 65, 0.75);
    --border:        rgba(97, 0, 194, 0.35);
    --border-bright: rgba(140, 60, 220, 0.6);
    --text-primary:   #ede0ff;
    --text-secondary: #c4a0e8;
    --text-muted:     #7a5a9a;
    --text-dim:       #4a3566;
    --font-ui:   'Syne', sans-serif;
    --font-mono: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace;
    --radius-sm: 4px;
    --radius-md: 8px;
    --canvas-width: 42%;
    --canvas-min: 360px;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  html, body {
    height: 100%;
    background: var(--bg-base);
    color: var(--text-primary);
    font-family: var(--font-ui);
    overflow: hidden;
  }

  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
      radial-gradient(ellipse 60% 50% at 20% 30%, rgba(97,0,194,0.18) 0%, transparent 70%),
      radial-gradient(ellipse 40% 30% at 80% 70%, rgba(140,0,255,0.12) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
  }

  #app {
    position: relative;
    z-index: 1;
    display: flex;
    height: 100vh;
    overflow: hidden;
  }

  #main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: margin-right 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  }

  #main-area.canvas-open { margin-right: var(--canvas-width); }

  #header {
    padding: 14px 22px;
    border-bottom: 1px solid var(--border-bright);
    background: linear-gradient(90deg, var(--purple-800) 0%, rgba(26,0,53,0.9) 100%);
    display: flex;
    align-items: center;
    gap: 12px;
    backdrop-filter: blur(8px);
    flex-shrink: 0;
  }

  #header .dot {
    width: 9px; height: 9px;
    border-radius: 50%;
    background: var(--purple-300);
    box-shadow: 0 0 10px var(--accent), 0 0 20px var(--purple-500);
    animation: pulse 2.5s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { box-shadow: 0 0 10px var(--accent), 0 0 20px var(--purple-500); }
    50%       { box-shadow: 0 0 16px var(--accent), 0 0 32px var(--purple-400); }
  }

  #header h1 {
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    background: linear-gradient(90deg, #e8d0ff 0%, #a96bec 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  #chat {
    flex: 1;
    overflow-y: auto;
    padding: 28px 24px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    scrollbar-width: thin;
    scrollbar-color: var(--purple-700) transparent;
  }

  #chat::-webkit-scrollbar { width: 4px; }
  #chat::-webkit-scrollbar-thumb { background: var(--purple-700); border-radius: 2px; }

  .message { display: flex; gap: 10px; animation: slideUp 0.22s ease-out both; }
  .message.user { flex-direction: row-reverse; }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .msg-content { max-width: 88%; display: flex; flex-direction: column; gap: 6px; }
  .message.user .msg-content { align-items: flex-end; }

  .bubble {
    padding: 10px 14px;
    border-radius: 14px 14px 3px 14px;
    font-size: 13px;
    line-height: 1.6;
    background: linear-gradient(135deg, var(--purple-500), var(--purple-400));
    color: #fff;
    box-shadow: 0 3px 14px rgba(97,0,194,0.45);
  }

  .bot-label {
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-muted);
    font-weight: 600;
  }

  .section {
    background: linear-gradient(135deg, rgba(26,0,53,0.95) 0%, rgba(34,0,69,0.95) 100%);
    border: 1px solid var(--border);
    padding: 12px 16px;
    border-radius: var(--radius-md);
    font-size: 13px;
    line-height: 1.7;
    color: var(--text-secondary);
  }

  .response-container { display: flex; flex-direction: column; gap: 12px; width: 100%; }

  .inline-code {
    background: rgba(97, 0, 194, 0.25);
    border: 1px solid var(--border);
    padding: 1px 5px;
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--purple-200);
  }

  .code-block {
    border-radius: var(--radius-md);
    overflow: hidden;
    font-family: var(--font-mono);
    box-shadow: 0 0 0 1px var(--border-bright), 0 4px 24px rgba(97,0,194,0.25);
    transition: box-shadow 0.2s;
  }

  .code-block:hover {
    box-shadow: 0 0 0 1px rgba(170,80,255,0.7), 0 6px 32px rgba(97,0,194,0.38);
  }

  .code-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 9px 14px;
    background: linear-gradient(90deg, rgba(69,0,144,0.55) 0%, rgba(45,0,96,0.55) 100%);
    border-bottom: 1px solid var(--border-bright);
    gap: 10px;
  }

  .lang-tag { display: flex; align-items: center; gap: 7px; }

  .lang-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--purple-300);
    box-shadow: 0 0 8px var(--purple-300);
    flex-shrink: 0;
  }

  .lang-name {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--purple-200);
  }

  .code-btn-group { display: flex; align-items: center; gap: 6px; }

  .code-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.18s ease;
    white-space: nowrap;
    line-height: 1;
  }

  .copy-btn { background: rgba(97,0,194,0.3); color: var(--purple-100); border-color: var(--border-bright); }
  .copy-btn:hover { background: rgba(97,0,194,0.55); border-color: rgba(180,100,255,0.7); color: #fff; box-shadow: 0 0 12px var(--accent-glow); }
  .copy-btn.copied { background: rgba(61,186,134,0.25); border-color: rgba(61,186,134,0.6); color: #6ee7b7; }

  .canvas-btn { background: rgba(199,109,255,0.12); color: var(--purple-200); border-color: rgba(199,109,255,0.35); }
  .canvas-btn:hover { background: rgba(199,109,255,0.28); border-color: rgba(199,109,255,0.65); color: var(--accent); box-shadow: 0 0 14px rgba(199,109,255,0.3); transform: translateY(-1px); }
  .canvas-btn.active { background: rgba(199,109,255,0.22); border-color: var(--accent); color: var(--accent); }

  .btn-icon { font-size: 11px; line-height: 1; }

  .code-body { background: var(--code-bg); padding: 16px 18px; overflow-x: auto; }
  .code-body pre { margin: 0; font-family: var(--font-mono); font-size: 12.5px; line-height: 1.75; color: var(--purple-50); white-space: pre; }

  /* Canvas panel */
  #canvas-panel {
    position: fixed;
    top: 0; right: 0;
    width: 0; height: 100vh;
    background: var(--bg-panel);
    border-left: 1px solid var(--border-bright);
    box-shadow: -4px 0 32px rgba(97,0,194,0.3);
    transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 100;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  #canvas-panel.open { width: var(--canvas-width); min-width: var(--canvas-min); }

  #canvas-top {
    padding: 14px 18px;
    border-bottom: 1px solid var(--border-bright);
    background: linear-gradient(90deg, var(--purple-800) 0%, rgba(26,0,53,0.95) 100%);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
    gap: 10px;
  }

  #canvas-top > div { display: flex; align-items: center; gap: 10px; }

  #canvas-lang-badge {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
    background: rgba(199,109,255,0.12);
    border: 1px solid rgba(199,109,255,0.35);
    padding: 3px 9px;
    border-radius: 3px;
  }

  #canvas-title {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--purple-100);
  }

  #canvas-top-right { display: flex; align-items: center; gap: 6px; }

  #canvas-copy-btn {
    display: flex; align-items: center; gap: 5px;
    padding: 5px 11px;
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: 10px; font-weight: 600;
    background: rgba(97,0,194,0.3);
    color: var(--purple-100);
    border: 1px solid var(--border-bright);
    cursor: pointer;
    transition: all 0.18s ease;
    white-space: nowrap;
  }

  #canvas-copy-btn:hover { background: rgba(97,0,194,0.55); color: #fff; box-shadow: 0 0 12px var(--accent-glow); }
  #canvas-copy-btn.copied { background: rgba(61,186,134,0.2); border-color: rgba(61,186,134,0.5); color: #6ee7b7; }

  #canvas-close-btn {
    background: transparent;
    color: var(--text-muted);
    border: 1px solid var(--border);
    padding: 5px 8px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s;
  }

  #canvas-close-btn:hover { background: rgba(255,80,80,0.15); border-color: rgba(255,80,80,0.5); color: #ff6464; }

  #canvas-body { flex: 1; overflow: hidden; padding: 16px; display: flex; flex-direction: column; }

  #canvas-editor {
    flex: 1; width: 100%;
    background: rgba(14,0,32,0.9);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    color: var(--purple-50);
    font-family: var(--font-mono);
    font-size: 12.5px;
    line-height: 1.75;
    padding: 16px;
    resize: none;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
    tab-size: 2;
    overflow: auto;
  }

  #canvas-editor:focus { border-color: var(--purple-400); box-shadow: 0 0 0 2px rgba(97,0,194,0.2), 0 0 20px rgba(97,0,194,0.15); }

  /* Input area */
  #input-area {
    padding: 14px 18px;
    border-top: 1px solid var(--border-bright);
    background: linear-gradient(180deg, rgba(17,0,40,0.95) 0%, rgba(9,0,24,0.98) 100%);
    flex-shrink: 0;
  }

  #upload-section { display: flex; gap: 6px; margin-bottom: 8px; align-items: center; flex-wrap: wrap; }

  #upload-btn {
    padding: 6px 12px;
    font-size: 11px; font-weight: 600;
    white-space: nowrap; flex-shrink: 0;
    background: transparent;
    color: var(--purple-300);
    border: 1px solid var(--border-bright);
    border-radius: 5px;
    cursor: pointer;
    transition: all 0.2s;
  }

  #upload-btn:hover { background: rgba(97,0,194,0.25); color: var(--purple-100); box-shadow: 0 0 10px var(--accent-glow); }

  #file-input { display: none; }
  #papers-list { display: flex; gap: 6px; flex-wrap: wrap; }

  .paper-tag {
    display: flex; align-items: center; gap: 4px;
    padding: 3px 8px;
    background: rgba(97,0,194,0.2);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: 11px; max-width: 150px;
    color: var(--purple-200);
  }

  .paper-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .paper-remove {
    cursor: pointer; padding: 0 2px;
    border: none; background: none;
    color: #e05c7a; font-size: 10px;
    transition: opacity 0.2s;
  }

  .paper-remove:hover { opacity: 0.7; }

  #query-area { display: flex; gap: 8px; }

  textarea#prompt {
    flex: 1;
    min-height: 36px; max-height: 120px;
    padding: 9px 13px;
    background: var(--bg-elevated);
    color: var(--text-primary);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-family: var(--font-ui);
    font-size: 12px;
    resize: none; outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  textarea#prompt::placeholder { color: var(--text-dim); }
  textarea#prompt:focus { border-color: var(--purple-400); box-shadow: 0 0 0 2px rgba(97,0,194,0.2); }

  #send {
    padding: 8px 16px;
    background: linear-gradient(135deg, var(--purple-500) 0%, var(--purple-400) 100%);
    color: #fff; border: none; border-radius: 6px;
    cursor: pointer; font-size: 12px; font-weight: 600;
    white-space: nowrap; flex-shrink: 0;
    transition: all 0.2s;
    box-shadow: 0 2px 10px rgba(97,0,194,0.4);
  }

  #send:hover { background: linear-gradient(135deg, var(--purple-400) 0%, var(--purple-300) 100%); box-shadow: 0 2px 16px rgba(97,0,194,0.6); transform: translateY(-1px); }

  #settings-toggle {
    padding: 8px 11px; font-size: 13px; flex-shrink: 0;
    background: transparent; color: var(--text-muted);
    border: 1px solid var(--border); border-radius: 6px;
    cursor: pointer; transition: all 0.2s;
  }

  #settings-toggle:hover { background: rgba(97,0,194,0.2); color: var(--purple-200); border-color: var(--border-bright); }

  #settings { display: none; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); max-height: 160px; overflow-y: auto; }
  #settings.visible { display: block; }

  .settings-group { margin-bottom: 10px; }

  .settings-group label {
    display: block; font-size: 11px; font-weight: 600;
    letter-spacing: 0.07em; text-transform: uppercase;
    margin-bottom: 4px; color: var(--text-muted);
  }

  .settings-group input,
  .settings-group select {
    width: 100%; padding: 6px 9px;
    background: var(--bg-elevated);
    color: var(--text-primary);
    border: 1px solid var(--border);
    border-radius: 4px; font-size: 11px;
    font-family: inherit; transition: border-color 0.2s;
  }

  .settings-group input:focus,
  .settings-group select:focus { outline: none; border-color: var(--purple-400); box-shadow: 0 0 8px rgba(97,0,194,0.3); }
  .settings-group select option { background: var(--bg-elevated); }

  #savecfg {
    width: 100%; padding: 7px; margin-top: 6px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.06em;
    background: linear-gradient(135deg, var(--purple-500), var(--purple-400));
    color: #fff; border: none; border-radius: 5px;
    cursor: pointer; transition: all 0.2s;
  }

  #savecfg:hover { background: linear-gradient(135deg, var(--purple-400), var(--purple-300)); box-shadow: 0 0 12px rgba(97,0,194,0.45); }
</style>
</head>
<body>

<div id="app">
  <div id="main-area">
    <div id="header">
      <div class="dot"></div>
      <h1>AlgoDraft</h1>
    </div>

    <div id="chat"></div>

    <div id="input-area">
      <div id="upload-section">
        <button id="upload-btn">📎 Upload</button>
        <input type="file" id="file-input" accept=".pdf,.txt,.tex,.md" multiple />
        <div id="papers-list"></div>
      </div>

      <div id="query-area">
        <textarea id="prompt" placeholder="Ask about your papers..." spellcheck="false"></textarea>
        <button id="send">Send</button>
        <button id="settings-toggle">⚙️</button>
      </div>

      <div id="settings">
        <div class="settings-group">
          <label>Mode:</label>
          <select id="mode">
            <option value="local">Local (Ollama)</option>
            <option value="cloud">Cloud (API)</option>
          </select>
        </div>
        <div id="provider-group" class="settings-group" style="display: none;">
          <label>Provider:</label>
          <select id="provider">
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="huggingface">Hugging Face</option>
          </select>
        </div>
        <div class="settings-group">
          <label>Model:</label>
          <input id="model" type="text" value="mistral" />
        </div>
        <div id="apikey-group" class="settings-group" style="display: none;">
          <label>API Key:</label>
          <input id="apikey" type="password" placeholder="sk-..." />
        </div>
        <button id="savecfg">Save Config</button>
      </div>
    </div>
  </div>

  <div id="canvas-panel">
    <div id="canvas-top">
      <div>
        <span id="canvas-lang-badge">js</span>
        <span id="canvas-title">Code Canvas</span>
      </div>
      <div id="canvas-top-right">
        <button id="canvas-copy-btn">⎘ Copy</button>
        <button id="canvas-close-btn" title="Close canvas">✕</button>
      </div>
    </div>
    <div id="canvas-body">
      <textarea id="canvas-editor" spellcheck="false"></textarea>
    </div>
  </div>
</div>

<script nonce="${nonce}">
  const vscode = acquireVsCodeApi();

  // Grab elements directly — same flat pattern as the working code
  const chat            = document.getElementById('chat');
  const modeSelect      = document.getElementById('mode');
  const providerGroup   = document.getElementById('provider-group');
  const apikeyGroup     = document.getElementById('apikey-group');
  const settingsToggle  = document.getElementById('settings-toggle');
  const settingsPanel   = document.getElementById('settings');
  const canvasPanel     = document.getElementById('canvas-panel');
  const canvasEditor    = document.getElementById('canvas-editor');
  const canvasCopyBtn   = document.getElementById('canvas-copy-btn');
  const canvasCloseBtn  = document.getElementById('canvas-close-btn');
  const canvasLangBadge = document.getElementById('canvas-lang-badge');
  const mainArea        = document.getElementById('main-area');
  const papersList      = document.getElementById('papers-list');

  let activeCanvasBtn = null;

  // Settings
  modeSelect.addEventListener('change', updateModeUI);
  document.getElementById('provider').addEventListener('change', updateProviderModel);
  settingsToggle.addEventListener('click', () => settingsPanel.classList.toggle('visible'));
  updateModeUI();

  function updateModeUI() {
    const mode = modeSelect.value;
    providerGroup.style.display = mode === 'cloud' ? 'block' : 'none';
    apikeyGroup.style.display   = mode === 'cloud' ? 'block' : 'none';
    if (mode === 'cloud') updateProviderModel();
  }

  function updateProviderModel() {
    const provider = document.getElementById('provider').value;
    const defaults = { openai: 'gpt-4o', anthropic: 'claude-3-5-sonnet-20241022', huggingface: 'meta-llama/Llama-2-70b-chat-hf' };
    document.getElementById('model').value = defaults[provider] || '';
  }

  // Canvas
  canvasCloseBtn.addEventListener('click', closeCanvas);
  canvasCopyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(canvasEditor.value).then(() => {
      canvasCopyBtn.innerHTML = '<span>✓</span> Copied!';
      canvasCopyBtn.classList.add('copied');
      setTimeout(() => { canvasCopyBtn.innerHTML = '<span>⎘</span> Copy'; canvasCopyBtn.classList.remove('copied'); }, 2000);
    });
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && canvasPanel.classList.contains('open')) closeCanvas();
  });

  function openCanvas(code, lang) {
    canvasEditor.value = code;
    canvasLangBadge.textContent = lang;
    canvasPanel.classList.add('open');
    mainArea.classList.add('canvas-open');
    canvasEditor.focus();
  }

  function closeCanvas() {
    canvasPanel.classList.remove('open');
    mainArea.classList.remove('canvas-open');
    if (activeCanvasBtn) { activeCanvasBtn.classList.remove('active'); activeCanvasBtn = null; }
  }

  // Response formatting
  function formatResponse(text) {
    const container = document.createElement('div');
    container.className = 'response-container';
    const bt = String.fromCharCode(96);
    const parts = text.split(new RegExp('(' + bt + bt + bt + '[\\s\\S]*?' + bt + bt + bt + '|' + bt + '[^' + bt + ']*' + bt + ')', 'g'));
    let textBuf = '';
    parts.forEach(part => {
      if (!part) return;
      if (part.startsWith(bt + bt + bt)) {
        if (textBuf.trim()) { container.appendChild(createSection(textBuf.trim())); textBuf = ''; }
        container.appendChild(createCodeBlock(part));
      } else {
        textBuf += part;
      }
    });
    if (textBuf.trim()) container.appendChild(createSection(textBuf.trim()));
    return container;
  }

  function createSection(text) {
    const section = document.createElement('div');
    section.className = 'section';
    const bt = String.fromCharCode(96);
    const textParts = text.split(new RegExp(bt + '[^' + bt + ']*' + bt, 'g'));
    const codeParts = text.match(new RegExp(bt + '[^' + bt + ']*' + bt, 'g')) || [];
    let ci = 0;
    textParts.forEach(tp => {
      if (tp) section.appendChild(document.createTextNode(tp));
      if (ci < codeParts.length) {
        const code = document.createElement('code');
        code.className = 'inline-code';
        code.textContent = codeParts[ci].slice(1, -1);
        section.appendChild(code);
        ci++;
      }
    });
    return section;
  }

  function createCodeBlock(blockText) {
    const container = document.createElement('div');
    container.className = 'code-block';
    const content     = blockText.slice(3, -3);
    const lines       = content.split('\\n');
    const firstLine   = lines[0] || '';
    const lang        = firstLine.match(/^([a-z0-9]*)/i)?.[1] || 'code';
    const codeContent = content.slice(firstLine.length).replace(/^\\n/, '').trimEnd();

    const header = document.createElement('div');
    header.className = 'code-header';

    const langTag = document.createElement('div');
    langTag.className = 'lang-tag';
    const dot = document.createElement('div');
    dot.className = 'lang-dot';
    const langName = document.createElement('span');
    langName.className = 'lang-name';
    langName.textContent = lang;
    langTag.appendChild(dot);
    langTag.appendChild(langName);

    const btnGroup = document.createElement('div');
    btnGroup.className = 'code-btn-group';

    const copyBtn = document.createElement('button');
    copyBtn.className = 'code-btn copy-btn';
    copyBtn.innerHTML = '<span class="btn-icon">⎘</span> Copy';
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(codeContent).then(() => {
        copyBtn.innerHTML = '<span class="btn-icon">✓</span> Copied!';
        copyBtn.classList.add('copied');
        setTimeout(() => { copyBtn.innerHTML = '<span class="btn-icon">⎘</span> Copy'; copyBtn.classList.remove('copied'); }, 2000);
      });
    });

    const canvasBtn = document.createElement('button');
    canvasBtn.className = 'code-btn canvas-btn';
    canvasBtn.innerHTML = '<span class="btn-icon">◈</span> Canvas';
    canvasBtn.addEventListener('click', () => {
      if (activeCanvasBtn === canvasBtn && canvasPanel.classList.contains('open')) { closeCanvas(); return; }
      if (activeCanvasBtn) activeCanvasBtn.classList.remove('active');
      activeCanvasBtn = canvasBtn;
      canvasBtn.classList.add('active');
      openCanvas(codeContent, lang);
    });

    btnGroup.appendChild(copyBtn);
    btnGroup.appendChild(canvasBtn);
    header.appendChild(langTag);
    header.appendChild(btnGroup);

    const codeDiv = document.createElement('div');
    codeDiv.className = 'code-body';
    const pre = document.createElement('pre');
    pre.textContent = codeContent;
    codeDiv.appendChild(pre);

    container.appendChild(header);
    container.appendChild(codeDiv);
    return container;
  }

  function addMsg(txt, cls) {
    cls = cls || 'bot';
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ' + cls;
    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';
    if (cls === 'bot') {
      const label = document.createElement('div');
      label.className = 'bot-label';
      label.textContent = 'AlgoDraft';
      contentDiv.appendChild(label);
      contentDiv.appendChild(formatResponse(txt));
    } else {
      const bubble = document.createElement('div');
      bubble.className = 'bubble';
      bubble.textContent = txt;
      contentDiv.appendChild(bubble);
    }
    msgDiv.appendChild(contentDiv);
    chat.appendChild(msgDiv);
    chat.scrollTop = chat.scrollHeight;
  }

  // Send
  document.getElementById('send').addEventListener('click', sendMessage);
  document.getElementById('prompt').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  function sendMessage() {
    const prompt = document.getElementById('prompt').value.trim();
    if (!prompt) return;
    addMsg(prompt, 'user');
    vscode.postMessage({ type: 'query', payload: { prompt } });
    document.getElementById('prompt').value = '';
  }

  // Upload
  document.getElementById('upload-btn').addEventListener('click', () => document.getElementById('file-input').click());
  document.getElementById('file-input').addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const data = ev.target.result;
        if (data && typeof data === 'string') {
          vscode.postMessage({ type: 'upload', payload: { file: { name: file.name, data: data.split(',')[1] } } });
        }
      };
      reader.readAsDataURL(file);
    });
    e.target.value = '';
  });

  // Papers
  function loadPapersList() { vscode.postMessage({ type: 'loadPapers', payload: {} }); }
  function removePaper(filename) { vscode.postMessage({ type: 'removePaper', payload: { filename } }); }

  function renderPapersList(papers) {
    papersList.innerHTML = '';
    papers.forEach(paper => {
      const tag = document.createElement('div');
      tag.className = 'paper-tag';
      const name = document.createElement('span');
      name.className = 'paper-name';
      name.textContent = paper;
      name.title = paper;
      const removeBtn = document.createElement('button');
      removeBtn.className = 'paper-remove';
      removeBtn.textContent = '\\u2715';
      removeBtn.addEventListener('click', () => removePaper(paper));
      tag.appendChild(name);
      tag.appendChild(removeBtn);
      papersList.appendChild(tag);
    });
  }

  // Save config
  document.getElementById('savecfg').addEventListener('click', () => {
    const mode     = document.getElementById('mode').value;
    const model    = document.getElementById('model').value;
    const api_key  = document.getElementById('apikey').value || '';
    const provider = document.getElementById('provider').value;
    vscode.postMessage({
      type: 'saveConfig',
      payload: {
        mode,
        local_model:    mode === 'local' ? model    : undefined,
        cloud_model:    mode === 'cloud' ? model    : undefined,
        cloud_provider: mode === 'cloud' ? provider : undefined,
        api_key:        api_key || undefined
      }
    });
  });

  // Message handler
  window.addEventListener('message', event => {
    const m = event.data;
    if (m.type === 'answer')        addMsg(m.payload, 'bot');
    if (m.type === 'analysis')      addMsg('Analysis Result:\\n' + m.payload, 'bot');
    if (m.type === 'papersList')    renderPapersList(m.payload.papers || []);
    if (m.type === 'uploadSuccess') addMsg('\\u2713 File uploaded: ' + m.payload.filename, 'bot');
    if (m.type === 'uploadError')   addMsg('\\u2717 Upload error: ' + m.payload.error, 'bot');
    if (m.type === 'papersError')   addMsg('\\u2717 Error loading papers: ' + m.payload.error, 'bot');
  });

  loadPapersList();
</script>
</body>
</html>`;
}