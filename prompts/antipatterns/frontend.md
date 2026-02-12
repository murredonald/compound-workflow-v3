# Frontend — Common Mistakes & Anti-Patterns

Common mistakes when running the frontend specialist. Each pattern
describes a failure mode that leads to poor frontend decisions.

**Referenced by:** `specialist_frontend.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Framework & Dependencies

### FRONT-AP-01: React by Default
**Mistake:** Recommends React (or Next.js) without evaluating whether a simpler framework or even server-rendered HTML would better serve the project's actual needs.
**Why:** React dominates LLM training data. For every "build X with Svelte" article, there are 50 "build X with React" articles. The model's prior probability for "React is the right choice" is artificially high because of this frequency imbalance, not because React is universally optimal.
**Example:**
```
FRONT-01: Framework
Use React 19 with Next.js App Router. React's large ecosystem and
community support make it the obvious choice for any modern web app.
```
(proposed for a documentation site with 20 static pages and a contact form)
**Instead:** Match the framework to the project's interactivity level. Static content sites: Astro, Hugo, or plain HTML + a build tool. Light interactivity (forms, toggles, filters): HTMX, Alpine.js, or Svelte. Rich client-side apps (dashboards, editors, real-time collaboration): React, Vue, or Svelte. State why the chosen framework fits THIS project's interactivity requirements, page count, and SEO needs.

### FRONT-AP-02: Dependency Bloat
**Mistake:** Adds npm packages for functionality that native browser APIs or small utility functions handle. Installs moment.js for date formatting, axios for HTTP requests, lodash for array operations, classnames for conditional CSS classes.
**Why:** The model has seen these libraries used in thousands of code examples and tutorials. It does not check whether the browser has a native equivalent (Intl.DateTimeFormat, fetch, Array.prototype methods, template literals) because the training data was written when these APIs were less mature or less widely known.
**Example:**
```json
{
  "dependencies": {
    "axios": "^1.6.0",
    "moment": "^2.30.0",
    "lodash": "^4.17.0",
    "classnames": "^2.5.0",
    "uuid": "^9.0.0"
  }
}
```
(all five can be replaced with native APIs: fetch, Intl.DateTimeFormat, Array methods, template literals, crypto.randomUUID())
**Instead:** Before recommending any dependency, check if a native browser API covers the use case. For each dependency in the FRONT-NN decisions, state what it provides that native APIs do not. Prefer zero-dependency solutions for simple operations. Reserve npm packages for genuinely complex functionality: rich text editors, chart libraries, animation engines.

### FRONT-AP-03: Component Library Lock-In
**Mistake:** Picks a UI component library (Material UI, Chakra UI, Ant Design) early without checking that it supports all required patterns. Discovers mid-build that the library's table component doesn't support virtual scrolling, or its date picker doesn't handle time zones, and ejecting means rewriting the entire UI.
**Why:** Component libraries are presented in training data as productivity accelerators. The model recommends them for the 80% of components that work well and does not investigate the 20% that require workarounds or ejection.
**Example:**
```
FRONT-03: Component Library
Use Material UI (MUI) v6 for all components. MUI provides a comprehensive
set of pre-built, accessible components that follow Material Design.
```
(project needs a complex data grid with inline editing, cell merging, and virtual scroll — MUI's free DataGrid does not support cell merging)
**Instead:** Audit the project's component needs against the library's capabilities BEFORE recommending it. List the most complex components the project requires (data tables, date/time pickers, rich text editors, drag-and-drop) and verify library support. If the library lacks critical components, state the plan: use the library for standard components and a specialized package for the complex ones, or use a headless UI library (Radix, Headless UI) with custom styling.

### FRONT-AP-04: State Management Overkill
**Mistake:** Installs Redux, Zustand, or Jotai for an application with 3 forms, 2 pages, and no shared global state beyond the current user. Adds reducer boilerplate, store configuration, and provider wrappers for state that could live in component state or URL params.
**Why:** State management libraries feature prominently in "production React" tutorials. The model associates "real application" with "needs a state management library" because that is the pattern in training data. Simple applications that use only useState/useReducer are underrepresented.
**Example:**
```
FRONT-04: State Management
Use Zustand for global state management. Create stores for:
- userStore (current user, auth state)
- uiStore (sidebar open/close, modal state, theme)
- formStore (multi-step form data)
```
(the app has a login page, a dashboard, and a settings page)
**Instead:** Start with the simplest state mechanism that works. URL params for navigation state (current tab, filters, page number). Component state (useState) for form inputs and toggle states. Context for truly global, rarely-changing data (current user, theme). Add a state management library only when you identify specific pain: deeply nested prop passing (3+ levels), state that multiple unrelated components need to read and write, or complex state transitions that benefit from reducer patterns.

---

## B. Performance & Build

### FRONT-AP-05: No Performance Budget
**Mistake:** Never defines a target for initial bundle size, time-to-interactive, or largest contentful paint. Dependencies accumulate unchecked, and the app ships 2MB of JavaScript without anyone noticing.
**Why:** Performance budgets are not part of standard framework tutorials. The model generates feature decisions without weight constraints because training data rarely includes "this decision adds 45KB to the bundle" alongside feature recommendations.
**Example:**
```
FRONT-05: Charting
Use Recharts for data visualization. FRONT-06: Rich Text
Use TipTap for content editing. FRONT-07: Animation
Use Framer Motion for page transitions.
```
(each library is 30-80KB gzipped; combined they add 150KB+ before any application code)
**Instead:** Define a performance budget in an early FRONT-NN decision: "Initial JS bundle must be under 200KB gzipped. Each new dependency must justify its size." For each library recommendation, include its gzipped size and the running total. If the budget is exceeded, prioritize: which libraries are critical path vs nice-to-have? Can any be loaded lazily?

### FRONT-AP-06: Client-Side Rendering Everything
**Mistake:** Builds a Single Page Application for content-heavy sites that need SEO, fast first paint, and accessibility. The user sees a blank white screen with a spinner for 2-3 seconds while JavaScript downloads, parses, and fetches data.
**Why:** SPA architecture is the dominant pattern in React/Vue/Angular tutorials. Server-side rendering and static site generation are presented as advanced topics. The model defaults to client-side rendering because that is the "standard" it has learned, even when the project's content and SEO requirements clearly call for server rendering.
**Example:**
```
FRONT-01: Architecture
Build a client-side SPA with React Router. On first load, show a
loading spinner while fetching page content from the API.
```
(proposed for a marketing site with a blog, pricing page, and documentation)
**Instead:** Choose the rendering strategy based on content type. Static content (blog, docs, marketing pages): SSG (build-time rendering) for instant loads and perfect SEO. Dynamic but SEO-important content (product pages, search results): SSR (server rendering on each request). Highly interactive app content behind auth (dashboards, editors): CSR (client rendering is fine — no SEO needed, users expect a brief load). Many apps need a mix: SSG for marketing pages, SSR for product catalog, CSR for the logged-in dashboard.

### FRONT-AP-07: Premature Code Splitting
**Mistake:** Lazily loads every route and component before measuring whether the total bundle is actually too large. Adds React.lazy() wrappers, Suspense boundaries, and loading states for routes that add 5KB each.
**Why:** Code splitting is presented as a best practice in performance optimization guides. The model applies it preemptively because "it can't hurt," but it adds complexity (loading states, error boundaries, waterfall requests) and can actually hurt perceived performance if the split chunks are small and the round-trip cost exceeds the download savings.
**Example:**
```typescript
const Dashboard = lazy(() => import('./pages/Dashboard'));    // 8KB
const Settings = lazy(() => import('./pages/Settings'));      // 4KB
const Profile = lazy(() => import('./pages/Profile'));        // 3KB
// Total app is 40KB — splitting saves nothing, adds 3 loading states
```
**Instead:** Measure first. Build the app without code splitting. Check the bundle size. If the initial bundle is under 200KB gzipped, code splitting adds complexity without meaningful benefit. If it exceeds the budget, split the largest routes first (typically those with heavy dependencies like charts or editors). Use the webpack-bundle-analyzer or equivalent to identify what actually needs splitting.

### FRONT-AP-08: Missing Loading States
**Mistake:** Designs the happy path (data loaded, components rendered) but no intermediate states. Users see blank white rectangles during data fetches, buttons that freeze during form submissions, and no feedback when operations are in progress.
**Why:** Tutorials and examples show the final rendered state. Loading states are "left as an exercise" or shown as a simple spinner. The model generates the data-present markup without systematically considering what the user sees during the 200ms to 3s gap between navigation and data arrival.
**Example:**
```tsx
function UserProfile({ userId }) {
  const { data } = useFetch(`/api/users/${userId}`);
  return (
    <div>
      <h1>{data.name}</h1>        {/* undefined for ~500ms */}
      <p>{data.bio}</p>            {/* blank until loaded */}
      <img src={data.avatar} />    {/* broken image icon */}
    </div>
  );
}
```
**Instead:** Define loading states as a FRONT-NN decision covering the entire app. Specify: skeleton screens for content-heavy pages (profile, feed, dashboard), inline spinners for button actions (submit, delete), progress bars for multi-step operations (file upload, checkout), and error states with retry actions. Each page design should include 3 states: loading, loaded, and error.

---

## C. Accessibility & UX

### FRONT-AP-09: Div Soup
**Mistake:** Builds the entire UI with `<div>` and `<span>` elements, using click handlers on divs instead of `<button>`, divs instead of `<nav>`, `<main>`, `<article>`, `<section>`. Breaks keyboard navigation, screen readers, and SEO.
**Why:** `<div>` is the most common element in training data because it is the generic container. The model defaults to `<div onclick={...}>` instead of `<button>` because it has seen more examples of the former, especially in styled-components and CSS-in-JS codebases where semantic elements seem unnecessary.
**Example:**
```tsx
<div className="header">
  <div className="nav">
    <div className="nav-item" onClick={() => navigate('/home')}>Home</div>
    <div className="nav-item" onClick={() => navigate('/about')}>About</div>
  </div>
