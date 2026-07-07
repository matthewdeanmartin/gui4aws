# Sprint 02

Goal: tighten safety gates and pagination.

## Scope

Add global safety toggles:

- "Enable changes" gates `SAFE_WRITE` and `COST_AFFECTING` row/action buttons.
- "Enable deletes" gates `DESTRUCTIVE` row/action buttons.
- Existing review and typed-confirmation dialogs stay in place.

Harden pagination:

- verify token handling for `NextToken`, `Marker`, and `NextMarker`;
- add tests around Prev/Next state;
- document where first/last page cannot be implemented because AWS only returns forward tokens.

Remove quick-start connection guesswork:

- add an AWS Account Info popup that reads STS caller identity from the active app connection;
- show account, ARN, user ID, target, region, profile, and endpoint after connecting to local backends;
- sync the CloudFormation CDK config helper with the active connection so it no longer asks the user to re-pick region/endpoint or type the account ID.

## Out of scope

New AWS services.

Queue priority/fairness.

Release pipeline changes.

## Done when

Safety gates are covered by headless tests.

Pagination behavior is covered without requiring live AWS.

Account info and CDK config use the active `AppContext` connection, including Robotocore.

Roadmap items that remain are phrased as future work, not half-done chores.
