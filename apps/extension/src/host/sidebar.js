'use strict';
const crypto = require('crypto');
const vscode = require('vscode');
const { validateWebviewMessage } = require('./messages');

class SidebarProvider {
  static viewId = 'devcomprehend.sidebar';

  constructor(extensionUri, onMessage, log) {
    this.extensionUri = extensionUri;
    this.onMessage = onMessage;
    this.log = log;
    this.view = null;
    this.lastState = null;
  }

  resolveWebviewView(view) {
    this.view = view;
    const webviewRoot = vscode.Uri.joinPath(this.extensionUri, 'src', 'webview');
    view.webview.options = { enableScripts: true, localResourceRoots: [webviewRoot] };
    view.webview.html = this.html(view.webview, webviewRoot);
    view.webview.onDidReceiveMessage((raw) => {
      const message = validateWebviewMessage(raw);
      if (!message) {
        this.log(`Webview mesajı reddedildi: ${raw && typeof raw.type === 'string' ? raw.type.slice(0, 40) : 'bilinmeyen'}`);
        return;
      }
      Promise.resolve(this.onMessage(message)).catch((error) => this.log(`Mesaj işlenemedi: ${error && error.message}`));
    });
    view.onDidDispose(() => {
      this.view = null;
    });
  }

  post(state) {
    this.lastState = state;
    if (this.view) this.view.webview.postMessage({ type: 'state', state });
  }

  html(webview, webviewRoot) {
    const nonce = crypto.randomBytes(16).toString('base64');
    const script = webview.asWebviewUri(vscode.Uri.joinPath(webviewRoot, 'main.js'));
    const style = webview.asWebviewUri(vscode.Uri.joinPath(webviewRoot, 'main.css'));
    const csp = [
      "default-src 'none'",
      `style-src ${webview.cspSource}`,
      `script-src 'nonce-${nonce}'`,
      `img-src ${webview.cspSource}`,
    ].join('; ');
    return `<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="${csp}">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="${style}">
  <title>DevComprehend</title>
</head>
<body>
  <main id="app" aria-live="polite"></main>
  <script nonce="${nonce}" src="${script}"></script>
</body>
</html>`;
  }
}

module.exports = { SidebarProvider };
