'use strict';
const crypto = require('crypto');
const vscode = require('vscode');
const { SidebarProvider } = require('./host/sidebar');
const { AnalysisController } = require('./host/controller');
const { collectChanges } = require('./host/git/collect');
const { openSource } = require('./host/navigation');
const { createMockClient } = require('./host/api/mockClient');
const { createHttpClient } = require('./host/api/httpClient');

const TOKEN_KEY = 'devcomprehend.apiToken';
const REPO_IDS_KEY = 'devcomprehend.repositoryIds';

function activate(context) {
  const output = vscode.window.createOutputChannel('DevComprehend');
  const log = (line) => output.appendLine(`[${new Date().toISOString()}] ${line}`);
  const mockClient = createMockClient();
  let httpCache = null;

  function getClient() {
    const config = vscode.workspace.getConfiguration('devcomprehend');
    if (config.get('apiMode') !== 'http') return { client: mockClient, mode: 'mock', target: 'mock' };
    const baseUrl = config.get('apiBaseUrl');
    if (!httpCache || httpCache.baseUrl !== baseUrl) {
      const getToken = () => context.secrets.get(TOKEN_KEY);
      try {
        httpCache = { baseUrl, client: createHttpClient({ baseUrl, getToken }) };
      } catch (error) {
        const failing = () => Promise.reject(error);
        httpCache = { baseUrl, client: { mode: 'http', origin: 'geçersiz adres', createAnalysis: failing, getAnalysis: failing, submitAnswer: failing } };
      }
    }
    return { client: httpCache.client, mode: 'http', target: httpCache.client.origin };
  }

  /** Opaque per-repository ID; the local path never leaves the machine. */
  function repositoryIdFor(root) {
    const ids = context.globalState.get(REPO_IDS_KEY, {});
    const key = crypto.createHash('sha256').update(root).digest('hex');
    if (!ids[key]) {
      ids[key] = `ws-${crypto.randomUUID()}`;
      context.globalState.update(REPO_IDS_KEY, ids);
    }
    return ids[key];
  }

  async function pickTarget() {
    const folders = (vscode.workspace.workspaceFolders || []).filter((folder) => folder.uri.scheme === 'file');
    if (folders.length === 0) {
      throw Object.assign(new Error('Önce bir Git deposu içeren klasör açın.'), { code: 'NO_WORKSPACE' });
    }
    let folder = folders[0];
    if (folders.length > 1) {
      const picked = await vscode.window.showQuickPick(
        folders.map((item) => ({ label: item.name, description: item.uri.fsPath, folder: item })),
        { title: 'DevComprehend: Hangi workspace klasörü?', placeHolder: 'Analiz edilecek klasörü seçin' },
      );
      if (!picked) return null;
      folder = picked.folder;
    }
    const scope = await vscode.window.showQuickPick(
      [
        { label: 'Unstaged', description: 'Çalışma ağacındaki, henüz stage edilmemiş değişiklikler', scope: 'unstaged' },
        { label: 'Staged', description: 'git add ile stage edilmiş değişiklikler', scope: 'staged' },
      ],
      { title: 'DevComprehend: Kapsam', placeHolder: 'Hangi değişiklikler önizlensin? (Onaydan önce hiçbir şey gönderilmez)' },
    );
    if (!scope) return null;
    return { cwd: folder.uri.fsPath, folderName: folder.name, scope: scope.scope };
  }

  let provider;
  const controller = new AnalysisController({
    getClient,
    pickTarget,
    collect: (cwd, scope) => collectChanges({ cwd, scope }),
    repositoryIdFor,
    openSource,
    post: (state) => provider.post(state),
    notify: (level, message) => {
      if (level === 'error') vscode.window.showErrorMessage(message);
      else if (level === 'warning') vscode.window.showWarningMessage(message);
      else vscode.window.showInformationMessage(message);
    },
    sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
    newId: () => crypto.randomUUID(),
  });
  provider = new SidebarProvider(context.extensionUri, (message) => controller.handleMessage(message), log);

  let staleTimer = null;
  context.subscriptions.push(
    output,
    vscode.window.registerWebviewViewProvider(SidebarProvider.viewId, provider, { webviewOptions: { retainContextWhenHidden: true } }),
    vscode.commands.registerCommand('devcomprehend.analyzeChanges', async () => {
      await vscode.commands.executeCommand(`${SidebarProvider.viewId}.focus`);
      await controller.analyze();
    }),
    vscode.commands.registerCommand('devcomprehend.showMockDemo', async () => {
      if (getClient().mode !== 'mock') {
        vscode.window.showInformationMessage('Mock demo yalnız devcomprehend.apiMode = "mock" iken çalışır.');
        return;
      }
      await vscode.commands.executeCommand(`${SidebarProvider.viewId}.focus`);
      await controller.showDemo();
    }),
    vscode.commands.registerCommand('devcomprehend.setApiToken', async () => {
      const token = await vscode.window.showInputBox({ title: 'DevComprehend API token', password: true, ignoreFocusOut: true, prompt: 'Token VS Code SecretStorage içinde saklanır.' });
      if (token && token.trim()) {
        await context.secrets.store(TOKEN_KEY, token.trim());
        vscode.window.showInformationMessage('API token kaydedildi.');
      }
    }),
    vscode.commands.registerCommand('devcomprehend.clearApiToken', async () => {
      await context.secrets.delete(TOKEN_KEY);
      vscode.window.showInformationMessage('API token silindi.');
    }),
    vscode.workspace.onDidSaveTextDocument(() => {
      clearTimeout(staleTimer);
      staleTimer = setTimeout(() => controller.refreshStale(), 800);
    }),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration('devcomprehend')) provider.post(controller.snapshotState());
    }),
    { dispose: () => clearTimeout(staleTimer) },
  );
  log(`Etkin. Mod: ${getClient().mode}`);
}

function deactivate() {}

module.exports = { activate, deactivate };
