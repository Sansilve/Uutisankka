#!/bin/bash
# UutisAnkka – GitHub Backlog Setup
# Vaatii: gh CLI kirjautuneena (gh auth status)
# Ajo: bash setup-github.sh

set -e
REPO="Sansilve/Uutisankka"

echo "=== Luodaan labelit ==="
gh label create "area:mobile"   --color "0075ca" --repo $REPO --force
gh label create "area:backend"  --color "e4e669" --repo $REPO --force
gh label create "area:web"      --color "cfd3d7" --repo $REPO --force
gh label create "type:feature"  --color "a2eeef" --repo $REPO --force
gh label create "type:refactor" --color "d4edda" --repo $REPO --force
gh label create "type:test"     --color "f9d0c4" --repo $REPO --force
gh label create "type:docs"     --color "fef2c0" --repo $REPO --force
gh label create "priority:P0"   --color "b60205" --repo $REPO --force
gh label create "priority:P1"   --color "e99695" --repo $REPO --force
gh label create "sprint:W1"     --color "bfd4f2" --repo $REPO --force
gh label create "sprint:W2"     --color "bfd4f2" --repo $REPO --force
gh label create "sprint:W3"     --color "bfd4f2" --repo $REPO --force
gh label create "sprint:W4"     --color "bfd4f2" --repo $REPO --force

echo "=== Luodaan milestonet ==="
gh api repos/$REPO/milestones -f title="Week 1 – Core Flow"             -f description="Lock user flow, refactor navigation, env config"              -f due_on="2026-05-09T23:59:59Z" || true
gh api repos/$REPO/milestones -f title="Week 2 – UX Stability"          -f description="Loading/error states, retry, onboarding polish"               -f due_on="2026-05-16T23:59:59Z" || true
gh api repos/$REPO/milestones -f title="Week 3 – Backend Stabilization" -f description="Logging, error format, route modularization"                   -f due_on="2026-05-23T23:59:59Z" || true
gh api repos/$REPO/milestones -f title="Week 4 – Tests and Quality"     -f description="Smoke tests, component tests, scoring calibration, demo run"   -f due_on="2026-05-30T23:59:59Z" || true

# Hae milestone-IDt
M1=$(gh api repos/$REPO/milestones | jq '.[] | select(.title | test("Week 1")) | .number')
M2=$(gh api repos/$REPO/milestones | jq '.[] | select(.title | test("Week 2")) | .number')
M3=$(gh api repos/$REPO/milestones | jq '.[] | select(.title | test("Week 3")) | .number')
M4=$(gh api repos/$REPO/milestones | jq '.[] | select(.title | test("Week 4")) | .number')

echo "Milestone IDt: W1=$M1 W2=$M2 W3=$M3 W4=$M4"

echo "=== Luodaan issuet (W1) ==="

gh issue create --repo $REPO \
  --title "Define official mobile MVP user flow" \
  --label "area:mobile,type:docs,priority:P0,sprint:W1" \
  --milestone $M1 \
  --body "## Objective
Lock the official user flow: **onboarding → briefing → swipe → history → preferences**.

## Acceptance criteria
- [ ] Flow is documented in README
- [ ] Out-of-scope list defined (no auth, no premium, no full web parity)
- [ ] All new tasks can be validated against this scope"

gh issue create --repo $REPO \
  --title "Refactor mobile screen navigation structure" \
  --label "area:mobile,type:refactor,priority:P0,sprint:W1" \
  --milestone $M1 \
  --body "## Objective
