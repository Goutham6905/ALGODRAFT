import * as vscode from 'vscode';
import { getWebviewContent } from './webview/webview.html';
import * as crypto from 'crypto';

const BACKEND_URL = process.env.ALGODRAFT_BACKEND || 'http://127.0.0.1:8000';

function sanitizeError(message: string): string {
  // Remove API keys and other sensitive info from error messages
  return message
    .replace(/hf_[a-zA-Z0-9]+/g, '[API_KEY_REDACTED]')
    .replace(/sk-[a-zA-Z0-9]+/g, '[API_KEY_REDACTED]')
    .replace(/sk-ant-[a-zA-Z0-9]+/g, '[API_KEY_REDACTED]')
    .replace(/api_key['\"]?\s*[:=]\s*['\"][^'\"]+['\"]/gi, 'api_key=[API_KEY_REDACTED]');
}

export function activate(context: vscode.ExtensionContext) {
  const sessionId = crypto.randomUUID();
  const provider = new AlgoDraftViewProvider(context.extensionUri, sessionId);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(AlgoDraftViewProvider.viewType, provider)
  );

  context.subscriptions.push(vscode.commands.registerCommand('algodraft.openSidebar', async () => {
    const view = await vscode.commands.executeCommand('workbench.view.extension.algodraft');
  }));

  context.subscriptions.push(vscode.commands.registerCommand('algodraft.analyzeSelection', async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage('No active editor');
      return;
    }
    const sel = editor.selection;
    if (sel.isEmpty) {
      vscode.window.showInformationMessage('Select code to analyze first');
      return;
    }
    const code = editor.document.getText(sel);
    try {
      const res = await fetch(`${BACKEND_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_code: code })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Backend returned ${res.status}`);
      }
      const data = await res.json();
      vscode.window.showInformationMessage('Analysis returned — check AlgoDraft panel');
      provider.postMessage({ type: 'analysis', payload: data.analysis });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const sanitized = sanitizeError(message);
      vscode.window.showErrorMessage('Failed to call AlgoDraft backend: ' + sanitized);
    }
  }));
}

export function deactivate() { }

class AlgoDraftViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'algodraft.sidebar';
  private _view?: vscode.WebviewView;
  private _sessionId: string;

  constructor(private readonly _extensionUri: vscode.Uri, sessionId: string) {
    this._sessionId = sessionId;
  }

  public resolveWebviewView(webviewView: vscode.WebviewView) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
    };
    webviewView.webview.html = getWebviewContent(webviewView.webview, this._extensionUri);

    webviewView.webview.onDidReceiveMessage(async (m: any) => {
      switch (m.type) {
        case 'query':
          await this.handleQuery(m.payload);
          break;
        case 'chat':
          await this.handleChat(m.payload);
          break;
        case 'generate':
          await this.handleGenerate(m.payload);
          break;
        case 'insert':
          await this.handleInsert(m.payload);
          break;
        case 'saveConfig':
          await this.handleSaveConfig(m.payload);
          break;
        case 'upload':
          await this.handleUpload(m.payload);
          break;
        case 'loadPapers':
          await this.handleLoadPapers();
          break;
        case 'removePaper':
          await this.handleRemovePaper(m.payload);
          break;
        case 'newSession':
          await this.handleNewSession();
          break;
      }
    });
  }

  async postMessage(msg: any) {
    this._view?.webview.postMessage(msg);
  }

  private async handleQuery(payload: { prompt: string }) {
    try {
      const res = await fetch(`${BACKEND_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: payload.prompt, top_k: 3, session_id: this._sessionId })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Backend returned ${res.status}`);
      }
      const data = await res.json();
      // Send structured response if available, fall back to raw answer
      if (data.sections && data.sections.length > 0) {
        this.postMessage({ type: 'structuredAnswer', payload: data });
      } else {
        this.postMessage({ type: 'answer', payload: data.answer });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const sanitized = sanitizeError(message);
      vscode.window.showErrorMessage('Query failed: ' + sanitized);
    }
  }

  private async handleChat(payload: { prompt: string }) {
    try {
      const res = await fetch(`${BACKEND_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: payload.prompt, session_id: this._sessionId })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Backend returned ${res.status}`);
      }
      const data = await res.json();
      if (data.sections && data.sections.length > 0) {
        this.postMessage({ type: 'structuredAnswer', payload: data });
      } else {
        this.postMessage({ type: 'answer', payload: data.answer });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const sanitized = sanitizeError(message);
      vscode.window.showErrorMessage('Chat failed: ' + sanitized);
    }
  }

  private async handleGenerate(payload: { prompt: string; language?: string }) {
    try {
      const res = await fetch(`${BACKEND_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: payload.prompt,
          language: payload.language || 'python',
          session_id: this._sessionId
        })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Backend returned ${res.status}`);
      }
      const data = await res.json();
      if (data.sections && data.sections.length > 0) {
        this.postMessage({ type: 'structuredAnswer', payload: data });
      } else {
        this.postMessage({ type: 'answer', payload: data.answer });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const sanitized = sanitizeError(message);
      vscode.window.showErrorMessage('Code generation failed: ' + sanitized);
    }
  }

  private async handleNewSession() {
    try {
      // Clear the old session on the backend
      await fetch(`${BACKEND_URL}/sessions/${this._sessionId}`, { method: 'DELETE' });
      // Generate a new session ID
      this._sessionId = crypto.randomUUID();
      this.postMessage({ type: 'sessionReset', payload: { session_id: this._sessionId } });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      vscode.window.showErrorMessage('Failed to reset session: ' + sanitizeError(message));
    }
  }

  private async handleInsert(payload: { text: string }) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage('No active editor for insertion');
      return;
    }
    const snippet = new vscode.SnippetString(payload.text);
    await editor.insertSnippet(snippet, editor.selection.active);
  }

  private async handleSaveConfig(cfg: any) {
    try {
      const res = await fetch(`${BACKEND_URL}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg)
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Backend returned ${res.status}`);
      }
      vscode.window.showInformationMessage('AlgoDraft config saved');
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const sanitized = sanitizeError(message);
      vscode.window.showErrorMessage('Failed to save config: ' + sanitized);
    }
  }

  private async handleUpload(payload: { file: { name: string; data: string } }) {
    try {
      const { name, data } = payload.file;
      const binaryString = atob(data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      const formData = new FormData();
      formData.append('file', new Blob([bytes]), name);

      const res = await fetch(`${BACKEND_URL}/upload`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Backend returned ${res.status}`);
      }

      this.postMessage({ type: 'uploadSuccess', payload: { filename: name } });
      await this.handleLoadPapers();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const sanitized = sanitizeError(message);
      this.postMessage({ type: 'uploadError', payload: { error: sanitized } });
    }
  }

  private async handleLoadPapers() {
    try {
      const res = await fetch(`${BACKEND_URL}/papers`);
      if (!res.ok) {
        throw new Error(`Backend returned ${res.status}`);
      }
      const data = await res.json();
      this.postMessage({ type: 'papersList', payload: data });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const sanitized = sanitizeError(message);
      this.postMessage({ type: 'papersError', payload: { error: sanitized } });
    }
  }

  private async handleRemovePaper(payload: { filename: string }) {
    try {
      const res = await fetch(`${BACKEND_URL}/remove-file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: payload.filename })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Backend returned ${res.status}`);
      }

      await this.handleLoadPapers();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const sanitized = sanitizeError(message);
      this.postMessage({ type: 'papersError', payload: { error: sanitized } });
    }
  }
}
