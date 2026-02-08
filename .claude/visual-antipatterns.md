# Visual Anti-Patterns Reference

Common LLM-generated frontend visual mistakes that a human spots immediately but an LLM cannot "see." This reference is shared across specialists (prevention) and agents (detection).

**Referenced by:**
- `qa-browser-tester` — runtime Playwright checks (Phase 7)
- `style-guide-auditor` — baseline quality floor
- `frontend-style-reviewer` — static code review (Step 4)
- `/specialists/uix` — produces testable UIX-XX decisions
- `/specialists/design` — Visual Quality Floor in style-guide.md template

**Severity model:**
- **Hard Fail** (CRITICAL/MAJOR): Blocks the pipeline. Contrast failures, overflow, invisible inputs, missing focus states, touch targets.
- **Soft Warning** (MINOR/INFO): Logged but doesn't block. Spacing rhythm, line length, font fallbacks, empty state suggestions.

---

## A. Contrast & Readability

### AP-01: Dark on Dark / Light on Light
**What:** Text color too close to background color, making text unreadable.
**Why LLMs do it:** LLMs set colors independently without computing the resulting contrast. Dark mode themes are especially prone — `gray-400` text on `gray-800` background "sounds reasonable" but fails WCAG.
**Detect (static):** Flag `color` and `background-color` on same element/container where both are in dark range (lightness < 40%) or both in light range (lightness > 70%).
**Detect (runtime):** Extract computed `color` + `background-color`, walk DOM for effective background, calculate WCAG contrast ratio. Flag < 4.5:1 (normal text) or < 3:1 (large text ≥18px or ≥14px bold). **Severity: CRITICAL.**
**Prevent:** Style guide minimum contrast ratio rule. Semantic color tokens with pre-validated pairings.

### AP-02: Low-Contrast Placeholder Text
**What:** Placeholder text in form fields is too faint to read.
**Why LLMs do it:** Placeholders are styled with very light gray to "look subtle," but the result is illegible on light backgrounds.
**Detect (static):** Check `::placeholder` color values — flag lightness > 75% on white backgrounds.
**Detect (runtime):** Extract placeholder computed color via `getComputedStyle(input, '::placeholder')`. **Severity: MAJOR.**
**Prevent:** Style guide placeholder color token with minimum 3:1 contrast.

### AP-03: Unreadable Disabled State
**What:** Disabled elements have such low contrast they're invisible.
**Why LLMs do it:** `opacity: 0.3` or very light gray is applied without checking readability.
**Detect (static):** Flag disabled states with `opacity` < 0.4 or color lightness > 80%.
**Detect (runtime):** Check `[disabled]` elements for contrast ratio. **Severity: MAJOR.**
**Prevent:** Style guide disabled state must maintain minimum 3:1 contrast.

### AP-04: Error Text on Colored Background
**What:** Red error text unreadable on dark or colored backgrounds.
**Why LLMs do it:** Error text is always `color: red` regardless of container background.
**Detect (static):** Flag hardcoded red/error colors without checking parent background context.
**Detect (runtime):** Extract error message computed color + effective background. **Severity: MAJOR.**
**Prevent:** Semantic error color token defined per background context.

### AP-05: Indistinguishable Links
**What:** Links look identical to body text — no color difference, no underline.
**Why LLMs do it:** Links styled with `text-decoration: none` and same color as body text for "clean look."
**Detect (static):** Flag `a` elements with `text-decoration: none` and no distinct color or hover change.
**Detect (runtime):** Compare link computed color to surrounding text color. Flag if identical. **Severity: MAJOR.**
**Prevent:** Links must differ from body text by color OR underline OR both.

---

## B. Layout & Spacing

### AP-06: Content Touching Edges
**What:** Page content has zero padding, text touching browser/container edges.
**Why LLMs do it:** LLMs forget to add padding to wrapper containers, or set `padding: 0` explicitly.
**Detect (static):** Flag `padding: 0` on content-wrapping containers (main, article, section, .container).
**Detect (runtime):** Extract padding on content containers. Flag 0px. **Severity: MAJOR.**
**Prevent:** Style guide minimum container padding (e.g., 16px).

