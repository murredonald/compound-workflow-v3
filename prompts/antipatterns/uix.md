# UIX — Common Mistakes & Anti-Patterns

Common mistakes when running the UIX specialist. Each pattern
describes a failure mode that leads to poor user experience decisions.

**Referenced by:** `specialist_uix.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Usability

### UIX-AP-01: Modal overuse
**Mistake:** Every action triggers a confirmation modal: "Are you sure you want to delete?" "Are you sure you want to save?" "Are you sure you want to navigate away?" Modals interrupt user flow and train users to click "Confirm" reflexively without reading.
**Why:** LLMs associate modals with "safe UX" because confirmation dialogs are documented as a way to prevent destructive actions. The model applies this pattern universally rather than reserving it for genuinely irreversible operations.
**Example:**
```
User flow: Edit profile
1. User changes display name → clicks Save
2. Modal: "Are you sure you want to save these changes?" [Cancel] [Save]
3. User clicks Save
4. Modal: "Changes saved successfully!" [OK]
5. User clicks OK

Three clicks for one save. Two modals for a non-destructive operation.
```
(Saving a display name is easily reversible. Neither modal adds value.)
**Instead:** Reserve modals for genuinely destructive, irreversible actions (deleting an account, cancelling a paid subscription, publishing to production). For reversible actions: save immediately with an undo toast ("Display name updated. [Undo]"). For confirmations: use inline state changes (button text changes to "Saved" with a checkmark for 2 seconds). Rule: if the action can be undone, do not use a modal.

### UIX-AP-02: Error messages that blame the user
**Mistake:** Error messages state the problem without explaining what is wrong, why, or how to fix it. "Invalid input," "Request failed," "Something went wrong" leave the user stranded with no actionable information.
**Why:** LLMs generate error messages by labeling the error state, not by empathizing with the user's confusion. The model thinks "Invalid email" is a sufficient message because it identifies the issue. It does not consider that the user is now wondering: "What is wrong with my email? It looks fine to me."
**Example:**
```
Form errors displayed:
  Email: "Invalid format"
  Phone: "Invalid input"
  ZIP: "Error"
  File: "Upload failed"
```
(User sees four red messages and has no idea what to fix. Their email has a space at the end. Their phone has dashes. Their ZIP is missing a digit. The file was too large.)
**Instead:** Error messages must answer three questions — what happened, why, and what to do: "Email: Remove the space at the end of your email address. Phone: Enter a 10-digit phone number without dashes (e.g., 5551234567). ZIP code: Enter a 5-digit ZIP code (you entered 4 digits). File: Your file is 12MB. Maximum size is 10MB — try compressing the image or choosing a smaller file."

### UIX-AP-03: Form design by database
**Mistake:** Form fields mirror database columns directly. Users see `created_at`, `updated_at`, `user_id` as form labels. Required fields are determined by database NOT NULL constraints rather than by what the user needs to accomplish the task.
**Why:** LLMs generate forms by reading the data model. Each database column maps to a form field. The model does not distinguish between data the system needs (foreign keys, timestamps) and data the user provides (name, email). Code generation patterns reinforce this: scaffold tools create forms from models.
**Example:**
```
Create Account Form:
  - user_id: [auto-generated, shown but disabled]
  - first_name: [text input]
  - last_name: [text input]
  - email: [text input]
  - password_hash: [text input]  ← should be "password" with masking
  - role_id: [dropdown with IDs]  ← should be role names
  - created_at: [datetime picker] ← should not exist
  - updated_at: [datetime picker] ← should not exist
  - is_active: [checkbox]         ← should default to true, not shown
