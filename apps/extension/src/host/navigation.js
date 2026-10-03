'use strict';
const path = require('path');
const vscode = require('vscode');

/** Opens a repository-relative source range; rejects paths that escape the repository. */
async function openSource(root, source) {
  const relative = source.path;
  if (path.isAbsolute(relative) || relative.split(/[\\/]/).includes('..')) {
    throw new Error('Kaynak yolu depo dışını gösteriyor; açılmadı.');
  }
  const absolute = path.resolve(root, relative);
  if (!absolute.startsWith(root + path.sep)) {
    throw new Error('Kaynak yolu depo dışını gösteriyor; açılmadı.');
  }
  const uri = vscode.Uri.file(absolute);
  try {
    await vscode.workspace.fs.stat(uri);
  } catch {
    throw new Error(`${relative} artık mevcut değil.`);
  }
  const document = await vscode.workspace.openTextDocument(uri);
  const last = Math.max(document.lineCount - 1, 0);
  const start = Math.min(source.start_line - 1, last);
  const end = Math.min(Math.max(source.end_line - 1, start), last);
  const range = new vscode.Range(start, 0, end, document.lineAt(end).text.length);
  await vscode.window.showTextDocument(document, { selection: range, preview: true });
}

module.exports = { openSource };
