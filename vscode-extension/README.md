# AlgoDraft VS Code Extension

The IDE-native frontend for AlgoDraft research copilot. Provides a Webview sidebar for querying papers, analyzing selected code, and configuring LLM backends (local Ollama or cloud APIs).

## Features

- **Chat Interface**: Query your ingested papers directly from VS Code.
- **Code Analysis**: Select code and get critique against research context via right-click context menu.
- **Dynamic LLM Routing**: Switch between local Ollama models and cloud APIs (OpenAI, etc.) via Webview UI.
- **Code Injection**: Generated code can be inserted directly into your active editor at the cursor.

## Installation (Development)

1. `npm install` — install dependencies.
2. `npm run build` — compile TypeScript to JavaScript.
3. Open this folder in VS Code and press **F5** to launch the Extension Development Host.

## Usage

1. **Open Sidebar**: Look for the **AlgoDraft** icon in the Activity Bar (left sidebar) or run command `AlgoDraft: Open Sidebar`.
2. **Query Papers**: Type a prompt and click **Send**, or press Shift+Enter. Responses appear in the chat box.
3. **Analyze Selection**: Select code in any editor, right-click, and choose **AlgoDraft: Analyze Selected Code**. Results appear in the sidebar.
4. **Configure Backend**:
   - Set **Mode** to `Local` (Ollama) or `Cloud` (API).
   - Enter the **Model name** (e.g., `mistral` for local, `gpt-4o` for OpenAI).
   - Provide your **API Key** if using cloud mode.
   - Click **Save Config** to persist settings.

## Configuration

The extension communicates with the backend at `http://127.0.0.1:8000` (default). To use a different URL, set the environment variable:

```bash
export ALGODRAFT_BACKEND=http://your-server:8000
```

before launching the extension.

## Architecture

- **extension.ts**: Main extension entry point. Registers webview view provider and commands.
- **webview/webview.html.ts**: Exports the HTML/CSS/JS for the Webview sidebar as a string template.

### Command Palette Commands

- `AlgoDraft: Open Sidebar` — Reveal the AlgoDraft view in the sidebar.
- `AlgoDraft: Analyze Selected Code` — Send current selection to backend for analysis.

### Editor Context Menu

- Right-click on selected code → **AlgoDraft: Analyze Selected Code**.

## Development

- **Watch mode**: `npm run watch` — auto-recompile on source changes.
- **Build**: `npm run build` — one-time TypeScript compilation.
- **Debugging**: Set breakpoints in TypeScript and step through in VS Code's Debug Console.

## API Communication

The extension sends messages to the backend:

- **`POST /query`**: Send user prompt, receive answer.
- **`POST /analyze`**: Send selected code, receive analysis.
- **`POST /config`**: Update backend configuration.
- **`GET /config`**: Fetch current server configuration.

See the main [README.md](../README.md) for endpoint details.

## Troubleshooting

- **Sidebar not appearing**: Run `F1 → AlgoDraft: Open Sidebar` or check the Activity Bar icon.
- **Backend connection fails**: Ensure the FastAPI server is running at `http://127.0.0.1:8000`.
- **Messages timeout**: Check network connectivity and backend logs.
- **TypeScript errors**: Run `npm run build` to see compile errors and fix them.

---

**Part of AlgoDraft AI** — offline-first research copilot MVP.
