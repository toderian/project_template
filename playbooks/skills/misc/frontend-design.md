# Frontend Design

## Purpose

Create distinctive, production-grade frontend interfaces with high design quality and rendered
verification. Use when the user asks to build web components, pages, applications, dashboards,
games, or redesign/restyle existing UI. Generate creative, polished code that avoids generic AI
aesthetics and proves the result in a browser.

Imported from Anthropic's [`frontend-design`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/frontend-design) plugin.

## Process

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic
"AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details,
creative choices, and visual verification.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

### 1. Discover the Existing UI System

Before designing or coding, inspect the real project surface:

- Component directories: `components/`, `ui/`, `shared/`, feature component folders, and reusable layout primitives.
- Styling system: CSS variables, Tailwind config, theme providers, CSS modules, shadcn, MUI, Chakra, or equivalent.
- Tokens and fonts: color variables, spacing scale, type ramp, font loading, icon library, radius/shadow conventions.
- Existing pages: route/layout patterns, app shell, navigation, empty/loading/error states, responsive breakpoints.
- UI dependencies: animation, charting, table, form, icon, and component libraries in package manifests.

Reuse and extend established components unless the task is explicitly to replace the design system.
Do not create duplicate buttons, inputs, cards, navigation, or token sets when a local pattern exists.

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:

- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work — the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:

- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

### 2. Build A Small Design System First

For non-trivial UI, write down the system before coding:

- Palette: background, surface, text, muted text, border, accent, semantic states, and dark-mode stance when the project supports it.
- Typography: display/body/utility roles, sizes, line heights, weights, and control text treatment.
- Layout: container model, grid/list/table/canvas/card usage, spacing scale, and responsive behavior.
- Components: button/input/navigation/card/table/form/empty-state variants and interaction states.
- Motion: what animates, why it helps, duration/easing, and reduced-motion behavior.

This can live in task notes, a spec/design artifact, or a short implementation note. It should not
become a new global token layer unless the feature genuinely needs one.

## Frontend Aesthetics Guidelines

Focus on:

- **Typography**: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics; unexpected, characterful font choices. Pair a distinctive display font with a refined body font.
- **Color & Theme**: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Motion**: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions. Use scroll-triggering and hover states that surprise.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density.
- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, and grain overlays.

NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white backgrounds), predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Remember: capable agents are capable of extraordinary creative work. Don't hold back; show what can truly be created when thinking outside the box and committing fully to a distinctive vision.

## UI Quality Gates

Every meaningful frontend change should satisfy these gates before final handoff:

- **Mobile first**: verify the layout at about 375px wide, then tablet and desktop. Touch targets should be at least 44px where practical, body/input text should remain readable, and mobile navigation must not overflow.
- **Accessibility**: use semantic elements, labels for controls, visible focus states, keyboard-accessible interactions, sufficient contrast, useful alt text, and `prefers-reduced-motion` for meaningful animation.
- **Responsive behavior**: components reorganize intentionally rather than merely shrinking. Check text wrapping, line length, clipping, horizontal overflow, z-index, fixed/sticky elements, and safe-area issues.
- **Interaction states**: cover default, hover, focus, active, disabled, loading, empty, success, and error states where relevant.
- **Implementation discipline**: use existing components/tokens, keep repeated styles shared, avoid one-off hex values unless the project has no token system, and do not add large dependencies for small visual needs.

## Rendered Verification

Run the app and inspect the rendered UI whenever the project can be run locally. A passing build is
not enough for visual work.

1. Start the repo's normal dev server or static preview.
2. Capture screenshots for the important surface at desktop, mobile, and any state the task changed.
3. Inspect screenshots visually for hierarchy, spacing, typography, color, clipping, overlap,
   responsive behavior, and interaction states.
4. Exercise at least one core interaction and verify the resulting UI state.
5. Fix visible issues before final handoff, then rerun the relevant screenshot or interaction check.

Temporary screenshots, traces, and browser QA artifacts go under
`.local/artifacts/<descriptive-slug>/` by default, for example
`.local/artifacts/settings-redesign/screenshots/mobile-375.png`. The `.local/` tree is ignored and
must not be committed. If screenshots or reports need to be durable, use
`docs/resources/_reports/<workflow>/` for Markdown findings and register large kept artifacts in
`artifacts/README.md`.

For a dedicated post-build critique, use the `ui-design-review` skill.