```
(The form exposes internal implementation. Users should never see `password_hash`, `user_id`, `created_at`, or `is_active` on a registration form.)
**Instead:** Design forms from the user's perspective: "What information does the user have? What is the user trying to accomplish? What can be inferred or defaulted?" A registration form needs: name, email, password (with confirmation). Everything else is either auto-generated (ID, timestamps, status) or deferred (role assigned by admin, profile details added later). Labels use human language ("Full name" not "first_name + last_name").

### UIX-AP-04: Navigation depth over breadth
**Mistake:** Features are buried 3-5 clicks deep in nested menus. Common actions require navigating through Settings > Account > Security > Two-Factor > Setup. The information architecture optimizes for categorization neatness rather than task completion speed.
**Why:** LLMs organize features hierarchically because hierarchies are the dominant pattern in training data (file systems, org charts, documentation sites). Deep hierarchies feel "organized" to the model. The model does not simulate a user repeatedly navigating 4 levels to reach a feature they use daily.
**Example:**
```
To change notification preferences:
  Dashboard → Settings → Account → Preferences → Notifications → Email Notifications → Edit

7 navigation steps. Users give up and live with default notifications.
```
(Notification settings are something users configure once but look for repeatedly when they get annoyed by emails.)
**Instead:** Flatten navigation based on usage frequency: "Primary navigation: features used daily (dashboard, main workflow, recent items). Secondary navigation: features used weekly (settings, reports). Settings page: flat list of categories, not nested hierarchy. Maximum depth: 3 clicks from any page to any feature. Shortcut: common settings accessible from the user menu dropdown (notifications, theme, account) without entering the full settings hierarchy."

### UIX-AP-05: Onboarding as documentation dump
**Mistake:** First-time users are greeted with a 7-10 step tutorial wizard or a series of tooltip popups pointing at every UI element. Users click "Next" without reading, dismiss the tutorial, and are left with no guidance when they actually need it.
**Why:** LLMs equate "onboarding" with "tour the interface." Training data includes many onboarding flows that walk through features. The model does not realize that users do not learn by being told — they learn by doing.
**Example:**
```
Step 1 of 10: "Welcome! This is your Dashboard. Here you can see..."
Step 2 of 10: "The sidebar contains your navigation. Click here to..."
Step 3 of 10: "This button creates a new project. You can..."
...
Step 10 of 10: "You're all set! Enjoy using the app."

User retention after tutorial: clicks through without reading, immediately
asks "how do I create a project?" because they forgot step 3.
```
(10 steps of information with zero context. The user has not tried to do anything yet.)
**Instead:** Progressive disclosure: teach features when the user encounters them. "Empty state onboarding: when the dashboard is empty, show a single call-to-action ('Create your first project') with a brief explanation. Contextual hints: when a user hovers over an unfamiliar icon for the first time, show a tooltip. First-use guidance: the first time a user opens a feature, show a brief (1-2 sentence) inline guide, then never again. Help accessible on demand: searchable help panel or command palette (Cmd+K), not forced tours."

---

## B. Accessibility

### UIX-AP-06: Keyboard navigation ignored
**Mistake:** All user flows are designed and tested with mouse interaction only. Tab order is illogical (jumps between sidebar and content area), focus is not managed when modals open/close, and custom components (dropdowns, date pickers, sliders) are not keyboard-operable.
**Why:** LLMs design visual layouts, not interaction models. Keyboard navigation is an invisible layer that does not appear in mockups, wireframes, or component descriptions. The model generates visual designs that look correct but are functionally inaccessible.
**Example:**
```
UIX-14: Custom dropdown component
  - Click to open menu
  - Click option to select
  - Click outside to close

Missing:
  - Enter/Space to open
  - Arrow keys to navigate options
  - Enter to select
  - Escape to close
  - Tab to move to next element after selection
  - Focus visible state on each option
```
(A keyboard-only user cannot use the dropdown at all.)
**Instead:** Every interactive component must define keyboard behavior: "Dropdowns: Enter/Space to open, Arrow Up/Down to navigate, Enter to select, Escape to close, Tab to exit. Modals: focus trapped inside modal, Escape to close, focus returns to trigger element on close. Tab order: follows visual reading order (left-to-right, top-to-bottom). Skip link: first focusable element is 'Skip to main content.' All custom components tested with keyboard-only navigation before approval."

### UIX-AP-07: Color as sole indicator
**Mistake:** Uses color alone to communicate state: red text for errors, green for success, orange for warnings, blue for links. No accompanying icons, text labels, or patterns. Approximately 8% of men and 0.5% of women have color vision deficiency — they cannot distinguish these states.
**Why:** LLMs describe visual design using color because color is the simplest differentiator to specify in text. Icons and patterns require additional design decisions the model would need to specify. "Show errors in red" is a shorter, simpler instruction than "show errors with a red background, a warning icon, and the text 'Error:' as a prefix."
**Example:**
```
Form validation states:
  - Valid: green border
  - Invalid: red border
  - Warning: orange border
  - Neutral: gray border