### AP-07: Inconsistent Spacing
**What:** Same component type has different spacing values across the page.
**Why LLMs do it:** Each component instance gets independently styled with arbitrary values.
**Detect (static):** Compare margin/padding values across same-class elements.
**Detect (runtime):** Extract spacing values for same-type components, flag variance. **Severity: MINOR.**
**Prevent:** Spacing scale tokens — all spacing from a defined scale.

### AP-08: No Breathing Room
**What:** Sections crammed together with no visual separation — wall of content.
**Why LLMs do it:** LLMs optimize for fitting everything visible, neglecting whitespace as a design tool.
**Detect (static):** Flag sibling sections with `margin: 0` or `gap: 0`.
**Detect (runtime):** Measure gap between major sections. Flag < 16px. **Severity: MINOR.**
**Prevent:** Section spacing rule in style guide (e.g., minimum 32px between sections).

### AP-09: Misaligned Elements
**What:** Left edges of elements in a column don't line up — visually jagged.
**Why LLMs do it:** Different padding/margin values on sibling elements create uneven alignment.
**Detect (runtime):** Compare `getBoundingClientRect().left` across sibling elements. Flag variance > 4px. **Severity: MINOR.**
**Prevent:** Consistent grid/container padding rules.

---

## C. Typography

### AP-10: Body Text Too Small
**What:** Main content text below 14px — hard to read, especially on mobile.
**Why LLMs do it:** Default browser `font-size: 16px` gets overridden to 12px or 13px for "compact" look.
**Detect (static):** Flag body/paragraph `font-size` values below 14px.
**Detect (runtime):** Extract computed font-size on `p`, `li`, `td` elements. Flag < 14px. **Severity: MAJOR.**
**Prevent:** Style guide body text minimum 14px.

### AP-11: Excessive Line Length
**What:** Text lines stretch across full viewport width — hard to track to next line.
**Why LLMs do it:** No `max-width` set on text containers, content fills available space.
**Detect (static):** Flag text containers without `max-width` or `max-inline-size`.
**Detect (runtime):** Measure `clientWidth` of text containers. Flag > 720px (~80ch). **Severity: MINOR.**
**Prevent:** Style guide max line length (e.g., 65-75ch / 720px).

### AP-12: Insufficient Line Height
**What:** Text lines too close together — cramped, hard to read.
**Why LLMs do it:** `line-height: 1` or `line-height: normal` left as default for body text.
**Detect (static):** Flag body text `line-height` values below 1.3.
**Detect (runtime):** Extract computed line-height, compare to font-size. Flag ratio < 1.3. **Severity: MAJOR.**
**Prevent:** Style guide minimum line-height 1.4 for body, 1.2 for headings.

### AP-13: Thin Font on Small Text
**What:** Light font weight (300) combined with small font size (< 16px) — unreadable.
**Why LLMs do it:** `font-weight: 300` applied globally for "elegant" look.
**Detect (static):** Flag `font-weight: 300` or `lighter` on elements with `font-size` < 16px.
**Detect (runtime):** Cross-check computed font-weight and font-size. **Severity: MAJOR.**
**Prevent:** Minimum font-weight 400 for text below 16px.

### AP-14: Font Size Chaos
**What:** Too many distinct font sizes on one page — no visual hierarchy rhythm.
**Why LLMs do it:** Each heading/label gets an arbitrary size instead of following a type scale.
**Detect (runtime):** Count distinct computed font-size values on page. Flag > 8. **Severity: MINOR.**
**Prevent:** Type scale with defined steps (e.g., 1.25 major third).

---

## D. Responsive & Overflow

### AP-15: Horizontal Scroll
**What:** Page has horizontal scrollbar — content wider than viewport.
**Why LLMs do it:** Fixed-width elements, uncontrolled images, or wide tables break layout.
**Detect (runtime):** `document.documentElement.scrollWidth > document.documentElement.clientWidth` at both desktop and mobile viewports. **Severity: CRITICAL.**
**Prevent:** `max-width: 100%` on images/media. Responsive table patterns. No fixed widths.

