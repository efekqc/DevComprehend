'use strict';

/** Error shape shared by mock/http clients; mirrors the contract error envelope. */
class ApiClientError extends Error {
  constructor(code, message, retryable = false, status = 0) {
    super(message);
    this.code = code;
    this.retryable = retryable;
    this.status = status;
  }

  toJSON() {
    return { code: this.code, message: this.message, retryable: this.retryable };
  }
}

module.exports = { ApiClientError };