</div>
<div className="main-content">
  <div className="card" onClick={() => openDetail(item)}>
    <div className="card-title">{item.name}</div>
  </div>
</div>
```
**Instead:** Use semantic HTML first, style second. `<header>` + `<nav>` for navigation. `<main>` for primary content. `<button>` for clickable actions. `<a>` for links that navigate. `<article>` for self-contained content. `<section>` for thematic groupings. Semantic HTML is free accessibility, free keyboard navigation, and free SEO. Define this as a FRONT-NN decision: "No interactive `<div>` or `<span>` elements. Use native HTML elements for their intended purpose."

### FRONT-AP-10: Custom Components Replacing Native HTML
**Mistake:** Builds or imports custom components for UI patterns that native HTML handles correctly: custom dropdowns instead of `<select>`, custom checkboxes instead of `<input type="checkbox">`, custom date pickers instead of `<input type="date">`. The custom versions have worse accessibility, more bugs, and are harder to maintain.
**Why:** Custom components look better in screenshots and demos. The model recommends them because training data contains many tutorials building custom form controls "from scratch" as learning exercises. It does not distinguish between learning exercises and production recommendations.
**Example:**
```
FRONT-08: Form Components
Build custom components for all form inputs: CustomSelect with search
and multi-select, CustomDatePicker with range selection, CustomCheckbox
with animated toggle. Use Radix primitives as the base.
```
(the project has a settings page with 5 dropdowns and a date filter)
**Instead:** Start with native HTML elements. Upgrade to custom components only when native behavior is insufficient for a specific requirement. `<select>` fails when you need: search/filter, multi-select with tags, option grouping with custom rendering. `<input type="date">` fails when you need: date ranges, time zone display, blocked date ranges. Document which form controls need custom implementations and why, not as a blanket replacement.

### FRONT-AP-11: Mobile as Afterthought
**Mistake:** Designs the desktop layout first with fixed widths and complex multi-column grids, then adds media queries to make it "work" on mobile by stacking everything vertically. The mobile experience feels like a broken desktop rather than a designed mobile experience.
**Why:** Design mockups in training data are predominantly desktop screenshots. The model generates desktop-first CSS because that is what it has seen most. Mobile-first CSS (starting from the smallest viewport and adding complexity for larger screens) is the recommended approach but is less common in tutorial code.
**Example:**
```css
.dashboard {
  display: grid;
  grid-template-columns: 250px 1fr 300px;
  gap: 24px;
}
@media (max-width: 768px) {
  .dashboard {
    grid-template-columns: 1fr;  /* everything stacks */
  }
  .sidebar { display: none; }   /* just hide the sidebar */
}
```
**Instead:** Define the mobile-first approach as a FRONT-NN decision. Start with the single-column mobile layout as the base CSS. Add complexity (multi-column grids, sidebars, expanded navigation) via `min-width` media queries for larger viewports. This produces cleaner responsive behavior because you add layout features rather than removing them. Critical mobile considerations: touch targets (44px minimum), thumb reach zones, swipe gestures, and reduced information density.

### FRONT-AP-12: Ignoring Keyboard Navigation
**Mistake:** Interactive elements are unreachable via the Tab key. Custom components lack focus management. Modal dialogs do not trap focus. No visible focus indicators on any element because `outline: none` was applied globally.
**Why:** Keyboard navigation is invisible in training data — it does not appear in screenshots or code demos. The model generates visual components without considering the non-visual interaction model. Focus management for modals, dropdowns, and tab panels requires explicit implementation that tutorials often skip.
**Example:**
```css
/* "Clean" reset that breaks keyboard navigation */
*:focus { outline: none; }

