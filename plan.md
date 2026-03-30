# Frontend Follow-Up Plan

## Current State

- Dark-first shell and grouped notification cards are in place.
- Inline HTML/CSS/JS has been replaced with packaged static assets.
- The dashboard payload now includes `thread_url`, but it is still the GitHub API thread URL.

## Next Work

1. Add real browser links for notifications
   - Store and expose a GitHub web URL for each notification when available.
   - Replace the current `API Thread` action with a user-facing `Open on GitHub` action.

2. Add quick filters in the dashboard shell
   - Add client-side filters for unread state, reason, and repository.
   - Keep the dashboard selector as the coarse view and filters as fast local triage controls.

3. Reduce metadata noise with progressive disclosure
   - Move `matched_rules` and `actions_taken` into expandable details instead of showing them on every card by default.
   - Keep primary attention on title, repo, freshness, unread state, and score.

4. Improve interaction polish
   - Add loading skeletons during refresh.
   - Add stronger keyboard support and shortcuts for refresh, filter focus, and dismiss.
   - Tighten motion so refreshes and dismissals feel intentional without adding noise.

5. Strengthen status and summary surfaces
   - Add explicit unread totals and other snapshot summaries from the backend if client-side derivation becomes limiting.
   - Improve empty, loading, and error states beyond plain text messages.

6. Consider a secondary theme only after the dark theme is fully settled
   - Keep dark mode as the default and required baseline.
   - If a light theme is reintroduced later, derive it from the same token system instead of adding another ad hoc palette swap.
