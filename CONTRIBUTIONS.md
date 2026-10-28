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
