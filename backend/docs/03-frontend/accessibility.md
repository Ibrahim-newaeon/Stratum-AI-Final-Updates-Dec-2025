# Accessibility (A11y)

## Overview

Stratum AI is built with accessibility in mind, following WCAG 2.1 AA guidelines.

---

## Key Features

### Skip to Content

```tsx
// components/ui/skip-to-content.tsx
import { SkipToContent } from '@/components/ui/skip-to-content'

// In App.tsx
<SkipToContent />
<div id="main-content" role="main">
  {/* Main content */}
</div>
```

Allows keyboard users to skip navigation and jump to main content.

### Focus Management

```tsx
// Auto-focus first input in dialogs
<Dialog>
  <DialogContent>
    <Input autoFocus />
  </DialogContent>
</Dialog>

// Focus trap in modals (built into Radix)
<Dialog>
  {/* Focus is trapped within dialog */}
</Dialog>
```

### Keyboard Navigation

| Key | Action |
|-----|--------|
| Tab | Move focus forward |
| Shift+Tab | Move focus backward |
| Enter/Space | Activate button |
| Escape | Close dialog/dropdown |
| Arrow keys | Navigate menu items |

---

## Semantic HTML

### Landmarks

```tsx
<header role="banner">
  <nav aria-label="Main navigation">...</nav>
</header>

<main role="main" id="main-content">
  <article>...</article>
</main>

<aside role="complementary">
  <nav aria-label="Sidebar navigation">...</nav>
</aside>

<footer role="contentinfo">...</footer>
```

### Headings

```tsx
// Proper heading hierarchy
<h1>Page Title</h1>
  <h2>Section</h2>
    <h3>Subsection</h3>
  <h2>Another Section</h2>
```

---

## ARIA Attributes

### Labels

```tsx
// Accessible button
<button aria-label="Close dialog">
  <XIcon aria-hidden="true" />
</button>

// Form labels
<label htmlFor="email">Email</label>
<input id="email" type="email" />

// Or using aria-label
<input aria-label="Search campaigns" type="search" />
```

### Live Regions

```tsx
// Announce dynamic content
<div aria-live="polite" aria-atomic="true">
  {loading ? 'Loading...' : 'Data loaded'}
</div>

// For urgent messages
<div role="alert" aria-live="assertive">
  Error: Invalid input
</div>
```

### States

```tsx
// Expanded state
<button aria-expanded={isOpen} onClick={toggle}>
  Menu
</button>

// Selected state
<li role="option" aria-selected={isSelected}>
  Option 1
</li>

// Disabled state
<button disabled aria-disabled="true">
  Disabled
</button>
```

---

## Component Patterns

### Dialog

```tsx
<Dialog>
  <DialogTrigger asChild>
    <Button>Open Dialog</Button>
  </DialogTrigger>
  <DialogContent
    aria-labelledby="dialog-title"
    aria-describedby="dialog-description"
  >
    <DialogHeader>
      <DialogTitle id="dialog-title">Title</DialogTitle>
      <DialogDescription id="dialog-description">
        Description
      </DialogDescription>
    </DialogHeader>
    {/* Content */}
  </DialogContent>
</Dialog>
```

### Dropdown Menu

```tsx
<DropdownMenu>
  <DropdownMenuTrigger aria-haspopup="menu">
    Actions
  </DropdownMenuTrigger>
  <DropdownMenuContent role="menu">
    <DropdownMenuItem role="menuitem">Edit</DropdownMenuItem>
    <DropdownMenuItem role="menuitem">Delete</DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

### Tabs

```tsx
<Tabs defaultValue="tab1">
  <TabsList role="tablist" aria-label="Dashboard tabs">
    <TabsTrigger value="tab1" role="tab">Overview</TabsTrigger>
    <TabsTrigger value="tab2" role="tab">Analytics</TabsTrigger>
  </TabsList>
  <TabsContent value="tab1" role="tabpanel">
    Overview content
  </TabsContent>
</Tabs>
```

### Table

```tsx
<table role="grid" aria-label="Campaign performance">
  <thead>
    <tr>
      <th scope="col">Name</th>
      <th scope="col">Status</th>
      <th scope="col">Spend</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Campaign A</td>
      <td>Active</td>
      <td>$1,500</td>
    </tr>
  </tbody>
</table>
```

---

## Focus Indicators

```css
/* Custom focus ring */
.focus-visible:focus {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

/* Remove default outline, keep custom */
button:focus {
  outline: none;
}

button:focus-visible {
  ring: 2px solid hsl(var(--ring));
}
```

---

## Color Contrast

All text colors meet WCAG AA contrast requirements:

| Combination | Ratio | Passes |
|-------------|-------|--------|
| text-primary on surface-primary | 16.5:1 | AAA |
| text-secondary on surface-primary | 7.2:1 | AAA |
| text-muted on surface-primary | 4.6:1 | AA |
| primary on surface-primary | 4.5:1 | AA |

---

## Reduced Motion

```css
/* Respect user preference */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

```tsx
// In components
const prefersReducedMotion = window.matchMedia(
  '(prefers-reduced-motion: reduce)'
).matches

<motion.div
  animate={prefersReducedMotion ? {} : { opacity: 1 }}
/>
```

---

## Screen Reader Support

### Hidden Content

```tsx
// Visually hidden but screen reader accessible
<span className="sr-only">Opens in new tab</span>

// Hidden from screen readers
<span aria-hidden="true">🎉</span>
```

### Loading States

```tsx
<div aria-busy={isLoading}>
  {isLoading ? (
    <span aria-live="polite">Loading data...</span>
  ) : (
    <DataTable />
  )}
</div>
```

### Error Messages

```tsx
<div>
  <Input
    aria-invalid={!!error}
    aria-describedby={error ? 'error-message' : undefined}
  />
  {error && (
    <span id="error-message" role="alert">
      {error}
    </span>
  )}
</div>
```

---

## Testing

### Manual Testing Checklist

- [ ] Can navigate entire app with keyboard only
- [ ] Focus order is logical
- [ ] Focus indicators are visible
- [ ] Screen reader announces content correctly
- [ ] ARIA labels are descriptive
- [ ] No keyboard traps
- [ ] Color is not the only indicator
- [ ] Text is resizable to 200%

### Automated Testing

```bash
# Run axe-core accessibility tests
npm run test:a11y

# In Playwright tests
import { injectAxe, checkA11y } from 'axe-playwright'

test('page is accessible', async ({ page }) => {
  await page.goto('/dashboard')
  await injectAxe(page)
  await checkA11y(page)
})
```

---

## RTL Support

```tsx
// App automatically handles RTL
function DocumentDirectionHandler() {
  useDocumentDirection()
  return null
}

// In components
<div className="mr-4 rtl:mr-0 rtl:ml-4">
  Content with RTL-aware spacing
</div>
```

---

## Best Practices

1. **Always provide alt text** for images
2. **Use semantic HTML** elements
3. **Ensure sufficient color contrast**
4. **Make interactive elements keyboard accessible**
5. **Provide clear focus indicators**
6. **Use ARIA only when necessary**
7. **Test with screen readers**
8. **Respect user preferences** (motion, contrast)