Replace centralized screen string switching in \`App.jsx\` with a clear, modular navigation structure.

## Files
- \`frontend-mobile/App.jsx\`

## Acceptance criteria
- [ ] All current screens reachable without regressions
- [ ] Navigation logic is modular and readable
- [ ] No broken transitions in core flow"

gh issue create --repo $REPO \
  --title "Split App-level state into domain modules" \
  --label "area:mobile,type:refactor,priority:P0,sprint:W1" \
  --milestone $M1 \
  --body "## Objective
Separate \`App.jsx\` state responsibilities into briefing, preferences, and session/UI.

## Files
- \`frontend-mobile/App.jsx\`

## Acceptance criteria
- [ ] Domain boundaries are clear and traceable
- [ ] Data flow is easy to follow and debug
- [ ] Core flow behavior is unchanged"

gh issue create --repo $REPO \
  --title "Add environment-based API base URL for mobile" \
  --label "area:mobile,type:feature,priority:P1,sprint:W1" \
  --milestone $M1 \
  --body "## Objective
Remove hardcoded API addresses from \`src/api.js\` and support dev/demo/prod configs without code changes.

## Files
- \`frontend-mobile/src/api.js\`

## Acceptance criteria
- [ ] API base URL changeable via env config
- [ ] Dev and demo targets verified
- [ ] Setup steps documented"

echo "=== Luodaan issuet (W2) ==="

gh issue create --repo $REPO \
  --title "Add loading, error, and empty states to key mobile screens" \
  --label "area:mobile,type:feature,priority:P0,sprint:W2" \
  --milestone $M2 \
  --body "## Objective
Eliminate silent failures and dead-end states in briefing, history, and preferences screens.

## Files
- \`frontend-mobile/src/components/ArticleCard.jsx\`
- \`frontend-mobile/src/components/HistoryScreen.jsx\`
- \`frontend-mobile/src/components/PreferencesPanel.jsx\`

## Acceptance criteria
- [ ] Briefing, history, preferences each have loading/error/empty states
- [ ] User always has a clear next action
- [ ] No silent failure paths remain"

gh issue create --repo $REPO \
  --title "Polish onboarding and completion flow continuity" \
  --label "area:mobile,type:feature,priority:P0,sprint:W2" \
  --milestone $M2 \
  --body "## Objective
Make first-time experience and end-of-briefing flow feel coherent and complete.

## Files
- \`frontend-mobile/src/components/OnboardingScreen.jsx\`
- \`frontend-mobile/App.jsx\`

## Acceptance criteria
- [ ] User cannot get stuck in onboarding or completion screen
- [ ] Transition back to news feed is clear
- [ ] Messaging is consistent across the flow"

gh issue create --repo $REPO \
  --title "Add retry actions for critical mobile API calls" \
  --label "area:mobile,type:feature,priority:P1,sprint:W2" \
  --milestone $M2 \
  --body "## Objective
Allow users to recover from temporary network errors without restarting the app.

## Files
- \`frontend-mobile/src/api.js\`

## Acceptance criteria
- [ ] Retry available for briefing, preferences, feedback calls
- [ ] Retry updates UI state correctly
- [ ] Error copy is user-friendly, not technical"

echo "=== Luodaan issuet (W3) ==="

gh issue create --repo $REPO \
  --title "Add backend operational logging for briefing/ingest/reenrich" \
  --label "area:backend,type:feature,priority:P0,sprint:W3" \
  --milestone $M3 \
  --body "## Objective
Improve observability so failures are diagnosable without guesswork.

## Files
- \`backend/app/services/ingest.py\`
- \`backend/app/services/scoring.py\`
- \`backend/app/main.py\`

## Acceptance criteria
- [ ] Success and error logs exist for core operations
- [ ] Logs are consistent and readable
- [ ] Background job (reenrich) status is visible in logs"

gh issue create --repo $REPO \
  --title "Standardize backend error response format" \
  --label "area:backend,type:refactor,priority:P0,sprint:W3" \
  --milestone $M3 \
  --body "## Objective
Return predictable error payloads to the mobile client across all core endpoints.

## Files
- \`backend/app/main.py\`
- \`backend/app/models.py\`

## Acceptance criteria
- [ ] Core endpoints use the same error shape
- [ ] Mobile client can map errors to user-friendly messages without per-endpoint hacks
- [ ] Documented in code"

gh issue create --repo $REPO \
  --title "Modularize backend routes into domain routers" \
  --label "area:backend,type:refactor,priority:P1,sprint:W3" \
  --milestone $M3 \
  --body "## Objective
Split \`main.py\` into APIRouter modules: briefing, preferences, feedback, admin.

## Files
- \`backend/app/main.py\`
- \`backend/app/api/\` (uudet router-tiedostot)

## Acceptance criteria
- [ ] Route split complete with behavior parity
- [ ] Main app entry is simpler and easier to read
- [ ] No API contract breakage for mobile client"

gh issue create --repo $REPO \
  --title "Update README to reflect actual summarization and architecture" \
  --label "area:backend,type:docs,priority:P1,sprint:W3" \
  --milestone $M3 \
  --body "## Objective
Align README with actual summarization line (LLM vs placeholder), real mobile-first architecture, and correct startup steps.

## Files
- \`README.md\`
- \`backend/app/services/summarizer.py\`

## Acceptance criteria
- [ ] README is not contradicted by the actual implementation
- [ ] Mobile startup steps are correct
- [ ] Summarization/fallback behavior is accurately described"

echo "=== Luodaan issuet (W4) ==="

gh issue create --repo $REPO \
  --title "Add backend smoke/API tests for critical endpoints" \
  --label "area:backend,type:test,priority:P0,sprint:W4" \
  --milestone $M4 \
  --body "## Objective
Add automated confidence checks for the critical API path.

## Endpoints to cover
- \`GET /api/health\`
- \`GET /api/briefing\`
- \`GET /api/preferences\` + \`PUT /api/preferences\`
- \`POST /api/feedback\`
- \`GET /api/history\`

## Acceptance criteria
- [ ] All listed endpoints covered
- [ ] Tests run consistently in local dev environment
- [ ] Regressions are caught before they reach mobile"

gh issue create --repo $REPO \
  --title "Add mobile component tests for core interactions" \
  --label "area:mobile,type:test,priority:P0,sprint:W4" \
  --milestone $M4 \
  --body "## Objective
Cover onboarding, article card swipe, and preferences interactions with component tests.

## Files
- \`frontend-mobile/src/components/OnboardingScreen.jsx\`
- \`frontend-mobile/src/components/ArticleCard.jsx\`
- \`frontend-mobile/src/components/PreferencesPanel.jsx\`

## Acceptance criteria
- [ ] Render + interaction paths tested for all three components
- [ ] Tests verify expected user behavior
- [ ] Baseline suite is stable and repeatable"

gh issue create --repo $REPO \
  --title "Run scoring calibration pass on 20 articles" \
  --label "area:backend,type:feature,priority:P1,sprint:W4" \
  --milestone $M4 \
  --body "## Objective
Improve recommendation quality by reviewing and adjusting scoring weights manually.

## Files
- \`backend/app/services/scoring.py\`
- \`backend/app/config.py\`

## Acceptance criteria
- [ ] 20-article manual review completed
- [ ] Findings documented (what scored too high/low and why)
- [ ] Weight adjustments decided and tracked as follow-up"

gh issue create --repo $REPO \
  --title "Execute full end-to-end demo run without manual fixes" \
  --label "area:mobile,area:backend,type:docs,priority:P1,sprint:W4" \
  --milestone $M4 \
  --body "## Objective
Validate MVP readiness by running the complete flow start to finish.

## Flow to verify
onboarding → briefing load → ≥3 swipes → history view → preferences change → briefing reload

## Acceptance criteria
- [ ] Full flow completes without ad-hoc backend interventions
- [ ] Demo checklist documented for repeatable use
- [ ] Any blockers found are filed as follow-up issues"

echo ""
echo "=== Valmis! ==="
echo "Kaikki labelit, milestonet ja 14 issuet luotu repolle $REPO"
echo "Katso: https://github.com/$REPO/issues"