### AP-16: Content Overflow / Clipping
**What:** Text or elements spilling outside their container, or clipped by `overflow: hidden`.
**Why LLMs do it:** Fixed heights on containers that hold dynamic content.
**Detect (static):** Flag `overflow: hidden` combined with fixed `height` on text containers.
**Detect (runtime):** Check containers with `overflow: hidden` — if `scrollHeight > clientHeight` by > 10px, content is clipped. **Severity: MAJOR.**
**Prevent:** Use `min-height` instead of `height`. Add overflow handling strategy.

### AP-17: Distorted Images
**What:** Images stretched or squished — wrong aspect ratio.
**Why LLMs do it:** Both `width` and `height` set to fixed values that don't match image's natural ratio.
**Detect (runtime):** Compare `naturalWidth/naturalHeight` vs rendered ratio. Flag distortion > 5%. **Severity: MAJOR.**
**Prevent:** Use `object-fit: cover/contain` or only constrain one dimension.

### AP-18: Tiny Touch Targets
**What:** Interactive elements too small to tap on mobile (< 44×44px).
**Why LLMs do it:** Desktop-designed buttons/links don't account for finger size.
**Detect (runtime):** At mobile viewport (375px), measure `getBoundingClientRect()` on all interactive elements. Flag width or height < 44px. Exception: inline text links (MINOR). **Severity: MAJOR.**
**Prevent:** Minimum 44×44px touch target rule in style guide.

---

## E. Color & Visual Hierarchy

### AP-19: Flat Hierarchy
**What:** Everything on the page has the same visual weight — no primary/secondary distinction.
**Why LLMs do it:** All text same size, all buttons same style, no emphasis on primary actions.
**Detect (runtime):** Compare primary vs secondary button colors/sizes. Check heading sizes vs body. Flag if primary CTA is indistinguishable from secondary actions. **Severity: MAJOR.**
**Prevent:** Style guide defines primary/secondary/tertiary button variants with distinct visual weight.

### AP-20: Color Overload
**What:** Too many competing colors on one page — visual chaos.
**Why LLMs do it:** Each section/component gets a unique color instead of using a palette.
**Detect (runtime):** Count distinct hue values across the page (excluding grays). Flag > 5. **Severity: MINOR.**
**Prevent:** Color palette limited to primary + secondary + 2-3 semantic colors.

### AP-21: Indistinguishable Status Colors
**What:** Success, error, warning, and info states all look similar.
**Why LLMs do it:** All use similar green/yellow shades, or only differ slightly.
**Detect (runtime):** Extract computed colors for success/error/warning/info elements. Check pairwise contrast between them. Flag if any pair has contrast < 3:1. **Severity: MAJOR.**
**Prevent:** Semantic color tokens with distinct hues for each status.

---

## F. Component Affordance

### AP-22: Invisible Buttons
**What:** Buttons have no background, no border — indistinguishable from text.
**Why LLMs do it:** "Ghost buttons" applied to primary actions, or button styling removed.
**Detect (static):** Flag buttons with `background: transparent/none` AND `border: none` AND no distinct color.
**Detect (runtime):** Check button `background-color` vs page background. Flag if identical and no visible border. **Severity: MAJOR.**
**Prevent:** Buttons must differ from background by color, border, or shadow.

### AP-23: Borderless Form Inputs
**What:** Form inputs have no visible border — invisible fields against the background.
**Why LLMs do it:** `border: none` for "modern clean" look, or relying on focus ring only.
**Detect (static):** Flag `input`/`select`/`textarea` with `border: none` without compensating `box-shadow` or `outline`.
**Detect (runtime):** Check `border-width`, `outline`, `box-shadow` on form elements. Flag if all are 0/none. **Severity: MAJOR.**
**Prevent:** Form inputs must have visible boundary (border ≥ 1px OR shadow OR distinct background).

### AP-24: Table Headers Look Like Data
**What:** Table headers (`<th>`) visually identical to data cells (`<td>`).
**Why LLMs do it:** No distinct styling for headers — same font weight, size, background.
**Detect (runtime):** Compare computed `font-weight`, `background-color`, `font-size` between `th` and `td`. Flag if all identical. **Severity: MINOR.**
**Prevent:** Table headers must have distinct weight, background, or size.

