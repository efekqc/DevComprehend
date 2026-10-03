'use strict';
const fs = require('fs/promises');
const path = require('path');
const { runGit: defaultRunGit, GitError } = require('./gitRunner');
const { exclusionReason } = require('./filter');
const { snapshotId } = require('./snapshot');

const DEFAULT_LIMITS = Object.freeze({
  maxFiles: 40,
  maxDiffBytes: 40_000,
  maxContextFileChars: 6_000,
  maxContextTotalChars: 12_000,
  maxReadBytes: 1_000_000,
});

const SHA1 = /^[a-f0-9]{40}$/;

function diffArgs(scope) {
  if (scope !== 'staged' && scope !== 'unstaged') throw new GitError('INVALID_SCOPE', 'Geçersiz kapsam.');
  const args = ['diff', '--no-color', '--no-ext-diff', '--no-textconv', '--no-renames'];
  if (scope === 'staged') args.push('--cached');
  return args;
}

function parseNumstat(output) {
  const entries = [];
  for (const record of output.split('\0')) {
    if (!record) continue;
    const match = /^(\d+|-)\t(\d+|-)\t(.+)$/s.exec(record);
    if (!match) continue;
    const isBinary = match[1] === '-' && match[2] === '-';
    entries.push({
      path: match[3],
      additions: isBinary ? 0 : Number(match[1]),
      deletions: isBinary ? 0 : Number(match[2]),
      isBinary,
    });
  }
  return entries;
}

async function readWorkingFile(root, relPath, maxBytes) {
  const resolved = path.resolve(root, relPath);
  if (!resolved.startsWith(root + path.sep)) return null;
  try {
    const stat = await fs.lstat(resolved);
    if (!stat.isFile() || stat.size > maxBytes) return null;
    return await fs.readFile(resolved, 'utf8');
  } catch {
    return null;
  }
}

function jsonBytes(text) {
  return Buffer.byteLength(JSON.stringify(text), 'utf8');
}

/**
 * Collects a bounded, filtered diff for one scope. Nothing is sent here;
 * the result is shown to the user for confirmation first.
 */
async function collectChanges({ cwd, scope, runGit = defaultRunGit, readFile, limits = DEFAULT_LIMITS }) {
  const base = diffArgs(scope);

  let root;
  try {
    root = (await runGit(cwd, ['rev-parse', '--show-toplevel'])).trim();
  } catch (error) {
    if (error.code === 'GIT_MISSING') throw error;
    throw new GitError('NOT_A_REPO', 'Seçilen klasör bir Git deposu değil.');
  }

  let baseCommitSha;
  try {
    baseCommitSha = (await runGit(root, ['rev-parse', '--verify', 'HEAD'])).trim();
  } catch {
    throw new GitError('NO_COMMITS', 'Depoda henüz commit yok. Base SHA için en az bir commit gerekli.');
  }
  if (!SHA1.test(baseCommitSha)) {
    throw new GitError('UNSUPPORTED_REPO', 'Yalnız SHA-1 Git depoları destekleniyor.');
  }

  const entries = parseNumstat(await runGit(root, [...base, '--numstat', '-z'])).sort((a, b) => a.path.localeCompare(b.path));
  const excluded = [];
  const omitted = [];
  const files = [];
  const chunks = [];
  let diffBytes = 0;

  for (const entry of entries) {
    const reason = exclusionReason(entry.path, entry.isBinary);
    if (reason) {
      excluded.push({ path: entry.path, reason });
      continue;
    }
    if (files.length >= limits.maxFiles) {
      omitted.push({ path: entry.path, reason: 'file_limit' });
      continue;
    }
    const fileDiff = await runGit(root, [...base, '--', `:(literal)${entry.path}`]);
    if (!fileDiff) continue;
    const bytes = jsonBytes(fileDiff);
    if (diffBytes + bytes > limits.maxDiffBytes) {
      omitted.push({ path: entry.path, reason: 'size' });
      continue;
    }
    diffBytes += bytes;
    chunks.push(fileDiff);
    files.push({ path: entry.path, additions: entry.additions, deletions: entry.deletions });
  }

  const read = readFile || ((relPath) => readWorkingFile(root, relPath, limits.maxReadBytes));
  const context = [];
  let contextChars = 0;
  for (const file of files) {
    const remaining = limits.maxContextTotalChars - contextChars;
    if (remaining <= 0) break;
    let content = null;
    if (scope === 'staged') {
      try {
        content = await runGit(root, ['show', `:${file.path}`]);
      } catch {
        content = null; // deleted in index
      }
    } else {
      content = await read(file.path);
    }
    if (content === null || content.includes('\0')) continue;
    const limit = Math.min(limits.maxContextFileChars, remaining);
    const truncated = content.length > limit;
    const sliced = truncated ? content.slice(0, limit) : content;
    contextChars += sliced.length;
    context.push({ path: file.path, content: sliced, truncated });
  }

  let untrackedCount = 0;
  if (scope === 'unstaged') {
    const untracked = await runGit(root, ['ls-files', '--others', '--exclude-standard', '-z']);
    untrackedCount = untracked.split('\0').filter(Boolean).length;
  }

  const diff = chunks.join('');
  return {
    root,
    scope,
    baseCommitSha,
    snapshotId: diff ? snapshotId(diff) : null,
    diff,
    diffBytes,
    files,
    excluded,
    omitted,
    context,
    untrackedCount,
  };
}

module.exports = { collectChanges, parseNumstat, DEFAULT_LIMITS };