Status indicators:
  - Active: green dot
  - Inactive: red dot
  - Pending: yellow dot
```
(A user with deuteranomaly cannot distinguish green from red. All three states look identical.)
**Instead:** Color + icon + text, always: "Valid: green border + checkmark icon. Invalid: red border + X icon + error message text. Warning: orange border + triangle icon + warning message text. Status: 'Active' label (green), 'Inactive' label (red), 'Pending' label (yellow). Rule: remove all color from the interface and verify that every state is still distinguishable by shape, icon, or text alone."

### UIX-AP-08: Touch targets too small
**Mistake:** Interactive elements (buttons, links, checkboxes, icons) are smaller than 44x44px on mobile. Users tap and miss, hitting adjacent elements or triggering no action. Particularly problematic for table row actions, close buttons, and icon-only buttons.
**Why:** LLMs design at desktop scale where a mouse cursor provides pixel-precise targeting. The model does not account for finger size (average tap area ~45px) or the imprecision of mobile touch interaction.
**Example:**
```
Mobile action buttons in a table row:
  [Edit] [Delete] [Share]    ← each button is 24x24px with 4px gap

Close button on modal:        ← 16x16px "X" in the corner

Pagination:
  [<] [1] [2] [3] [4] [>]   ← each number is 20x20px
```
(Users trying to tap "Edit" hit "Delete" instead because the targets are 24px wide with 4px gaps.)
**Instead:** Minimum touch target: 44x44px (WCAG 2.5.8 / Apple HIG). Minimum spacing between targets: 8px. "Table row actions: use a single overflow menu (...) icon at 44x44px that expands to show Edit/Delete/Share in a dropdown with 48px row height. Close button: 44x44px tap area (the visible X can be smaller, but the tappable area must be at least 44x44px using padding). Pagination: 44x44px per page number, or replace with 'Load more' / infinite scroll on mobile."

### UIX-AP-09: Missing alt text strategy
**Mistake:** Either no alt text at all (screen readers announce "image" or the filename) or excessively verbose alt text that describes visual details instead of conveying purpose ("image of a round blue button with white text that says Submit on a gray background").
**Why:** LLMs either skip alt text entirely (it is not visible in the UI) or over-describe because the model tries to "translate" the visual into text. Neither approach serves screen reader users, who need to know the image's purpose in context — not what it looks like.
**Example:**
```html
<!-- No alt text -->
<img src="check-circle.svg">

<!-- Over-described -->
<img src="check-circle.svg" alt="A green circle with a white checkmark
    icon inside it, indicating that the operation completed successfully,
    rendered as an SVG image at 24 by 24 pixels">

<!-- Filename as alt -->
<img src="hero-banner-2024-q3-campaign.jpg" alt="hero-banner-2024-q3-campaign">
```
(Screen reader announces: "image" / a 30-word description of a checkmark / "hero-banner-2024-q3-campaign".)
**Instead:** Alt text conveys purpose, not appearance: "Decorative images (icons next to text labels): `alt=\"\"` (empty — screen reader skips it, the text label provides meaning). Functional images (icons as buttons): `alt=\"Mark as complete\"` (the action, not the visual). Content images (photos, charts): `alt=\"Q3 revenue grew 15% over Q2\"` (the insight, not the visual description). Rule: read the alt text without seeing the image — does it convey what the user needs to know?"

