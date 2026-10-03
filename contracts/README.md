# DevComprehend Contracts (v1)

This directory contains the data contracts (JSON schemas) and examples used in the DevComprehend project.

---

## 1. Contract Versioning Policy
We strictly follow semantic versioning (SemVer) for our JSON schemas. 
Changes are versioned by directories representing the major version (e.g., `v1/`, `v2/`).

### Breaking vs Non-Breaking Changes
- **Non-Breaking Changes (Minor/Patch):**
  - Adding optional properties.
  - Adding new event types (e.g., `error.response`).
  - Expanding enum definitions (if backwards compatible).
  These changes do not require a new major version directory. Just bump the `version` property in the payload and update the schema.

- **Breaking Changes (Major):**
  - Removing required or optional properties.
  - Changing the data type of an existing property.
  - Modifying required properties (adding a new requirement).
  - Removing enum values.
  These changes **must** go into a new major version directory (e.g., creating `contracts/v2/`).

---

## 2. Event Types & Flow

| Event Type | Direction | Description | Typical HTTP Code |
|------------|-----------|-------------|:-----------------:|
| `analysis.request` | Extension → API | User submits approved git diff | `POST /v1/analyses` |
| `analysis.queued` | API → Extension | Analysis accepted for processing | `202 Accepted` / `200 OK` |
| `analysis.ready` | API → Extension | AI questions generated & ready | `200 OK` |
| `answer.request` | Extension → API | User submits free-text answer | `POST /v1/answers` |
| `evaluation.result` | API → Extension | Evaluation & FSRS repetition schedule | `200 OK` |
| `error.response` | API → Extension | Standardized error payload | `400 / 409 / 413 / 429 / 502` |

---

## 3. HTTP 200 OK vs 202 Accepted Policy

API and Client (VS Code / Cursor extension) support both synchronous and asynchronous workflows:

| HTTP Status | State | Usage Context | Expected Payload |
|:-----------:|:-----:|---------------|------------------|
| **`202 Accepted`** *(Default)* | `QUEUED` | **Asynchronous Queue:** Real LLM pipeline. The backend accepts the request, puts it into a queue, and returns an `analysis_id`, `estimated_seconds` and `retry_after_ms` for client polling. | `{ "analysis_id": "...", "status": "QUEUED", "http_status": 202, "retry_after_ms": 3000 }` |
| **`200 OK`** | `READY` | **Synchronous / Mock Mode:** Instant response used in local mock adapter, testing, or cached analyses where questions are immediately available without polling. | `{ "analysis_id": "...", "status": "READY", "http_status": 200, "questions": [...] }` |

> **Client Recommendation:** Extension clients must check the HTTP status code and `status` field:
> - If `status == "QUEUED"` (HTTP 202): Start polling `GET /v1/analyses/{analysis_id}` using `retry_after_ms`.
> - If `status == "READY"` (HTTP 200): Render comprehension questions immediately in the webview.

---

## 4. Standard Error Codes Mapping

When an error occurs, the API returns an `error.response` event with a structured payload:

| `error_code` | `http_status` | Trigger Condition | Recommended User Action |
|--------------|:-------------:|-------------------|--------------------------|
| `EMPTY_DIFF` | `400` | Diff contains no changes or zero files | Prompt user to stage or modify files before analyzing |
| `PAYLOAD_TOO_LARGE` | `413` | Diff exceeds 400 lines or includes lock files (`package-lock.json`, `pnpm-lock.yaml`, etc.) | Advise user to commit atomic changes or exclude lock files |
| `STALE_SNAPSHOT` | `409` | Client's `snapshot_id` does not match server's active file hash | Refresh git status and request new analysis |
| `RATE_LIMIT_EXCEEDED` | `429` | Daily token quota (50,000) or analysis quota (10) exceeded | Display quota reset time; offer Pro upgrade |
| `INVALID_MODEL_OUTPUT` | `502` | LLM generated malformed JSON or unparseable output | Prompt user to retry; fallback to situational defaults |

### Error Payload Schema
```json
{
  "version": "v1.0.0",
  "event_type": "error.response",
  "timestamp": "2026-10-03T05:00:00Z",
  "payload": {
    "error_code": "EMPTY_DIFF",
    "http_status": 400,
    "message": "Gönderilen diff herhangi bir değişiklik veya dosya içermiyor.",
    "details": {
      "reason": "empty_changeset"
    }
  }
}
```

---

## 5. Fixture Naming Convention
Example data files (fixtures) must be placed in `contracts/v1/examples/`:
- `analysis-request.json`
- `analysis-queued.json`
- `analysis-ready.json`
- `answer-request.json`
- `evaluation-result.json`
- `error-response.json`

---

## 6. Validation Instructions
To validate JSON fixtures against the schema:
```bash
python scripts/check_contract_examples.py
python -m pytest tests/contract/ -v
```

---

## 7. FSRS Parameters
Our evaluation events output Free Spaced Repetition Scheduler (FSRS) metrics to model user learning retention:
- **Difficulty (D):** A measure of the inherent complexity of the concept for the user (scale of 1-10).
- **Stability (S):** The time, in days, after which the probability of recall drops to 90%. Higher stability means longer memory retention.
- **Retrievability (R):** The probability (0.0 to 1.0) that the user will successfully recall the concept right now.
- **Rating:** 1 = Again, 2 = Hard, 3 = Good, 4 = Easy.
