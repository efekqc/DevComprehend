# DevComprehend Contracts

This directory contains the data contracts (JSON schemas) and examples used in the DevComprehend project.

## Contract Versioning Policy
We strictly follow semantic versioning (SemVer) for our JSON schemas. 
Changes are versioned by directories representing the major version (e.g., `v1/`, `v2/`).

### Breaking vs Non-Breaking Changes
- **Non-Breaking Changes (Minor/Patch):**
  - Adding optional properties.
  - Adding new event types.
  - Expanding enum definitions (if backwards compatible).
  These changes do not require a new major version directory. Just bump the `version` property in the payload and update the schema.

- **Breaking Changes (Major):**
  - Removing required or optional properties.
  - Changing the data type of an existing property.
  - Modifying required properties (adding a new requirement).
  - Removing enum values.
  These changes **must** go into a new major version directory (e.g., creating `contracts/v2/`).

## How to Add a New Event Type
1. Edit the relevant `message.schema.json`.
2. Add the new event name to the `event_type` enum.
3. If necessary, define the specific payload schema associated with this event using `$defs` or conditional evaluation (`if/then`).
4. Add an example JSON file in the corresponding `examples/` directory.

## Fixture Naming Convention
Example data files (fixtures) must be placed in the `examples/` subdirectory of their version.
The naming convention is: `<kebab-case-event-type>.json`.
For example, for `analysis.request`, the fixture should be named `analysis-request.json`.

## Validation Instructions
To validate JSON files against the schema, you can use any JSON Schema (Draft 2020-12) compatible validator.
Using Python's `jsonschema` library:
```bash
# Install the validator
pip install jsonschema

# Run validation (example command)
jsonschema -i contracts/v1/examples/analysis-request.json contracts/v1/message.schema.json
```

## FSRS Parameters
Our evaluation events output Free Spaced Repetition Scheduler (FSRS) metrics to model user learning retention:
- **Difficulty (D):** A measure of the inherent complexity of the concept for the user (scale of 1-10).
- **Stability (S):** The time, in days, after which the probability of recall drops to 90%. Higher stability means longer memory retention.
- **Retrievability (R):** The probability (0.0 to 1.0) that the user will successfully recall the concept right now.