### UIX-AP-10: ARIA overuse
**Mistake:** Adds `aria-label`, `role`, and `tabindex` to elements that already have semantic meaning through native HTML. Over-specified ARIA confuses assistive technology more than missing ARIA because the custom attributes override the native behavior.
**Why:** LLMs learn that "ARIA improves accessibility" and apply it as a general rule. The model does not internalize the first rule of ARIA: "If you can use a native HTML element with the semantics and behavior you require already built in, do so instead of adding ARIA."
**Example:**
```html
<!-- Over-ARIA'd: native button already has button role -->
<button role="button" aria-label="Submit" tabindex="0">
  Submit
</button>

<!-- Over-ARIA'd: native nav already has navigation role -->
<nav role="navigation" aria-label="Main navigation">
  <a href="/" role="link" tabindex="0">Home</a>
</nav>
```
(`<button>` already has `role="button"` and `tabindex="0"` by default. Adding them explicitly does nothing. `aria-label="Submit"` overrides the visible text, creating a disconnect if the visible text changes.)
**Instead:** Use native HTML first, ARIA only for gaps: "`<button>` instead of `<div role=\"button\" tabindex=\"0\">`. `<nav>` instead of `<div role=\"navigation\">`. `<input type=\"checkbox\">` instead of `<div role=\"checkbox\" aria-checked=\"true\">`. Add ARIA only when: native HTML cannot express the pattern (tabs, tree views, live regions), or when additional context is needed (`aria-describedby` to link an input to its help text, `aria-live` for dynamic content updates)."

---

## C. Mobile & Responsive

### UIX-AP-11: Desktop flow on mobile
**Mistake:** Ships the same multi-column layout, hover-dependent interactions, and dense data tables on a 375px mobile screen. Content overflows, horizontal scrolling appears, hover menus are unreachable, and data tables require side-scrolling to see all columns.
**Why:** LLMs design layouts as component hierarchies without simulating them at different viewport sizes. The model specifies "3-column layout" and does not consider what happens when those columns collapse to a phone screen. Responsive design requires explicit breakpoint decisions the model does not make by default.
**Example:**
```
Desktop dashboard: 3-column layout
  [Sidebar 250px] [Main content 600px] [Right panel 300px]

On mobile (375px): all three columns render at specified widths
  → horizontal scroll to see right panel
  → sidebar covers 67% of screen
  → data table with 8 columns scrolls horizontally
```
(The mobile experience is the desktop experience with a smaller viewport. Nothing was redesigned.)
**Instead:** Design mobile-first, then expand for desktop: "Mobile (375px): single column, bottom navigation bar, cards instead of table rows, swipe actions instead of hover menus. Tablet (768px): two columns, sidebar collapses to hamburger menu. Desktop (1024px+): full layout with sidebar, multi-column content, hover interactions. Data tables on mobile: priority columns only (name, status, date), expand row for details, or use card layout. Define responsive behavior for every component in the design system."

### UIX-AP-12: Infinite scroll without escape
**Mistake:** Implements infinite scroll with no way to reach the footer, no URL-based pagination for sharing or bookmarking, no "back to top" button, and no position indicator. The user scrolls through 500 items, accidentally refreshes, and starts from the top.
**Why:** Infinite scroll appears modern and user-friendly in training data. LLMs recommend it as the default pagination pattern without considering the edge cases: footer content is unreachable, browser back button breaks, scroll position is lost on refresh, and users cannot share a specific page of results.
**Example:**
```
Product listing page:
  - Infinite scroll loads 20 items at a time
  - Footer contains: Terms of Service, Contact, About
  - No page numbers in URL
  - No "back to top" button
  - No scroll position indicator

User scrolls to item #200, clicks a product, clicks browser Back:
  → returns to top of list, must scroll through 200 items again
```
(The footer is permanently unreachable because new items load before the user can scroll to it.)
**Instead:** Paginated scroll with escape hatches: "Load-more button (not auto-scroll) as default. URL includes page parameter (`?page=5`) for sharing and bookmarking. 'Back to top' button appears after scrolling past 2 viewport heights. Scroll position indicator ('Showing 41-60 of 1,234'). Footer moved above the infinite scroll area, or accessible via a fixed footer link. If true infinite scroll is chosen: virtual scrolling to maintain performance, URL updates as user scrolls, and position is restored on back navigation via session storage."

