# RequestGuard

A standalone request-allowance component and offline evaluator for
AI provider calls.

It reserves a persistent request slot before provider dispatch.
Exhausted or disabled requests are blocked. Failed provider attempts
retain their slot, and the wrapper performs no automatic retries.

## Hackathon provenance

An earlier AgentGuard prototype existed before kickoff. Its application
code, refund scenarios, dashboard, archives and Git history are excluded
from this repository.

This repository contains an audited post-kickoff allowance module,
its standalone adaptations, guarded dispatch, request records,
offline demonstrations and evaluation tests developed during the event.

See CONTRIBUTIONS.md for the contribution record.

## Requirements

Python 3.11 or later. The current offline implementation uses only
Python's standard library. No API key or external service is required.

Run commands from the repository root.

## Run the tests

    python3 -m unittest discover -s tests -v

Current verification: 18 tests passed locally.

## Run the combined evaluation

    python3 -m requestguard.evaluate

The JSON report covers:
- A successful mock request followed by a blocked attempt.
- A timed-out mock request followed by a blocked attempt.

Each scenario permits exactly one mock-provider call.
Exit code 0 means both scenarios passed; 1 means an evaluation failed.

Tests also deliberately bypass protection and verify that the
evaluator detects the broken behaviour.

## Individual demonstrations

    python3 -m requestguard.demo
    python3 -m requestguard.failure_demo

Demonstrations use temporary data folders and make no network requests.

## Request records

In-memory records contain a local request ID, UTC timestamp,
duration, outcome and available provider-reported token counts.

They exclude request text, response text, credentials and raw errors.
Missing token usage is recorded as unknown, not zero.
Records are not a persistent or tamper-evident audit trail.

## Safety boundaries

- This is a request-count limit, not a dollar spending cap.
- Protection applies only to calls routed through guarded_call.
- Direct provider calls can bypass this wrapper.
- Deleting or replacing storage, or choosing a new data directory,
  can defeat allowance persistence.
- REQUESTGUARD_LIVE_ENABLED must equal YES to permit guarded dispatch.
- REQUESTGUARD_DATA_DIR selects the persistent allowance location.
- Failed attempts consume a slot even when provider usage is unknown.
- This repository does not yet integrate Meta or Baseten.
- Earlier live Meta testing used the excluded AgentGuard application;
  it does not establish live integration for this project.

## Credentials

Never commit API keys, environment files or local allowance databases.
The offline demonstrations require no credentials.
