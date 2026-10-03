'use strict';
const { execFile } = require('child_process');

const MAX_BUFFER = 8 * 1024 * 1024;

class GitError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

/**
 * Runs git without a shell. Repository-configured external diff/textconv
 * drivers and fsmonitor hooks are disabled so analysis never executes repo code.
 */
function runGit(cwd, args) {
  const fullArgs = ['-c', 'core.fsmonitor=false', '-c', 'core.quotepath=off', ...args];
  return new Promise((resolve, reject) => {
    execFile(
      'git',
      fullArgs,
      { cwd, maxBuffer: MAX_BUFFER, windowsHide: true, env: { ...process.env, GIT_OPTIONAL_LOCKS: '0' } },
      (error, stdout, stderr) => {
        if (!error) return resolve(stdout);
        if (error.code === 'ENOENT') return reject(new GitError('GIT_MISSING', 'Git bulunamadı. Git kurulu ve PATH içinde olmalı.'));
        if (error.code === 'ERR_CHILD_PROCESS_STDIO_MAXBUFFER') {
          return reject(new GitError('DIFF_TOO_LARGE', 'Git çıktısı işlenemeyecek kadar büyük.'));
        }
        reject(new GitError('GIT_FAILED', String(stderr || error.message).trim()));
      },
    );
  });
}

module.exports = { runGit, GitError };