### UIX-AP-13: No offline/slow connection handling
**Mistake:** The application shows a blank white screen, a perpetual spinner, or an unhandled JavaScript error when the network connection is slow or unavailable. No cached content, no loading skeletons, no offline indicator.
**Why:** LLMs design for the happy path where API calls succeed instantly. Network failure states are not part of the visual design process — they are edge cases that require explicit error state design. The model generates component trees that assume data is always available.
**Example:**
```
Network goes offline:
  Dashboard: blank white screen
  Form submission: spinner that never stops
  Data table: "undefined is not an object" error in console
  Navigation: links fail silently, user thinks app is frozen
```
(The user has no idea if their connection is down, the server is down, or the app is broken.)
**Instead:** Design offline states explicitly: "Network indicator: banner at the top ('You are offline. Some features may be unavailable.'). Cached content: show last-loaded data with a 'Last updated 5 minutes ago' timestamp. Loading states: skeleton screens (not spinners) while data loads, with timeout (after 10 seconds, show 'Taking longer than expected. Check your connection.'). Form submission: queue submissions locally, sync when connection returns, show pending state ('Your changes will be saved when you reconnect.'). Graceful degradation: read-only mode offline, full functionality online."

---

## D. Feedback & States

### UIX-AP-14: No loading state design
**Mistake:** Buttons have no loading state after click. Forms show no indication that a submission is being processed. Users click multiple times because there is no visual feedback that anything is happening, creating duplicate submissions, duplicate API calls, and confused users.
**Why:** LLMs design static states (default, hover, active) but often skip transitional states (loading, processing). Loading states require coordinating button text, disabled state, and spinner — three changes for a single interaction — which the model does not always produce.
**Example:**
```
Submit button behavior:
  1. User clicks "Submit"
  2. Button still says "Submit" and is still clickable
  3. User waits 2 seconds, nothing visible happens
  4. User clicks again → second API call
  5. First request completes → page updates
  6. Second request completes → duplicate entry created
```
(No loading state, no disable-on-click, no visual feedback. Duplicate submissions are the user's fault in this design.)
**Instead:** Define loading behavior for every interactive element: "Button: on click, immediately disable + change text to 'Submitting...' with spinner icon. Re-enable on success or error. Forms: overlay the form with a translucent loading state or disable all inputs during submission. Page transitions: show a progress bar at the top of the viewport (like YouTube/GitHub). Data loads: skeleton screens matching the shape of the expected content. Long operations (>5 seconds): show progress percentage or step indicator ('Processing payment... Step 2 of 3')."

### UIX-AP-15: Success without confirmation
**Mistake:** An action completes successfully but nothing in the UI changes to confirm it. The user clicks "Save," the button briefly disables and re-enables, but there is no toast, no banner, no text change, and no visual indication that the save worked. The user saves again "just in case."
**Why:** LLMs focus on the action (call the API, update the state) and do not consistently generate the feedback UI. Success is an "end state" in the model's reasoning — the task is done, so the output stops. But from the user's perspective, the task is not done until they know it worked.
**Example:**
```
User flow: Update email address
  1. User types new email in settings
  2. User clicks "Update"
  3. Button briefly shows loading state
  4. Button returns to "Update"
  5. ...that's it. Did it work? User checks email field — same value.
     Maybe it saved? User refreshes page to verify. Email is updated.
     But they had to refresh to confirm.
```
(The action succeeded. The user has no idea.)
**Instead:** Every user action must produce visible confirmation: "Saves: toast notification ('Email updated successfully') that auto-dismisses after 5 seconds with a dismiss button. Alternatively, inline confirmation (the field briefly highlights green with a checkmark). Deletes: item animates out of the list + toast with undo option. Form submissions: redirect to success state or clear the form + show confirmation message. File uploads: progress indicator during upload + 'Upload complete' with file name/size. Rule: if you cannot point to the visual element that tells the user 'it worked,' the flow is incomplete."

---

## E. Component Affordance & Visual States

LLM-generated components commonly lack visual affordance — users can't tell what's clickable, what's a form field, or what state something is in. These are implementation-level patterns to catch during review.

### UIX-AP-16: Invisible Buttons
**Mistake:** Buttons have no background, no border, and no distinct color — they look identical to surrounding text. Users don't know they can click.
**Why:** LLMs apply "ghost button" styling (`background: transparent; border: none`) to primary actions for a "clean" aesthetic without realizing the button disappears visually.
**Detect:** Check button `background-color` vs page background. Flag if identical and no visible border or shadow. **Severity: MAJOR.**
**Prevent:** Every button must differ from its background by color, border, or shadow. Ghost buttons are acceptable only for tertiary actions with an accompanying text label.

### UIX-AP-17: Borderless Form Inputs
**Mistake:** Form inputs have no visible border, shadow, or background distinction — invisible fields on the page. Users can't tell where to type.
**Why:** LLMs apply `border: none` for a "modern" look, relying on the focus ring to reveal inputs. But users need to find the input before they can focus it.
**Detect:** Check `border-width`, `outline`, `box-shadow` on form elements at rest (not focused). Flag if all are 0/none with no distinct background. **Severity: MAJOR.**
**Prevent:** Form inputs must have a visible boundary at rest: `border >= 1px` OR `box-shadow` OR distinct background color from the container.

### UIX-AP-18: Missing Hover/Focus States
**Mistake:** Interactive elements show no visual change on hover or keyboard focus — zero interaction feedback. Users don't know if a click registered or which element has focus.
**Why:** LLMs define only the default state. `:hover`, `:focus-visible`, and `:active` styles are omitted because the model generates appearance, not behavior.
**Detect:** Programmatically hover/focus elements, compare computed styles before vs after. Flag if no change. **Severity: MAJOR.**
**Prevent:** All interactive elements need: hover state (subtle color/shadow change), focus-visible state (visible ring or outline), active state (slight press effect). Never apply `outline: none` without a replacement.

### UIX-AP-19: Placeholder-as-Label
**Mistake:** Form inputs use only placeholder text as labels. When the user focuses the field and starts typing, the label disappears — they forget what the field is for.
**Why:** LLMs use placeholders to save vertical space. In training data, placeholders appear in many form examples as the only label.
**Detect:** Check `<input>` elements without associated `<label>` or `aria-label`. **Severity: MAJOR.**
**Prevent:** Every input must have a persistent visible label (above or beside the field). Placeholders are supplementary hints ("e.g., john@example.com"), not replacements for labels.

### UIX-AP-20: Blank Empty States
**Mistake:** When no data exists, the container shows blank white space — no message, no illustration, no call-to-action. The user thinks the page is broken.
**Why:** LLMs implement the "data exists" rendering path. The empty case is either forgotten or shows an empty `<table>` / `<ul>` with headers but no rows.
**Detect:** Check for containers with no visible child content (empty `<tbody>`, empty `<ul>`, empty `<div>` with no text). **Severity: MINOR.**
**Prevent:** Every data container must have an empty state: a message explaining why it's empty ("No projects yet") and a primary CTA ("Create your first project").

### UIX-AP-21: Hover-Only Disclosure
**Mistake:** Content or controls are only visible on `:hover` — completely inaccessible on touch devices where hover doesn't exist.
**Why:** LLMs use hover-reveal as a space-saving technique (tooltip triggers, action menus on table rows, edit icons that appear on card hover). Training data is desktop-heavy where hover is natural.
**Detect:** At mobile viewport, verify all content/controls are discoverable without hover. Flag `opacity: 0` or `visibility: hidden` elements that only become visible via `:hover` with no touch fallback. **Severity: MAJOR.**
**Prevent:** All hover-revealed controls must have a touch alternative: always-visible icon buttons, long-press menus, or swipe actions. Use `@media (hover: hover)` to scope hover-only styles to devices that support it.

### UIX-AP-22: Dropdown Behind Content
**Mistake:** Dropdown menus render behind sibling elements or overlapping containers because of z-index conflicts or stacking context issues.
**Why:** LLMs don't track z-index across components. Each component gets its own z-index without considering the page-level stacking order.
**Detect:** Open dropdowns/menus, check if visible content is obscured via `elementFromPoint()`. **Severity: MAJOR.**
**Prevent:** Define a z-index scale in the style guide (content: 0, dropdowns: 100, overlays: 200, modals: 300, toasts: 400). All z-index values must come from this scale.
