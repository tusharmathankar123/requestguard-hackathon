# Hackathon contribution record

## Pre-existing work — excluded
The earlier AgentGuard prototype, including its governance engine,
refund scenarios and dashboard, was built before kickoff.
Its source code, archives and Git history are excluded from this repository.

## Post-kickoff candidates
A request-allowance module and supporting tests were written after
kickoff on October 26, according to the recorded provenance audit.
They have not yet been added to this repository.

## Current event work
- October 28: created a fresh local repository.
- October 28: added this contribution record and credential/data exclusions.

## Verification status
No runnable application or independently tested component exists here yet.
The repository is local and has not yet been published.

## Standalone safeguards milestone — October 28
- Added the audited post-kickoff allowance module.
- Replaced inherited application settings with REQUESTGUARD settings.
- Added seven independent standard-library tests covering disabled mode,
  exhaustion, restart persistence, reset prevention, concurrency,
  missing storage and corrupt storage.
- Verification: seven tests passed locally.
- No provider calls were made during this milestone.
- This component limits request counts; it does not enforce a dollar cap.

## Guarded dispatch milestone — October 28
- Added a provider wrapper that reserves a slot before dispatch.
- Added four mock-provider tests proving that disabled or exhausted
  requests never reach the provider, and failures consume their slot
  without automatic retries.
- Verification: all eleven tests passed locally.
- No external API calls were made.

## Offline demonstration milestone — October 28
- Added a repeatable demonstration using temporary allowance storage.
- Verified one allowed request and one exhausted request blocked
  before provider dispatch, with exactly one mock-provider call.
- The demonstration makes no network requests and does not modify
  the earlier AgentGuard allowance.

## Request records milestone — October 28
- Added in-memory records containing request ID, UTC timestamp,
  duration, outcome and available provider-reported token counts.
- Records exclude request text, response text and raw error details.
- Missing usage remains unknown rather than being recorded as zero.
- Verification: fourteen tests passed; offline demo produced one
  completed record and one blocked record with one provider call.
- No external API calls were made.

## Provider-failure demonstration — October 28
- Added an offline timeout scenario using temporary allowance storage.
- Verified that a failed provider attempt retains its consumed slot.
- A subsequent attempt was blocked before dispatch.
- Records showed provider_failed followed by blocked, with exactly
  one mock-provider call and zero remaining requests.
- No network requests or Meta allowance changes occurred.

## Combined offline evaluation — October 28
- Added one evaluation command covering success followed by exhaustion,
  and timeout followed by a blocked retry.
- Both scenarios passed with one mock-provider call each.
- The command emits structured JSON and exits unsuccessfully if
  either scenario fails its checks.
- No network requests or Meta allowance changes occurred.

## Evaluator verification — October 28
- Added four tests for evaluator results and exit codes.
- Verified that deliberately bypassing dispatch protection inside
  a test causes the evaluator to report failure.
- Verification: all eighteen tests passed locally.
- The bypass exists only in tests; no network requests were made.

## Meta adapter milestone
- Added a new Muse Wonder Responses API adapter during the event.
- Added bounded request/output sizes, a 30-second timeout,
  verified TLS, redirect rejection and no automatic retries.
- Preserved available provider-reported token counts.
- Added mocked transport and guarded-integration tests.
- Verification: all 27 tests passed locally.
- No live inference was performed by this repository during this milestone.

## First live Meta verification
- October 28, 23:52 UTC: standalone RequestGuard completed one
  Muse Wonder request through guarded dispatch.
- Provider-reported usage: 14 input tokens, 31 output tokens,
  45 total tokens.
- Recorded duration: 1143.24 ms.
- Persistent allowance changed from one available slot to zero.
- Response wording was not asserted; no live second attempt was made.

## Live-check safety verification
- Added five offline tests for default mode, missing storage,
  exhausted allowance, successful dispatch and provider failure.
- Verified mode restoration and exclusion of credentials and
  response text from live-check output.
- All 32 tests passed.
- Manually confirmed the exhausted live-check command stopped
  before requesting a key or making another provider call.

## Offline dashboard milestone
- Added an original self-contained evaluation dashboard with scenario
  selection, actual request records and explicit unknown mock token usage.
- Labelled the earlier user-reported live Meta result as historical evidence.
- Added four dashboard tests, including preservation of existing allowance
  storage and escaping of embedded report data.
- Closed SQLite connections after transactions to resolve resource warnings
  observed on Python 3.14.
- Verification: 36 offline tests passed; no live provider requests were made.

## Dashboard visual refinement — October 29
- Applied the selected midnight theme: navy surfaces, cyan selection, mint
  completion, amber provider failures and neutral protected blocks.
- Embedded Inter and IBM Plex Mono locally for offline rendering. These fonts
  are third-party dependencies under their supplied SIL Open Font Licenses;
  they are not claimed as original event contributions.

## Offline retry comparison — October 29
- Added a controlled three-attempt comparison using an always-timeout mock.
- Observed three unguarded dispatches versus one guarded dispatch and two
  locally blocked attempts; neither side recovers the request.
- Integrated the comparison into the dashboard, labelled as simulated and
  without claims of measured monetary savings.
- Added four tests, including bypass detection and preservation of existing
  allowance storage and environment. All 40 tests passed offline.
- No live inference or billing actions were performed.

## New Control Tower vertical slice — October 29
- Wrote new event-only policy, evidence store, proposal agent, orchestrator,
  synthetic executor and FastAPI surface; no pre-kickoff CAOF source imported.
- Added React/Tailwind Control Tower with workflows, approval queue,
  policy outcomes, persistent ledger, token records and a decision trail.
- Implemented bounded approval, hard denial and clarification, execution-time
  balance/permission rechecks, unique simulated receipts and atomic settlement.
- Added a labelled recovery checkpoint plus tests for actual process interruption,
  rollback and restart recovery without automatic provider redispatch.
- Added 25 Control Tower tests; all 65 tests passed offline. Built frontend and
  exercised approval, recovery, denial and clarification through the browser.
- Reused the already documented third-party fonts and installed normal open-source
  React, Tailwind, Vite, FastAPI and testing dependencies.
- No new paid inference calls were made. Live Meta Control Tower execution remains
  unverified; previous live evidence concerns the standalone RequestGuard check.
