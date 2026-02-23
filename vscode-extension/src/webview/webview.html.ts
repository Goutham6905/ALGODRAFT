export function getWebviewContent(webview: any, extensionUri: any) {
  const nonce = Date.now().toString();
  return `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src https: data:; script-src 'nonce-${nonce}'; style-src 'unsafe-inline';">
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>AlgoDraft</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0;
    padding: 0;
    background: var(--vscode-editor-background);
    color: var(--vscode-editor-foreground);
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }
  #container {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  #header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--vscode-input-border);
    background: var(--vscode-sideBar-background);
  }
  #header h2 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--vscode-editor-foreground);
  }
  #chat {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .message {
    display: flex;
    gap: 8px;
    animation: fadeIn 0.2s ease-in;
  }
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  .message.user {
    flex-direction: row-reverse;
  }
  .message-content {
    max-width: 85%;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .user .message-content {
    align-items: flex-end;
  }
  .user .msg-box {
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    padding: 8px 12px;
    border-radius: 8px;
    word-wrap: break-word;
    font-size: 13px;
    line-height: 1.4;
  }
  .bot .msg-box {
    padding: 0;
  }
  .section {
    background: var(--vscode-sideBar-background);
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 4px;
    font-size: 13px;
    line-height: 1.5;
  }
  .section p {
    margin: 6px 0;
  }
  .section p:first-child {
    margin-top: 0;
  }
  .section p:last-child {
    margin-bottom: 0;
  }
  .code-block {
    background: var(--vscode-textCodeBlock-background);
    border: 1px solid var(--vscode-input-border);
    border-radius: 6px;
    overflow: hidden;
    font-family: 'Courier New', monospace;
    margin-bottom: 4px;
  }
  .code-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: var(--vscode-diffEditor-removedLineBackground);
    font-size: 12px;
    color: var(--vscode-descriptionForeground);
  }
  .code-lang {
    font-weight: 500;
  }
  .code-copy-btn {
    padding: 4px 8px;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none;
    border-radius: 3px;
    cursor: pointer;
    font-size: 11px;
    transition: all 0.2s;
  }
  .code-copy-btn:hover {
    background: var(--vscode-button-hoverBackground);
  }
  .code-copy-btn.copied {
    background: #4ec9b0;
  }
  .code-content {
    padding: 12px;
    overflow-x: auto;
    font-size: 12px;
    line-height: 1.4;
    color: var(--vscode-editor-foreground);
  }
  .code-content pre {
    margin: 0;
    font-family: inherit;
    white-space: pre-wrap;
    word-wrap: break-word;
  }
  #input-area {
    padding: 12px 16px;
    border-top: 1px solid var(--vscode-input-border);
    background: var(--vscode-sideBar-background);
  }
  #controls {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
  }
  #upload-section {
    display: flex;
    gap: 6px;
    margin-bottom: 8px;
    align-items: center;
  }
  #upload-btn {
    padding: 6px 12px;
    font-size: 12px;
    white-space: nowrap;
    flex-shrink: 0;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  #upload-btn:hover {
    background: var(--vscode-button-hoverBackground);
  }
  #file-input {
    display: none;
  }
  #papers-list {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 8px;
  }
  .paper-tag {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: var(--vscode-textCodeBlock-background);
    border: 1px solid var(--vscode-input-border);
    border-radius: 4px;
    font-size: 11px;
    max-width: 150px;
  }
  .paper-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .paper-remove {
    cursor: pointer;
    padding: 0 2px;
    border: none;
    background: none;
    color: var(--vscode-errorForeground);
    font-size: 10px;
    transition: opacity 0.2s;
  }
  .paper-remove:hover {
    opacity: 0.7;
  }
  #query-area {
    display: flex;
    gap: 8px;
  }
  textarea {
    flex: 1;
    min-height: 36px;
    padding: 8px 12px;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border);
    border-radius: 4px;
    font-family: inherit;
    font-size: 12px;
    resize: none;
    font-weight: 400;
  }
  textarea:focus {
    outline: none;
    border-color: var(--vscode-focusBorder);
  }
  #send {
    padding: 8px 16px;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    white-space: nowrap;
    flex-shrink: 0;
  }
  #send:hover {
    background: var(--vscode-button-hoverBackground);
  }
  #settings-toggle {
    padding: 8px 12px;
    font-size: 12px;
    flex-shrink: 0;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  #settings-toggle:hover {
    background: var(--vscode-button-hoverBackground);
  }
  #settings {
    display: none;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--vscode-input-border);
    max-height: 150px;
    overflow-y: auto;
  }
  #settings.visible {
    display: block;
  }
  .settings-group {
    margin-bottom: 10px;
  }
  .settings-group label {
    display: block;
    font-size: 12px;
    font-weight: 500;
    margin-bottom: 4px;
    color: var(--vscode-editor-foreground);
  }
  .settings-group input,
  .settings-group select {
    width: 100%;
    padding: 6px 8px;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border);
    border-radius: 3px;
    font-size: 11px;
    font-family: inherit;
  }
  .settings-group input:focus,
  .settings-group select:focus {
    outline: none;
    border-color: var(--vscode-focusBorder);
  }
  #savecfg {
    width: 100%;
    padding: 6px;
    margin-top: 8px;
    font-size: 11px;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  #savecfg:hover {
    background: var(--vscode-button-hoverBackground);
  }
  .inline-code {
    background: var(--vscode-textCodeBlock-background);
    padding: 2px 4px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
  }
  .copy-text-btn {
    padding: 4px 8px;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none;
    border-radius: 3px;
    cursor: pointer;
    font-size: 11px;
    margin-left: 4px;
    transition: all 0.2s;
  }
  .copy-text-btn:hover {
    background: var(--vscode-button-hoverBackground);
  }
  .copy-text-btn.copied {
    background: #4ec9b0;
  }
</style>
</head>
<body>
  <div id="container">
    <div id="header">
      <h2>AlgoDraft</h2>
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

<script nonce="${nonce}">
  const vscode = acquireVsCodeApi();
  const chat = document.getElementById('chat');
  const modeSelect = document.getElementById('mode');
  const providerGroup = document.getElementById('provider-group');
  const apikeyGroup = document.getElementById('apikey-group');
  const settingsToggle = document.getElementById('settings-toggle');
  const settingsPanel = document.getElementById('settings');
  
  // Initialize
  modeSelect.addEventListener('change', updateModeUI);
  document.getElementById('provider')?.addEventListener('change', updateProviderModel);
  settingsToggle.addEventListener('click', () => settingsPanel.classList.toggle('visible'));
  updateModeUI();
  loadPapersList();
  
  function updateModeUI() {
    const mode = modeSelect.value;
    providerGroup.style.display = mode === 'cloud' ? 'block' : 'none';
    apikeyGroup.style.display = mode === 'cloud' ? 'block' : 'none';
    if (mode === 'cloud') updateProviderModel();
  }
  
  function updateProviderModel() {
    const provider = document.getElementById('provider').value;
    const defaults = {
      openai: 'gpt-4o',
      anthropic: 'claude-3-sonnet-20240229',
      huggingface: 'meta-llama/Llama-2-70b-chat-hf'
    };
    document.getElementById('model').value = defaults[provider] || '';
  }
  
  // Create copy button element
  function createCopyBtn(text) {
    const btn = document.createElement('button');
    btn.className = 'copy-text-btn';
    btn.textContent = 'Copy';
    btn.addEventListener('click', function() {
      navigator.clipboard.writeText(text).then(() => {
        this.textContent = '✓ Copied!';
        this.classList.add('copied');
        setTimeout(() => {
          this.textContent = 'Copy';
          this.classList.remove('copied');
        }, 2000);
      });
    });
    return btn;
  }
  
  // Format bot response with sections and code blocks
  function formatResponse(text) {
    const container = document.createElement('div');
    container.style.width = '100%';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '4px';
    
    const bt = String.fromCharCode(96);
    const codeBlockPattern = '(' + bt + bt + bt + '[\\s\\S]*?' + bt + bt + bt + '|' + bt + '[^' + bt + ']*' + bt + ')';
    const regex = new RegExp(codeBlockPattern, 'g');
    const parts = text.split(regex);
    
    let currentTextBlock = '';
    
    parts.forEach(part => {
      if (!part) return;
      
      if (part.startsWith(bt + bt + bt)) {
        // Flush any accumulated text
        if (currentTextBlock.trim()) {
          const section = createSection(currentTextBlock.trim());
          container.appendChild(section);
          currentTextBlock = '';
        }
        
        // Add code block
        const codeBlock = createCodeBlock(part);
        container.appendChild(codeBlock);
      } else if (part.startsWith(bt) && part.endsWith(bt) && !part.startsWith(bt + bt + bt)) {
        // Inline code in text - will be handled in section
        currentTextBlock += part;
      } else {
        // Regular text
        currentTextBlock += part;
      }
    });
    
    // Flush remaining text
    if (currentTextBlock.trim()) {
      const section = createSection(currentTextBlock.trim());
      container.appendChild(section);
    }
    
    return container;
  }
  
  function createSection(text) {
    const section = document.createElement('div');
    section.className = 'section';
    
    const bt = String.fromCharCode(96);
    const inlineCodePattern = bt + '[^' + bt + ']*' + bt;
    const inlineRegex = new RegExp(inlineCodePattern, 'g');
    const textParts = text.split(inlineRegex);
    const codeParts = text.match(inlineRegex) || [];
    
    let codeIdx = 0;
    textParts.forEach((textPart, idx) => {
      if (textPart) {
        section.appendChild(document.createTextNode(textPart));
      }
      if (codeIdx < codeParts.length) {
        const code = document.createElement('code');
        code.className = 'inline-code';
        code.textContent = codeParts[codeIdx].slice(1, -1);
        section.appendChild(code);
        codeIdx++;
      }
    });
    
    return section;
  }
  
  function createCodeBlock(blockText) {
    const container = document.createElement('div');
    container.className = 'code-block';
    
    const content = blockText.slice(3, -3);
    const lines = content.split('\\n');
    const firstLine = lines[0] || '';
    const lang = firstLine.match(/^([a-z0-9]*)/)?.[1] || 'code';
    const codeStart = firstLine.length + 1;
    const codeContent = content.slice(codeStart).trim();
    
    const header = document.createElement('div');
    header.className = 'code-header';
    
    const langSpan = document.createElement('span');
    langSpan.className = 'code-lang';
    langSpan.textContent = lang;
    
    const copyBtn = document.createElement('button');
    copyBtn.className = 'code-copy-btn';
    copyBtn.textContent = 'Copy';
    copyBtn.addEventListener('click', function() {
      navigator.clipboard.writeText(codeContent).then(() => {
        this.textContent = '✓ Copied!';
        this.classList.add('copied');
        setTimeout(() => {
          this.textContent = 'Copy';
          this.classList.remove('copied');
        }, 2000);
      });
    });
    
    header.appendChild(langSpan);
    header.appendChild(copyBtn);
    
    const codeDiv = document.createElement('div');
    codeDiv.className = 'code-content';
    const pre = document.createElement('pre');
    pre.textContent = codeContent;
    codeDiv.appendChild(pre);
    
    container.appendChild(header);
    container.appendChild(codeDiv);
    
    return container;
  }
  
  function addMsg(txt, cls = 'bot') {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ' + cls;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const msgBox = document.createElement('div');
    msgBox.className = 'msg-box';
    
    if (cls === 'bot') {
      msgBox.appendChild(formatResponse(txt));
    } else {
      msgBox.textContent = txt;
    }
    
    contentDiv.appendChild(msgBox);
    messageDiv.appendChild(contentDiv);
    chat.appendChild(messageDiv);
    chat.scrollTop = chat.scrollHeight;
  }
  
  // File upload
  document.getElementById('upload-btn').addEventListener('click', () => {
    document.getElementById('file-input').click();
  });
  
  document.getElementById('file-input').addEventListener('change', async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;
    
    for (const file of files) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const data = event.target?.result;
        if (data && typeof data === 'string') {
          const base64 = data.split(',')[1];
          vscode.postMessage({
            type: 'upload',
            payload: {
              file: {
                name: file.name,
                data: base64
              }
            }
          });
        }
      };
      reader.readAsDataURL(file);
    }
    
    e.target.value = '';
  });
  
  function loadPapersList() {
    vscode.postMessage({ type: 'loadPapers', payload: {} });
  }
  
  function removePaper(filename) {
    vscode.postMessage({ type: 'removePaper', payload: { filename } });
  }
  
  // Query handling
  document.getElementById('send').addEventListener('click', () => {
    const prompt = document.getElementById('prompt').value.trim();
    if (!prompt) return;
    addMsg(prompt, 'user');
    vscode.postMessage({ type: 'query', payload: { prompt } });
    document.getElementById('prompt').value = '';
  });

  document.getElementById('prompt').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      document.getElementById('send').click();
    }
  });

  document.getElementById('savecfg').addEventListener('click', () => {
    const mode = document.getElementById('mode').value;
    const model = document.getElementById('model').value;
    const api_key = document.getElementById('apikey')?.value || '';
    const provider = document.getElementById('provider')?.value || 'openai';
    
    vscode.postMessage({
      type: 'saveConfig',
      payload: {
        mode,
        local_model: mode === 'local' ? model : undefined,
        cloud_model: mode === 'cloud' ? model : undefined,
        cloud_provider: mode === 'cloud' ? provider : undefined,
        api_key: api_key || undefined
      }
    });
  });

  window.addEventListener('message', event => {
    const m = event.data;
    if (m.type === 'answer') {
      addMsg(m.payload, 'bot');
    }
    if (m.type === 'analysis') {
      addMsg('Analysis Result:\\n' + m.payload, 'bot');
    }
    if (m.type === 'papersList') {
      const listDiv = document.getElementById('papers-list');
      listDiv.innerHTML = '';
      const papers = m.payload.papers || [];
      if (papers.length > 0) {
        papers.forEach(paper => {
          const tag = document.createElement('div');
          tag.className = 'paper-tag';
          
          const name = document.createElement('span');
          name.className = 'paper-name';
          name.textContent = paper;
          name.title = paper;
          
          const removeBtn = document.createElement('button');
          removeBtn.className = 'paper-remove';
          removeBtn.textContent = '✕';
          removeBtn.addEventListener('click', () => removePaper(paper));
          
          tag.appendChild(name);
          tag.appendChild(removeBtn);
          listDiv.appendChild(tag);
        });
      }
    }
    if (m.type === 'uploadSuccess') {
      addMsg('✓ File uploaded: ' + m.payload.filename, 'bot');
    }
    if (m.type === 'uploadError') {
      addMsg('✗ Upload error: ' + m.payload.error, 'bot');
    }
    if (m.type === 'papersError') {
      addMsg('✗ Error loading papers: ' + m.payload.error, 'bot');
    }
  });
</script>
</body>
</html>`;
}
