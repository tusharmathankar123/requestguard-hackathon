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

Current verification: 40 tests passed locally.

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
- The Meta adapter has mocked HTTP coverage and one successful live Muse Wonder verification.
- Baseten is not integrated.
- Earlier live Meta testing used the excluded AgentGuard application;
  it does not establish live integration for this project.

## Credentials

Never commit API keys, environment files or local allowance databases.
The offline demonstrations require no credentials.

## Live verification evidence

On October 28 at 23:52 UTC, this standalone project completed one
Muse Wonder request through guarded dispatch.

- Provider-reported usage: 14 input, 31 output, 45 total tokens.
- Recorded duration: 1143.24 ms.
- The persistent one-request allowance was exhausted.
- A subsequent command stopped before prompting for a key or
  dispatching another provider request.

This verifies one live request and local blocking after exhaustion.
It does not establish a dollar spending cap or broad model accuracy.
The response wording was not asserted.

The live-check command requires explicit --run activation and an
existing unused one-slot allowance. Do not delete or reset an
exhausted ledger to repeat the check.

## Offline dashboard

    python3 -m requestguard.dashboard

Open `local-data/dashboard.html` in a browser. The generated page is a
self-contained snapshot of two fresh mock evaluations; scenario buttons
inspect those results without making provider calls. Regenerate it to refresh.
No server, API key or live allowance is needed. Existing live storage is
unchanged. The separately labelled Meta figures are historical user-reported
evidence from the earlier live check, not a live connection.

The generated HTML stays in ignored local-data/. The source template and
builder are included in the repository.

Dashboard typography uses bundled Inter and IBM Plex Mono, embedded in the
generated HTML. See requestguard/fonts/ for third-party font licenses.

## Controlled retry comparison

    python3 -m requestguard.compare

Both sides attempt three calls against the same always-timeout mock. An
unguarded loop dispatches three times; a one-slot guarded loop dispatches
once and blocks twice. The dashboard includes these observed counts. Neither
side recovers the failed request. This is a controlled offline simulation,
not a claim of actual monetary savings or a recommendation to retry blindly.
Existing live allowance storage is unchanged.
