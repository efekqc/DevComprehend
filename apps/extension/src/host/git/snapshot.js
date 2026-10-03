'use strict';
const crypto = require('crypto');

/** snapshot_id = SHA-256 of the exact bounded diff that is sent (contracts/README.md). */
function snapshotId(diff) {
  return crypto.createHash('sha256').update(diff, 'utf8').digest('hex');
}

module.exports = { snapshotId };
