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

Python 3.11 or later. The RequestGuard evaluator uses only Python's standard library.
The new Control Tower additionally uses FastAPI and a React/Tailwind frontend.
No API key is required for offline testing or fixture workflows.

Run commands from the repository root.

## Run the tests

    python3 -m unittest discover -s tests -v

Current verification: 65 tests passed locally, including the new Control Tower tests.

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

## New AgentGuard Control Tower

The event-built interactive application is separate from the earlier static
RequestGuard evaluation snapshot. It implements the architecture as:

- React + Tailwind web Control Tower, using bundled fonts.
- FastAPI API and newly authored orchestration and agent contracts.
- Meta proposal agent calling the existing event-built RequestGuard wrapper.
- Independent default-deny policy followed by a synthetic tool executor.
- SQLite workflow state, refundable balances, unique receipts and hash-chain events.

No earlier CAOF/Control Tower application source was copied into this implementation.
The generic multi-agent CAOF framework is not included; this first vertical slice
implements one refund-agent contract and one simulated refund tool.

### Install and start offline

Requires Python 3.11+ and Node 22.12+ (Node 24 recommended), with npm.
Dependency installation requires internet; the built offline app does not.

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements-dev.txt
    cd frontend
    npm ci
    npm run build
    cd ..
    python -m control_tower --port 8010

Open http://127.0.0.1:8010. The API serves the built frontend from the same
origin. Single worker and loopback binding are intentional. Stop with Ctrl-C.
Once dependencies and frontend are built, only the final Python command is
needed to start it again.

### Scenario rehearsal

Use each scenario button and Submit to agent:

| Request | Expected result |
|---|---|
| €125 / DEMO-125 | Simulated refund succeeds automatically |
| €300 / DEMO-300 | Awaits approval; reviewer.demo can approve and execute |
| €750 / DEMO-750 | Policy denial; no approval override or simulated debit |
| Ambiguous complaint | Clarification decision; no tool execution |

Offline interpretation recognises only those four exact examples. The current
policy's conservative supported grammar is an explicit refund, EUR amount and
transaction reference; unsupported language requires clarification even in Meta
mode. This is not broad semantic understanding or complete injection protection.

Unlike the earlier prototype, synthetic balances are consumed and persist.
Repeating a completed transaction will be denied when no refundable balance
remains. There is no dashboard reset button. For a separate offline rehearsal,
choose a new database explicitly with --data local-data/another-rehearsal.sqlite.
This changes only the simulated business ledger, never the RequestGuard allowance.

### Restart and recovery

On a fresh DEMO-125 request, select Pause before execution for a recovery
rehearsal, then submit. This deliberately records a simulated checkpoint before
any debit. Stop/restart with the SAME --data path, select the persisted workflow
and choose Recover safely. Recovery checks persisted inputs, policy, approval,
remaining balance and existing receipts. It does not recall Meta.

Unexpected interruption before/during simulated settlement is covered by tests:
startup marks unfinished work interrupted, and the SQLite transaction rolls back
partial debit/receipt writes. A pending human approval also survives restart.
Interpretation interrupted before a proposal was persisted is not automatically
retried and requires a new request, subject to the unchanged provider allowance.
Recovery guarantees here apply to the atomic SQLite simulation, not an external
payment provider with uncertain network outcomes.

### Meta mode remains opt-in

The new Control Tower is tested with mocked Meta responses, not yet live Meta
inference. The earlier standalone RequestGuard live result does not verify this
new workflow. Do not replenish allowances or run paid tests without reviewing
remaining credits first.

Starting with --live requires a server-side MODEL_API_KEY,
REQUESTGUARD_LIVE_ENABLED=YES and an existing RequestGuard allowance. Every
workflow interpretation uses guarded_call; approval/recovery uses the persisted
proposal and does not make a second model call. There is no browser key field,
provider fallback, allowance top-up or live-mode toggle in the UI. A provider
failure never silently falls back to fixture interpretation.

### Limits and evidence

- Reviewer labels are audit labels, not authenticated identities or separation of duties.
- Default contract permits only refund:simulate and simulate_refund.
- The approval gate is server enforced and cannot override the €500 cap.
- Policy and balance are rechecked at execution, including after approval/recovery.
- Model extra fields, including approval flags, fail schema validation.
- Workflows and event evidence persist; chains are not externally signed/anchored.
- The workflow evidence intentionally includes synthetic customer text; do not use
  real customer information. Credentials and raw provider errors are not recorded.
- Polling refreshes the browser every two seconds. This is not an SSE stream.
- Read APIs are local demo interfaces. Mutation APIs require a per-process local
  session token and reject cross-origin requests. This is not enterprise authentication.

Run all tests after installing the development dependencies:

    python -m unittest discover -s tests -v
    python -m pytest tests/test_control_tower.py -q

Control Tower verification includes four API outcomes, malicious proposals,
permissions, €250/€500 boundaries, repeated and concurrent approvals, balance
rechecks, event/input tampering, checkpoint and actual crash recovery, atomic
rollback, mocked Meta token accounting and HTTP boundary checks.