### AP-25: Missing Hover/Focus States
**What:** Interactive elements show no visual change on hover or focus — no feedback.
**Why LLMs do it:** `:hover` and `:focus` styles omitted, only default state defined.
**Detect (static):** Flag interactive elements without `:hover` or `:focus`/`:focus-visible` style rules.
**Detect (runtime):** Programmatically hover/focus elements, compare computed styles before/after. Flag if no change. **Severity: MAJOR.**
**Prevent:** All interactive elements must have hover + focus state definitions.

### AP-26: Missing Loading States
**What:** Content appears suddenly, causing layout shift — no skeleton/spinner/placeholder.
**Why LLMs do it:** Async data fetched and rendered without transition, leaving blank space then sudden jump.
**Detect (runtime):** Track bounding box positions before and after network idle. Flag major shifts (CLS > 0.1). **Severity: MINOR.**
**Prevent:** Loading skeletons or spinners for async content areas.

---

## G. Z-index & Layering

### AP-27: Dropdown Behind Content
**What:** Dropdown menus render behind sibling elements or overlapping containers.
**Why LLMs do it:** Missing `z-index` or conflicting stacking contexts.
**Detect (runtime):** Open dropdowns/menus, check if visible content is obscured via `elementFromPoint()`. **Severity: MAJOR.**
**Prevent:** Define z-index scale in style guide. Dropdown z-index must exceed content z-index.

### AP-28: Modal Not Covering Viewport
**What:** Modal overlay doesn't cover full screen, or content shows through.
**Why LLMs do it:** Modal overlay missing `position: fixed` + `inset: 0`, or z-index too low.
**Detect (runtime):** When modal is open, check overlay dimensions vs viewport. **Severity: MAJOR.**
**Prevent:** Modal overlay template with fixed positioning and full viewport coverage.

### AP-29: Sticky Header Overlap
**What:** Sticky/fixed header overlaps body content without visual separation.
**Why LLMs do it:** Header is `position: sticky` but no `box-shadow` or border on scroll.
**Detect (runtime):** Scroll page, check if sticky header overlaps content (via `elementFromPoint` below header). **Severity: MINOR.**
**Prevent:** Sticky elements get shadow or border on scroll.

---

## H. State & Interaction Feedback

### AP-30: Missing Focus Ring
**What:** No visible focus indicator when tabbing through interactive elements — keyboard users lost.
**Why LLMs do it:** `outline: none` applied globally for "clean" look, no `:focus-visible` replacement.
**Detect (static):** Flag `outline: none` or `outline: 0` without `:focus-visible` style. Flag interactive elements without any focus styling.
**Detect (runtime):** Tab through elements in Playwright, check for visible outline/border change via computed styles. **Severity: CRITICAL.**
**Prevent:** All interactive elements must have visible `:focus-visible` style. Never remove outline without replacing.

### AP-31: No Active State Feedback
**What:** Buttons show no change when clicked/pressed — no click feedback.
**Why LLMs do it:** `:active` state not defined, only `:hover`.
**Detect (runtime):** Click buttons, compare computed styles during mousedown vs rest. **Severity: MINOR.**
**Prevent:** Buttons should have `:active` state (slight scale, darken, or depression effect).

### AP-32: Invisible Disabled State
**What:** Disabled elements look identical to enabled ones — users try to interact and nothing happens.
**Why LLMs do it:** `disabled` attribute added but no visual styling change.
**Detect (runtime):** Compare computed styles of `[disabled]` vs enabled sibling elements. Flag if identical. **Severity: MAJOR.**
**Prevent:** Disabled state must have reduced opacity (≥ 0.4) or distinct color/background.

### AP-33: Placeholder-as-Label
**What:** Form inputs use only placeholder text as labels — labels disappear on focus.
**Why LLMs do it:** Placeholders used instead of `<label>` elements for space savings.
**Detect (static):** Flag `<input>` elements without associated `<label for="">` or `aria-label`.
**Detect (runtime):** Check input elements for associated labels. **Severity: MAJOR.**
**Prevent:** Every input must have a persistent label (not just placeholder).

---

## I. Content Volatility

