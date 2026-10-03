'use strict';
// Paths that must never leave the machine or add no learning value.

const SECRET_PATTERNS = [
  /(^|\/)\.env(\..*)?$/i,
  /(^|\/)\.npmrc$/i,
  /(^|\/)\.netrc$/i,
  /(^|\/)id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$/i,
  /\.(pem|key|p12|pfx|jks|keystore|crt|cer)$/i,
  /(^|\/)(secrets?|credentials?)(\.[a-z0-9]+)?$/i,
];

const GENERATED_PATTERNS = [
  /(^|\/)(node_modules|dist|build|out|coverage|vendor|__pycache__|\.next|\.venv|target)\//,
  /(^|\/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Pipfile\.lock|Cargo\.lock|composer\.lock|Gemfile\.lock|go\.sum)$/,
  /\.min\.(js|css)$/i,
  /\.(map|snap)$/i,
  /\.(generated|g)\.[a-z0-9]+$/i,
  /_pb2(_grpc)?\.py$/,
  /\.pb\.go$/,
];

const BINARY_EXTENSIONS = /\.(png|jpe?g|gif|bmp|ico|webp|pdf|zip|gz|tgz|7z|rar|jar|exe|dll|so|dylib|bin|wasm|woff2?|ttf|otf|mp3|mp4|mov|sqlite|db|vsix)$/i;

/**
 * @param {string} filePath repository-relative path with forward slashes
 * @param {boolean} isBinary git numstat reported the file as binary
 * @returns {null | 'secret' | 'binary' | 'generated'}
 */
function exclusionReason(filePath, isBinary) {
  if (SECRET_PATTERNS.some((pattern) => pattern.test(filePath))) return 'secret';
  if (isBinary || BINARY_EXTENSIONS.test(filePath)) return 'binary';
  if (GENERATED_PATTERNS.some((pattern) => pattern.test(filePath))) return 'generated';
  return null;
}

module.exports = { exclusionReason };
