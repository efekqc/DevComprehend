# ADR-0002: Contract-First Design and Local Development Isolation

## Status
Accepted

## Date
2026-10-03

## Context

DevComprehend is a multi-component system consisting of a VS Code/Cursor extension (frontend), a backend API, and an AI engine. The team is distributed across four engineers with distinct responsibilities:

- **Extension UI** (Ahmet): VS Code/Cursor webview
- **Backend API** (Derviş): REST API and orchestration
- **AI Engine** (Murathan): LLM integration and prompt engineering
- **Contracts & Infrastructure** (Efe): Data schemas, DB, CI/CD, QA

Key challenges:
1. Components must integrate without blocking each other during development.
2. The system handles sensitive Git diff data that must not leak.
3. LLM API calls are expensive and non-deterministic — CI must be fully deterministic.
4. The spaced repetition feature needs a modern, research-backed algorithm.

## Decision

We adopt the following architectural decisions:

### 1. Contract-First Development
All inter-component communication is defined by JSON Schema (Draft 2020-12) contracts in `contracts/v1/`. Each component team develops against these schemas using synthetic fixtures, enabling fully parallel development.

**Versioning:** Schemas follow semantic versioning with directory-based major versions (`v1/`, `v2/`). Non-breaking additions (new optional fields) increment the patch version. Breaking changes require a new major version directory.

### 2. Zero-Client Secret
No LLM API keys, tokens, or secrets are ever stored in the VS Code extension. All sensitive credentials are managed server-side via a Key Management Service (KMS). The extension only holds a short-lived session token for API authentication.

### 3. Data Privacy — Local Git Diff Only
The extension transmits ONLY user-approved Git diff data (staged/unstaged changes). Before transmission:
- Users must explicitly consent via UI approval.
- A regex-based masking pipeline replaces detected secrets (API keys, passwords, tokens) with `[REDACTED_SECRET]`.
- Full file contents are never sent; only diff hunks within user-selected scope.

### 4. FSRS over SM-2 for Spaced Repetition
We chose the **Free Spaced Repetition Scheduler (FSRS)** over the legacy SuperMemo-2 (SM-2) algorithm because:
- FSRS uses three parameters (Difficulty D, Stability S, Retrievability R) providing more granular control.
- FSRS is backed by recent research (2022-2024) with empirically validated improvements in retention prediction.
- FSRS supports four rating levels (Again=1, Hard=2, Good=3, Easy=4) matching our evaluation rubric output.
- SM-2's ease factor has known issues with "ease hell" — FSRS's stability model avoids this.

### 5. Deterministic CI with Fake LLM Provider
CI pipelines never make real LLM API calls. A fake provider (`tests/mock_adapters/fake_llm_provider.py`) returns deterministic responses based on input diff content hashes, ensuring:
- 100% reproducible test results
- Zero API cost in CI
- No API key requirements in CI environment

### 6. Local Development Isolation
Each developer runs services locally via Docker Compose with:
- Isolated PostgreSQL 16 instance (non-standard port 5433 to avoid conflicts)
- Redis for rate limiting simulation
- Auto-applied database migrations via `docker-entrypoint-initdb.d`

## Consequences

### Positive
- Teams can develop and test independently using contract fixtures.
- CI is fast, cheap, and deterministic.
- No risk of secret leakage from the extension.
- FSRS provides better learning outcome predictions than SM-2.
- Local environments are reproducible and isolated.

### Negative
- Contract changes require coordination across teams.
- Fake LLM responses may not catch all edge cases in real LLM behavior.
- FSRS parameter tuning requires empirical data from pilot users.

### Risks
- Contract drift: mitigated by automated schema validation in CI.
- Fake provider divergence: mitigated by periodic integration tests against staging.

## References
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-core)
- [FSRS Algorithm](https://github.com/open-spaced-repetition/fsrs4anki)
- [ADR Format — Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