### AP-34: Fixed-Height Text Clipping
**What:** Text containers with fixed `height` clip content when text is longer than expected.
**Why LLMs do it:** Layouts designed for specific "John Doe" length strings, break with real data.
**Detect (static):** Flag fixed `height` on text-containing elements without `overflow` handling.
**Detect (runtime):** Inject long strings (50+ chars) into form fields, check for overflow/clipping. **Severity: MAJOR.**
**Prevent:** Use `min-height` instead of `height`. Add `text-overflow: ellipsis` or scroll strategy.

### AP-35: No Truncation Strategy
**What:** Long text overflows containers with no ellipsis, wrapping, or scroll.
**Why LLMs do it:** `text-overflow: ellipsis` not applied, or `white-space: nowrap` missing.
**Detect (static):** Flag constrained-width elements with text content but no overflow handling.
**Detect (runtime):** Check text elements where `scrollWidth > clientWidth`. **Severity: MAJOR.**
**Prevent:** Define truncation strategy per component (ellipsis, wrap, tooltip, expand).

### AP-36: Blank Empty States
**What:** When no data exists, container shows blank space instead of helpful message.
**Why LLMs do it:** Only the "data exists" state is implemented — no fallback for empty.
**Detect (runtime):** Check for containers with no visible child content (empty `<tbody>`, empty `<ul>`, empty `<div>` with no text). **Severity: MINOR.**
**Prevent:** Every data container must have an empty state with message and CTA.

### AP-37: Unpredictable Card Heights
**What:** Cards in a grid have different heights due to varying content length.
**Why LLMs do it:** No `min-height` or content normalization strategy.
**Detect (runtime):** Compare heights of sibling cards in a grid. Flag variance > 50px. **Severity: MINOR.**
**Prevent:** Cards in grids should use consistent min-height or CSS Grid `align-items: stretch`.

---

## J. Motion & Perceived Quality

### AP-38: Transition All
**What:** `transition: all` causes unintended animations on every property change — jank.
**Why LLMs do it:** Shortcut instead of specifying exact properties (`transition: background-color 200ms`).
**Detect (static):** Flag `transition: all` in any stylesheet. **Severity: MINOR.**
**Prevent:** Always specify exact transition properties.

### AP-39: Hover-Only Disclosure
**What:** Content only visible on `:hover` — inaccessible on touch devices.
**Why LLMs do it:** Tooltips, dropdown triggers, or reveal panels use hover without touch fallback.
**Detect (static):** Flag `opacity: 0` / `visibility: hidden` + `:hover` reveal without `@media (hover: none)` fallback.
**Detect (runtime):** At mobile viewport (no hover), verify all content/controls are discoverable. **Severity: MAJOR.**
**Prevent:** All hover-revealed content must have a touch-accessible alternative.

### AP-40: No Reduced Motion Respect
**What:** Animations run regardless of user's `prefers-reduced-motion` setting.
**Why LLMs do it:** `@media (prefers-reduced-motion: reduce)` not implemented.
**Detect (static):** Flag animations/transitions without `prefers-reduced-motion` media query.
**Detect (runtime):** Emulate `prefers-reduced-motion: reduce`, verify animations stop. **Severity: MINOR.**
**Prevent:** All animations must respect `prefers-reduced-motion`.

### AP-41: Font Fallback Failure
**What:** Declared font family not loaded, ugly system font displayed instead.
**Why LLMs do it:** Custom font specified without system fallback stack, or font URL broken.
**Detect (static):** Flag `font-family` declarations without system fallback (e.g., `sans-serif`, `serif`).
**Detect (runtime):** Check `document.fonts.check()` for each declared family. **Severity: MINOR.**
**Prevent:** Every font-family must include system fallback stack.

### AP-42: Scroll Lock from Modals
**What:** Opening a modal doesn't prevent background scroll, or closing doesn't restore it.
**Why LLMs do it:** `body { overflow: hidden }` not toggled properly with modal open/close.
**Detect (runtime):** Open modal, attempt to scroll background. Close modal, verify scroll restored. **Severity: MAJOR.**
**Prevent:** Modal implementation must manage body scroll lock.
