# PR metadata
PR_TITLE="feat(i18n): add Arabic (ar) translations and RTL support"

PR_BODY=$(cat <<'EOF'
This PR adds complete Arabic (ar) localization support for the dashboard and RTL layout handling.

Summary of changes:
- Add Arabic locale files under `dashboard/src/i18n/locales/ar/`:
  - core: common.json, actions.json, status.json, navigation.json, header.json, shared.json
  - features: dashboard.json, chat.json, settings.json
  - messages: errors.json, success.json, validation.json
- Update `dashboard/src/i18n/composables.ts`:
  - Register 'ar' in available locales
  - Add Arabic option ("العربية") to languageOptions
  - Persist locale to localStorage
  - Toggle `document.documentElement.lang` and `dir` and a `body.is-rtl` class when Arabic is selected
- Update `dashboard/src/scss/style.scss`:
  - Append RTL helper rules to handle direction, flipping, and spacing for RTL layouts
- Update `dashboard/src/i18n/translations.ts`:
  - (Imports + mapping) Register Arabic translation imports and an 'ar' mapping entry so it is bundled at build time

Testing & validation:
1. Checkout this branch locally (it should already be the current branch).
2. Start the dashboard dev server:
   cd dashboard
   pnpm install   # or npm install
   pnpm dev
3. Open the UI and switch language to "العربية" in the language selector.
4. Verify:
   - The html element has lang="ar" and dir="rtl"
   - document.body.classList contains "is-rtl"
   - Translated strings from the new ar files display correctly for header, dashboard, chat, and settings
   - Layout flows right-to-left; check navigation, text alignment, and form controls
   - Run a production build: pnpm build and review the built assets for RTL correctness
5. If any components need additional flipping, add `.rtl-flip` class or logical CSS where necessary.

Notes:
- No secret or credential data is added to the repo.
- The branch was created and pushed automatically by the automation script.
- If CI fails due to missing translations in other modules, copy corresponding en-US/zh-CN files into the ar folder as placeholders and translate iteratively.

If you want reviewers, assignees, or labels added, set the environment variables:
- REVIEWERS="alice,bob"
- ASSIGNEE="alice"
- LABELS="i18n,feature"
- DRAFT=1   (to create a draft PR)
EOF
)
