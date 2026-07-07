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

## Out of scope

New AWS services.

Queue priority/fairness.

Release pipeline changes.

## Done when

Safety gates are covered by headless tests.

Pagination behavior is covered without requiring live AWS.

Roadmap items that remain are phrased as future work, not half-done chores.