/* Custom dropdown with no keyboard support */
function Dropdown({ options }) {
  const [open, setOpen] = useState(false);
  return (
    <div onClick={() => setOpen(!open)}>
      {open && options.map(o => (
        <div onClick={() => select(o)}>{o.label}</div>
      ))}
    </div>
  );
}
```
**Instead:** Define keyboard navigation as a FRONT-NN decision covering: visible focus indicators (`:focus-visible` with a clear ring), tab order that follows visual order, focus trapping in modals and dialogs, arrow key navigation in menus and dropdowns, Escape to close overlays, and Enter/Space to activate buttons. Reference WAI-ARIA Authoring Practices for the interaction patterns of each component type.

---

## D. State & Data

### FRONT-AP-13: Optimistic UI Everywhere
**Mistake:** Shows success state before the server confirms for all operations, including irreversible ones like payments, account deletion, and data exports. If the server rejects the operation, the UI has already shown a success message.
**Why:** Optimistic UI is presented as a best practice for "snappy" interfaces in training data. The model applies it uniformly because it improves perceived performance. It does not distinguish between operations where a rollback is trivial (toggling a like) and operations where a false success is dangerous (charging a credit card).
**Example:**
```typescript
async function deleteAccount() {
  setStatus('deleted');              // optimistic: show "Account deleted"
  showToast('Account deleted');      // user sees success immediately
  try {
    await api.delete('/account');    // actual deletion
  } catch {
    setStatus('active');             // rollback — but user already saw "deleted"
    showToast('Delete failed');      // confusing: "deleted" then "failed"
  }
}
```
**Instead:** Categorize operations by reversibility. Safe for optimistic UI: toggling favorites, marking as read, reordering list items (trivially reversible, low stakes). Unsafe for optimistic UI: payments, deletions, sending messages, publishing content (irreversible or high-stakes). For unsafe operations, show a loading state, wait for server confirmation, then show the result. Define the policy in a FRONT-NN decision.

### FRONT-AP-14: Client-Side Only Validation
**Mistake:** Validates form inputs in the browser but not on the server. The validation is trivially bypassed by anyone who opens the browser dev tools or sends a direct API request.
**Why:** Frontend tutorials focus on client-side UX: showing inline error messages, disabling submit buttons, highlighting invalid fields. Server-side validation is covered by backend tutorials. The model treats them as separate concerns and may only implement the side it is currently focused on.
**Example:**
```tsx
function RegisterForm() {
  const validate = (values) => {
    if (!values.email.includes('@')) return { email: 'Invalid email' };
    if (values.password.length < 8) return { password: 'Too short' };
  };
  // No corresponding server-side validation — curl bypasses everything
}
```
**Instead:** Client-side validation is a UX convenience, not a security measure. The FRONT-NN decision should state: "Client-side validation provides immediate feedback. It DOES NOT replace server-side validation. Every validation rule enforced in the browser MUST also be enforced on the server." Reference the corresponding BACK-NN decision that defines the server-side validation rules. The two should be consistent.

### FRONT-AP-15: Prop Drilling Avoidance at All Costs
**Mistake:** Introduces React Context, Zustand stores, or event buses to avoid passing props 2 levels deep. A component needs `userId` from a grandparent, so a global store is created instead of passing the prop through one intermediate component.
**Why:** "Prop drilling is bad" is a meme in React training data. The model has learned to treat any prop passed through an intermediate component as a code smell, even though 2-3 levels of prop passing is normal, readable, and easier to trace than global state.
**Example:**
```tsx
// "Problem": userId passed through 2 levels
<Page userId={userId}>
  <Sidebar userId={userId}>
    <UserAvatar userId={userId} />

// "Solution": global store to avoid prop passing
const useUserStore = create((set) => ({ userId: null }));
// Now userId is invisible in the component tree — harder to trace, harder to test
```
**Instead:** Prop drilling becomes a problem at 4+ levels or when many unrelated props are threaded through components that don't use them. For 2-3 levels, explicit props are clearer and more maintainable than implicit global state. Define the threshold in a FRONT-NN decision: "Use explicit props for up to 3 levels. Use Context for widely-shared, rarely-changing data (theme, locale, current user). Use a state management library only for complex shared state that multiple unrelated components read and write."
