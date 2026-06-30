# UI Design Review

## Purpose

Review rendered frontend UI for design quality, accessibility, responsiveness, interaction states,
and implementation polish. Use after building or modifying a frontend surface, or when the user asks
for a UI review, design critique, visual QA, polish pass, responsive audit, accessibility check, or
post-build frontend review.

This playbook reviews the application the user sees in the browser, not external design-file parity.

## Process

### 1. Establish The Review Target

Identify the surface and flow under review:

- entry route or file-backed static page
- primary user goal
- changed components or pages
- relevant states: loading, empty, populated, error, success, hover, focus, open modal/menu, selected tab
- design intent from the prompt, task/spec, existing app style, or nearby components

If the route is unclear, inspect package scripts, routes, and changed files before asking.

### 2. Inspect The Code Context

Read the relevant component, page, and style files. Check for:

- reuse of existing components, layout primitives, tokens, icon sets, and font conventions
- duplicated components or hardcoded one-off visual values
- semantic HTML, labels, focus handling, and keyboard behavior
- responsive implementation strategy
- state coverage for forms, lists, async results, overlays, and destructive actions

### 3. Capture Visual Evidence

Run the app when possible and capture screenshots before making review claims. Use the available
browser tool first; if none is available, use Playwright or the repo's existing e2e/screenshot flow.

Temporary artifacts go under `.local/artifacts/<review-slug>/` by default:

```text
.local/artifacts/<review-slug>/
  screenshots/
    desktop-1280.png
    tablet-768.png
    mobile-375.png
  notes.md
```

Use descriptive filenames for extra states such as `menu-open-mobile-375.png`,
`form-error-desktop-1280.png`, or `dark-mode-desktop-1280.png`. The `.local/` tree is ignored and
must not be committed.

Minimum visual coverage for non-trivial reviews:

- desktop around 1280px wide
- tablet around 768px wide when layout changes there
- mobile around 375px wide
- one important interaction state or workflow result

If the app cannot run, state the blocker and perform a code-only review with lower confidence.

### 4. Review Checklist

Prioritize findings that users can perceive or that will create maintenance problems.

**Visual hierarchy**

- The main task or content is the most prominent thing.
- Headings, body text, captions, controls, and metadata have a clear scale.
- The reading path is obvious and does not fight the layout.

**Layout and responsiveness**

- No clipping, accidental wrapping, horizontal overflow, overlapping controls, or trapped scrolling.
- Layout reorganizes intentionally across breakpoints.
- Fixed, sticky, modal, dropdown, and sidebar elements work on mobile.

**Accessibility and interaction**

- Interactive elements are semantic and keyboard-accessible.
- Focus states are visible.
- Icon-only controls have accessible names.
- Forms have labels, errors, loading, disabled, and success states where relevant.
- Motion respects reduced-motion preferences.

**Consistency**

- Similar components look and behave similarly.
- Colors, spacing, radius, shadows, typography, and icons follow the local system.
- Existing components were reused or extended instead of duplicated.

**Content and states**

- Empty, loading, error, long-content, and user-generated-content cases do not break the UI.
- Button labels are specific actions.
- Error and empty-state copy tells users what to do next.

**Performance-sensitive UI**

- Large lists are virtualized or otherwise bounded.
- Images have stable dimensions and lazy loading where appropriate.
- Animations target transform/opacity rather than layout-heavy properties.

### 5. Report Findings

Lead with findings, ordered by severity:

- **Must fix**: broken interactions, inaccessible controls, unreadable content, severe responsive
  failures, major visual regressions.
- **Should fix**: inconsistent states, weak hierarchy, missing responsive refinement, duplicated
  visual patterns.
- **Could improve**: polish, motion tuning, copy refinement, small alignment or spacing issues.

Each finding should include:

- path and line when code evidence exists
- screenshot path when visual evidence exists
- what the user sees
- concrete fix direction

If no issues are found, say that clearly and mention any untested viewports or states.

## Durable Reports

Do not commit screenshots by default. If the user asks for a saved review report, write Markdown to
`docs/resources/_reports/ui-design-review/<timestamp>_<slug>.md` and reference temporary screenshots
under `.local/artifacts/<review-slug>/`. If screenshots must be committed as durable artifacts, list
them in `artifacts/README.md` and use the repo's artifact/LFS convention.
