# Design — Common Mistakes & Anti-Patterns

Common mistakes when running the design specialist. Each pattern
describes a failure mode that leads to poor visual design decisions.

**Referenced by:** `specialist_design.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Visual System

### STYLE-AP-01: Color Psychology as Science
**Mistake:** Presents color associations ("blue = trust," "red = urgency," "green = growth") as universal truths that should drive palette selection, without acknowledging that these associations are culturally dependent, context-dependent, and frequently contradicted by successful products.
**Why:** Color psychology blog posts are abundant in training data and state correlations as causal rules. The model absorbs "blue builds trust" as a design principle rather than a Western marketing heuristic. In China, red signals prosperity; in South Korea, death is associated with red; in the Middle East, green carries religious significance.
**Example:**
```
STYLE-01: Primary Color
Use blue (#2563EB) as the primary brand color. Blue conveys trust,
reliability, and professionalism — essential for a financial product.
Studies show that 33% of top brands use blue because it creates an
emotional connection with users.
```
**Instead:** Choose colors based on: brand identity (what does the brand want to feel like?), differentiation (what colors do competitors use — should you match or contrast?), accessibility (does the color meet WCAG contrast requirements?), and practical usability (does it work as a button color, a link color, and a background accent?). Present color options to the user with swatches, not psychological justifications. Let the user pick what resonates with their brand.

### STYLE-AP-02: Too Many Colors
**Mistake:** Defines 8+ colors in the palette — primary, secondary, tertiary, accent, highlight, plus 5 semantic colors. The result is a visual cacophony where every element competes for attention and the design lacks coherence.
**Why:** The model generates comprehensive solutions. When asked to define a color palette, it tries to cover every possible use case by adding more colors. Training data includes design system documentation from large companies (Google Material, IBM Carbon) that define extensive palettes for massive product suites — not appropriate for an MVP.
**Example:**
```
STYLE-02: Color Palette
Primary: #2563EB (blue)
Secondary: #7C3AED (purple)
Tertiary: #059669 (green)
Accent: #F59E0B (amber)
Highlight: #EC4899 (pink)
Success: #10B981     Error: #EF4444
Warning: #F59E0B     Info: #3B82F6
Surface: #F8FAFC     Border: #E2E8F0
```
(10 distinct hues for an app with 5 screens)
**Instead:** Start minimal: one primary color, one neutral scale (gray), and 3 semantic colors (success/error/warning — info can share the primary hue). That is 5 hues. A secondary color is optional and should only be added if the design actually needs a second accent (e.g., for distinguishing categories). Present the minimal palette first. Expand only if the user identifies a specific need that requires more colors.

### STYLE-AP-03: 8pt Grid as Religion
**Mistake:** Applies the 8pt spacing grid rigidly to every element, including dense data UIs (admin tables, dashboards, code editors) where 8px minimum spacing wastes screen real estate and forces awkward proportions.
**Why:** The 8pt grid system is heavily promoted in design systems (Material Design, Ant Design) and design tutorial content. The model treats it as a universal rule rather than a useful default that should be adapted to context. Dense data interfaces benefit from a 4pt base unit.
**Example:**
```
STYLE-03: Spacing System
All spacing uses the 8pt grid: 8, 16, 24, 32, 40, 48, 56, 64.
No exceptions. Table cell padding: 16px. Form field gap: 24px.
Dashboard card padding: 32px.
```
(table with 15 columns cannot fit on screen because every cell has 16px padding)
**Instead:** Define the spacing base unit based on the UI density the project requires. Content-focused apps (blogs, marketing, e-commerce): 8pt base works well. Data-dense apps (admin panels, analytics dashboards, trading platforms): 4pt base allows 4, 8, 12, 16, 24, 32 — more granular control. Present both options with mockups showing the density difference. Let the user choose based on their product's character.

### STYLE-AP-04: Font Pairing Without Hierarchy
**Mistake:** Selects two fonts for aesthetic pairing ("Inter for headings, Lora for body — clean sans-serif meets elegant serif") but does not define the type scale: which sizes, which weights, which line heights for each level of the hierarchy (h1-h6, body, caption, label, overline).
**Why:** Font pairing articles focus on the aesthetic combination. The model stops at "pick two fonts that look good together" without building the complete type system that makes them functional. A type scale is less visually interesting to describe than a font pairing, so it is underrepresented in training data.
**Example:**
```
STYLE-04: Typography
Heading font: Space Grotesk (geometric sans-serif, modern feel)
Body font: Source Serif 4 (readable serif, professional)
These fonts create a sophisticated contrast between headings and body.
```
(no sizes, no weights, no line-heights, no scale ratio defined)
**Instead:** Define the complete type system: scale ratio (e.g., 1.25 major third), resulting sizes for each heading level (h1: 36px, h2: 28px, h3: 22px, h4: 18px), body text size and line height (16px / 1.5), weight assignments (headings: 600, body: 400, emphasis: 500), and small text / caption sizes (14px, 12px). The font pairing is just one input — the hierarchy system is what makes typography functional.

### STYLE-AP-05: Inaccessible Color Choices
**Mistake:** Picks aesthetically pleasing colors that fail WCAG AA contrast requirements. Light pastels for text on white backgrounds, or medium grays for body text, or colored text on colored backgrounds without checking the computed ratio.
**Why:** The model selects colors based on aesthetic harmony (complementary hues, pleasing saturation) without computing the contrast ratio against the background. It does not have visual perception — it cannot "see" that `#94A3B8` on `#F8FAFC` is hard to read, even though the hex values look different.
**Example:**
```
STYLE-05: Text Colors
Body text: #94A3B8 (slate-400, soft and modern)
Background: #F8FAFC (slate-50, clean white)
```
(contrast ratio: 2.8:1 — fails WCAG AA minimum of 4.5:1 for normal text)
**Instead:** For every text-on-background combination, compute the WCAG contrast ratio and include it in the decision. Body text must meet 4.5:1 (AA) or 7:1 (AAA). Large text (18px+ or 14px+ bold) must meet 3:1. Present the values: "Body text: #475569 on #F8FAFC — contrast ratio 7.2:1 (passes AAA)." Use a contrast checker tool during the specialist session. Reject any color pairing below AA.

---

## B. Responsiveness & Layout

### STYLE-AP-06: Desktop-First Design
**Mistake:** Designs complete desktop layouts with multi-column grids, wide tables, and horizontal navigation, then retrofits mobile breakpoints by stacking columns and hiding sidebars. The mobile version feels like a damaged desktop rather than a designed mobile experience.
**Why:** Desktop layouts are more visually impressive and generate more detailed design discussion. Training data contains more desktop mockups and layout descriptions than mobile-first design discussions. The model defaults to thinking about the largest canvas first.
**Example:**
```
STYLE-06: Dashboard Layout
3-column layout: left sidebar (250px) + main content (fluid) + right panel (300px).
Mobile: stack everything vertically, hide right panel, collapse sidebar to hamburger.
```
**Instead:** Design mobile first. Start with the single-column layout that works on a 375px screen. Define what information is essential at that size, what is secondary (revealed on tap or scroll), and what is supplementary (only shown at larger sizes). Then add layout features for progressively larger breakpoints: 768px (tablet: 2 columns), 1024px (desktop: sidebar + content), 1440px (wide desktop: 3 columns). Present mobile wireframes alongside desktop — the mobile design should feel intentional, not derived.

### STYLE-AP-07: Fixed Widths
**Mistake:** Specifies pixel widths for layout containers, cards, sidebars, and content areas. The design breaks at any viewport width that was not explicitly considered.
**Why:** Pixel values are concrete and unambiguous — the model can state "sidebar: 280px" with confidence. Fluid units (%, fr, rem, clamp()) require understanding the responsive context, which is harder to describe in text-only decisions.
**Example:**
```
STYLE-07: Card Grid
Cards: 350px wide, 3 per row.
Container: 1200px centered.
Sidebar: 280px fixed.
```
(at 1100px viewport, 3 cards at 350px = 1050px + gaps overflow the container)
**Instead:** Use fluid and responsive units. Cards: `minmax(300px, 1fr)` in a CSS Grid auto-fill. Container: `max-width: 1200px; width: 100%; padding: 0 1rem`. Sidebar: `min-width: 240px; max-width: 300px; flex-shrink: 0`. Define sizes as ranges and constraints rather than fixed values. Use `clamp()` for font sizes and spacing that should scale with viewport.

### STYLE-AP-08: Single Breakpoint
**Mistake:** Defines only two layouts — "desktop" (>768px) and "mobile" (<768px) — without considering tablet, small desktop, or ultrawide viewports. The design jumps abruptly at 768px with no intermediate states.
**Why:** Media query tutorials typically show one breakpoint as an example. The model extrapolates "mobile and desktop" as the complete responsive model. Intermediate sizes (768-1024px tablets, 1024-1280px small laptops) fall through the cracks.
**Example:**
```
STYLE-08: Breakpoints
Mobile: < 768px (single column, stacked layout)
Desktop: >= 768px (multi-column, full layout)
```
(an 800px tablet gets the full desktop layout crammed into a too-narrow viewport)
**Instead:** Define 3-4 breakpoints based on content needs, not device names. Common system: 640px (small), 768px (medium), 1024px (large), 1280px (extra-large). For each breakpoint, describe what changes: navigation style (hamburger vs horizontal), column count, sidebar visibility, content density. Test the design at each breakpoint plus the gaps between them (e.g., 900px — does it look reasonable?).

### STYLE-AP-09: Ignoring Content Variability
**Mistake:** Designs layouts with placeholder content that is always the right length ("John Doe," "Lorem ipsum dolor sit amet," exactly 4 items in a list), without considering what happens with real data: names like "Dr. Bartholomew Winchester III," descriptions that are 3 paragraphs or empty, and lists with 0 or 47 items.
**Why:** Design mockups use idealized content. The model generates designs around the placeholder text it imagines, which is always a convenient length. It does not stress-test the layout with edge-case content because it is designing for the aesthetic ideal.
**Example:**
```
STYLE-09: User Card
Avatar (48px circle) + Name (one line) + Role (one line) + Bio (2 lines max).
3 cards per row, equal height.
```
(real data: a user with no avatar, a 40-character name that wraps, no role, and a 500-word bio)
**Instead:** Define how the design handles content extremes. For every text element: what happens when it is empty (placeholder? hide element?), what happens when it is 2x expected length (truncate with ellipsis? wrap? expand?), what happens when it is a single character? For lists: what happens with 0 items (empty state), 1 item (no grid needed), 100 items (pagination? virtual scroll?). Include these edge cases in the STYLE-NN decision.

---

## C. Component Design

### STYLE-AP-10: Dark Mode as Afterthought
**Mistake:** Designs the complete light theme first, then generates the dark theme by inverting colors or reducing lightness values. The result has poor contrast, muddy colors, and surfaces that look washed out instead of rich.
**Why:** Light themes dominate design training data. Dark mode is treated as a transformation ("just flip the colors") rather than a parallel design system. The model does not understand that dark backgrounds need different color saturation, that text contrast behaves differently on dark surfaces, and that shadows become invisible on dark backgrounds.
**Example:**
```
Light theme:
  Background: #FFFFFF → Dark: #1A1A1A (inverted)
  Text: #1F2937 → Dark: #E5E7EB (inverted)
  Primary: #2563EB → Dark: #2563EB (unchanged)
  Card: #F9FAFB → Dark: #2D2D2D (derived)
  Shadow: rgba(0,0,0,0.1) → Dark: rgba(0,0,0,0.3) (invisible on dark bg)
```
**Instead:** Design the dark theme as a separate color system, not a mathematical inversion. Dark mode surfaces use grays (#121212, #1E1E1E, #2D2D2D) with elevation expressed through lighter surfaces rather than shadows. Colors need higher saturation on dark backgrounds to appear equally vibrant. Text should be slightly off-white (#E0E0E0, not pure #FFFFFF) to reduce eye strain. Define both themes in parallel in the STYLE-NN decision, with contrast ratios computed for both.

### STYLE-AP-11: Missing Interactive States
**Mistake:** Defines the default appearance of buttons, inputs, links, and cards, but not their hover, active, focus, disabled, loading, and error states. The developer invents these states during implementation with no design guidance.
**Why:** Static design deliverables (mockups, tokens, style guides) show default states. Interactive states require describing behavior over time, which is harder to capture in text. The model defines what elements look like, not how they respond to interaction.
**Example:**
```
STYLE-10: Buttons
Primary: bg-blue-600, text-white, rounded-lg, px-4 py-2
Secondary: bg-transparent, text-blue-600, border-blue-600
Tertiary: bg-transparent, text-blue-600, no border
```
(no hover, active, focus, disabled, or loading states defined)
**Instead:** For every interactive component, define all states: Default (base appearance), Hover (what changes on mouse-over — typically slight darkening or shadow), Active/Pressed (what changes during click — typically slight scale or darker shade), Focus (keyboard focus ring style and color), Disabled (reduced opacity or gray out, must still meet 3:1 contrast), Loading (spinner or skeleton replacement), Error (for form elements: border color, icon, message style). Present these as a complete interaction matrix.

### STYLE-AP-12: Animation Without Purpose
**Mistake:** Adds transitions, entrance animations, parallax effects, and scroll-triggered reveals for visual flair without considering: does this animation communicate information? Does it help the user understand state changes? Does it respect users who experience motion sickness?
**Why:** Animation tutorials and showcase sites are visually impressive, generating disproportionate training data engagement. The model treats animation as a quality signal ("polished apps have animations") rather than a communication tool with accessibility implications.
**Example:**
```
STYLE-11: Motion System
Page transitions: 300ms slide-in from right
Card hover: 200ms scale(1.05) + shadow elevation
Scroll: parallax background at 0.5x speed
List items: stagger-fade-in, 100ms delay between items
Modal: 400ms spring animation from center
```
(every interaction is animated; users with vestibular disorders cannot use the app)
**Instead:** Categorize animations by purpose: Functional (loading spinners, progress bars — communicate system state), Transitional (page changes, modal open/close — help users track spatial relationships), Decorative (hover effects, entrance animations — purely aesthetic). Define motion principles: duration range (100-300ms for micro-interactions, 200-500ms for transitions), easing curves, and mandatory `prefers-reduced-motion` handling. For reduced motion: disable decorative animations, simplify transitions to opacity-only, keep functional animations.

### STYLE-AP-13: Design System Too Ambitious for Team
**Mistake:** Proposes a 200-token design system with 50+ components, 8 breakpoints, 12 color shades per hue, 6 elevation levels, and comprehensive theming — for a 2-person team building an MVP that needs to ship in 4 weeks.
**Why:** The model has been trained on design system documentation from companies like Google (Material), Salesforce (Lightning), and Shopify (Polaris). These systems have dedicated teams of 10+ designers and engineers. The model does not scale the system's ambition to the team's capacity.
**Example:**
```
STYLE-12: Design System Scope
Tokens: 200+ (color, spacing, typography, elevation, motion, opacity, border-radius)
Components: 52 (Button, Input, Select, Checkbox, Radio, Toggle, Slider, DatePicker,
  TimePicker, ColorPicker, Table, DataGrid, Card, Modal, Dialog, Drawer, Tooltip,
  Popover, Toast, Alert, Badge, Tag, Avatar, ...)
Themes: Light, Dark, High-Contrast
Breakpoints: 8 (xs, sm, md, lg, xl, 2xl, 3xl, 4xl)
```
**Instead:** Start with the minimum viable design system: 20-30 tokens (3-5 colors with shades, 6 spacing values, 5 font sizes, 2 border radii, 2 shadows). 8-12 components (the ones the app actually uses in the first milestone). 1 theme (add dark mode in v2 if users request it). 3 breakpoints. Document the system in a way that is easy to extend. A small, consistent system beats a large, partially-implemented one.
