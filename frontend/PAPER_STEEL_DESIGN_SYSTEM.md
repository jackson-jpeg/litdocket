# Paper & Steel Design System
## LitDocket Editorial Legal Utility

**Design Philosophy**: Dense, authoritative, editorial. No "AI slop" or generic SaaS aesthetics.

**North Star**: CompuLaw + Bloomberg Terminal + Editorial Print Design

---

## 1. Typography System

### Font Stack (via next/font)

```typescript
// Authority Font - Editorial headings
font-heading: Playfair Display (serif, editorial)
// Use for: Page titles, section headers, legal citations

// Data/UI Font - Precision
font-sans: Space Grotesk (geometric sans)
// Use for: UI labels, deadlines, case numbers, tables, navigation

// Body Font - Long-form
font-serif: Newsreader (editorial serif)
// Use for: Long-form legal text, document content

// Mono Font - Data precision
font-mono: JetBrains Mono
// Use for: Dates, IDs, statutes, terminal UI, code-like data
```

### Typography Rules

- **Headings**: `font-heading` with `font-bold` or `font-black`
- **UI Labels**: `font-sans` with `uppercase tracking-wide` for authority
- **Data/Numbers**: `font-mono` always
- **Body Text**: `font-serif` for readability
- **No line-height > 1.6**: Legal pros need density

---

## 2. Color Palette

### Canvas Colors

```css
bg-paper     /* #FDFBF7 - Warm paper background */
bg-surface   /* #F5F2EB - Card stock surface */
bg-steel     /* #2C3E50 - Deep charcoal primary */
bg-wax       /* #8B0000 - Sealing-wax crimson accent */
```

### Ink Colors (Typography)

```css
text-ink              /* #1A1A1A - Near black */
text-ink-secondary    /* #4A4A4A - Secondary text */
text-ink-muted        /* #888888 - Muted text */
```

### Deadline Fatality Colors

```css
text-fatal         /* #C0392B - Fatal deadlines (dark crimson) */
text-critical      /* #D35400 - Critical (burnt orange) */
text-important     /* #E67E22 - Important (orange) */
text-standard      /* #2C3E50 - Standard (steel) */
text-informational /* #7F8C8D - Info (graphite) */
```

### Terminal Colors (Command Bar, AI Dock)

```css
bg-terminal-bg       /* #1A1A1A - Terminal background */
text-terminal-text   /* #F5F2EB - Terminal text */
text-terminal-green  /* #27AE60 - Success/prompts */
text-terminal-amber  /* #D35400 - Warnings/loading */
```

### Grid Colors (Data Tables)

```css
border-grid-line   /* #1A1A1A - Hard black lines (1px) */
bg-grid-header     /* #F5F2EB - Card stock header */
bg-grid-zebra      /* #FDFBF7 - Paper zebra stripe */
bg-grid-dark       /* #1A1A1A - Dark container for gap-px grids */
```

---

## 3. Layout Patterns

### ZERO RADIUS POLICY

```typescript
// ALL border-radius values are ZERO
borderRadius: {
  'none': '0',
  'sm': '0',
  'DEFAULT': '0',
  'md': '0',
  'lg': '0',
  'xl': '0',
  '2xl': '0',
  '3xl': '0',
  'full': '0',
}
```

### Hard Borders

- **Always**: `border-ink` (1px solid #1A1A1A)
- **Never**: Soft shadows, blur, `border-slate-200`
- **Accents**: `border-2` or `border-4` for emphasis

### Spacing (Density)

- **Prefer**: `p-4`, `p-6` (dense padding)
- **Avoid**: `p-8`, `p-12` (wasteful whitespace)
- **Tables**: `px-4 py-2` (tight cells)
- **Sections**: `border-b border-ink` instead of margin

---

## 4. Component Patterns

### Tactical Grid (gap-px technique)

For hard 1px grid lines without border collapse issues:

```tsx
<div className="bg-ink p-px">
  <div className="grid grid-cols-5 gap-px bg-ink">
    <div className="bg-surface p-4">Cell 1</div>
    <div className="bg-surface p-4">Cell 2</div>
    {/* gap-px creates hard 1px ink lines */}
  </div>
</div>
```

**Why**: Dark container + gap-px = perfect 1px grid lines

### Data Tables

```tsx
<table className="w-full font-mono text-sm border-collapse">
  <thead className="bg-steel border-b-2 border-ink sticky top-0">
    <tr className="text-terminal-text text-[10px] uppercase tracking-wider">
      <th className="px-4 py-2 border-r border-ink">Type</th>
      <th className="px-4 py-2 border-r border-ink">ID</th>
      <th className="px-4 py-2">Title</th>
    </tr>
  </thead>
  <tbody>
    <tr className="border-b border-ink/30 hover:translate-x-1">
      <td className="px-4 py-2 border-r border-ink/30 font-mono">CASE</td>
      <td className="px-4 py-2 border-r border-ink/30">24-CV-1234</td>
      <td className="px-4 py-2">Smith v. Jones</td>
    </tr>
  </tbody>
</table>
```

**Key traits**:
- Mono font for data
- Hard borders between columns
- Uppercase headers
- Tight padding

### Terminal-Style Command Bar

```tsx
<div className="bg-terminal-bg border-2 border-ink">
  <div className="bg-steel border-b-2 border-ink px-4 py-3">
    <span className="text-terminal-green font-mono">&gt;_</span>
    <input className="bg-transparent text-terminal-text font-mono" />
  </div>
  {/* Results table */}
</div>
```

### Card Pattern (Paper & Steel)

```tsx
<div className="bg-paper border border-ink">
  <div className="p-6 border-b border-ink bg-surface">
    <h3 className="font-heading font-bold text-ink">Section Title</h3>
  </div>
  <div className="p-6">
    {/* Content */}
  </div>
  <div className="p-6 border-t border-ink bg-surface">
    {/* Footer */}
  </div>
</div>
```

---

## 5. Micro-Interactions

### Hard Movement (No Fade)

**Button Hover**:
```css
/* GOOD - Hard translate */
hover:translate-x-1 hover:translate-y-1

/* BAD - Soft fade */
hover:opacity-80
```

**Row Selection**:
```css
/* GOOD - Instant border + translate */
hover:translate-x-1 hover:border-2 hover:border-ink

/* BAD - Background fade */
hover:bg-slate-100 transition-colors
```

### Loading States

**Blinking Cursor** (not spinners):
```tsx
<span className="font-mono">SEARCHING_</span>
```

**Progress Bar** (not circular):
```tsx
<div className="h-1 bg-steel">
  <div className="h-full bg-terminal-green transition-all" style={{width: `${progress}%`}} />
</div>
```

### Keyboard Navigation

- Always visible kbd elements: `<kbd className="px-1.5 py-0.5 border border-terminal-green">↑↓</kbd>`
- Hard selection highlight: `border-l-4 border-terminal-green`
- No soft focus rings

---

## 6. Typography Hierarchy

### Page Structure

```tsx
// Page Title
<h1 className="font-heading text-3xl font-black text-ink">
  Case Management
</h1>

// Section Header
<h2 className="font-heading text-xl font-bold text-ink border-b-2 border-ink pb-2">
  Active Deadlines
</h2>

// Subsection
<h3 className="font-sans text-sm font-bold text-ink-secondary uppercase tracking-wide">
  Fatal Priority
</h3>

// Data Label
<span className="font-mono text-xs text-ink-secondary uppercase">
  Case ID
</span>

// Data Value
<span className="font-mono text-sm font-bold text-ink">
  24-CV-1234
</span>

// Body Text
<p className="font-serif text-base text-ink leading-relaxed">
  Long-form legal content...
</p>
```

---

## 7. Forbidden Patterns

### ❌ Never Use

- `rounded-xl`, `rounded-2xl`, `rounded-lg` → Always `border-radius: 0`
- `shadow-sm`, `shadow-lg`, `shadow-xl` → Use `border` instead
- `bg-white` → Use `bg-paper` or `bg-surface`
- `text-slate-600` → Use semantic `text-ink-secondary`
- `bg-blue-500` → Use `bg-steel` or semantic colors
- `transition-opacity` → Use `transition-transform`
- Spinner SVGs → Use `_` cursor or progress bars
- `Inter`, `Roboto`, `system-ui` → Use Paper & Steel font stack

### ❌ Anti-Patterns

- Centered "marketing" layouts with excessive whitespace
- Soft glassmorphism effects
- Gradient backgrounds
- Purposeless animations
- Generic blue primary colors
- Default Tailwind component styles

---

## 8. Component Checklist

Before shipping a component, verify:

- [ ] Zero border radius on all elements
- [ ] Using Paper & Steel color palette (no `slate-`, `blue-`, `purple-`)
- [ ] Using correct font family (`font-heading`, `font-sans`, `font-mono`, `font-serif`)
- [ ] Hard borders (`border-ink`) instead of soft shadows
- [ ] Dense padding (prefer `p-4` over `p-8`)
- [ ] Uppercase labels with tracking (`uppercase tracking-wide`)
- [ ] Hard hover effects (`translate-x-1`) not opacity fades
- [ ] Mono font for all data/numbers
- [ ] Loading states use `_` cursor or progress bars (not spinners)

---

## 9. Example Components

See reference implementations:
- `/components/DeadlineHeatMap.tsx` - Tactical grid with gap-px
- `/components/GlobalSearch.tsx` - Terminal-style command bar
- `/components/cases/deadlines/DeadlineTable.tsx` - Dense data table
- `/app/layout.tsx` - Typography system setup

---

## 10. Design Tokens Reference

```typescript
// tailwind.config.ts

theme: {
  borderRadius: { /* all set to 0 */ },
  extend: {
    fontFamily: {
      heading: ['var(--font-playfair)', 'Playfair Display', 'Georgia', 'serif'],
      serif: ['var(--font-newsreader)', 'Newsreader', 'Georgia', 'serif'],
      sans: ['var(--font-space-grotesk)', 'Space Grotesk', 'system-ui', 'sans-serif'],
      mono: ['var(--font-jetbrains)', 'JetBrains Mono', 'Consolas', 'monospace'],
    },
    colors: {
      paper: '#FDFBF7',
      surface: '#F5F2EB',
      steel: '#2C3E50',
      wax: '#8B0000',
      ink: {
        DEFAULT: '#1A1A1A',
        secondary: '#4A4A4A',
        muted: '#888888',
      },
      fatal: '#C0392B',
      critical: '#D35400',
      important: '#E67E22',
      standard: '#2C3E50',
      informational: '#7F8C8D',
      terminal: {
        bg: '#1A1A1A',
        text: '#F5F2EB',
        green: '#27AE60',
        amber: '#D35400',
      },
      grid: {
        line: '#1A1A1A',
        header: '#F5F2EB',
        zebra: '#FDFBF7',
        dark: '#1A1A1A',
      },
    },
  },
}
```

---

**Design Authority**: Jackson (Product Owner)
**System Version**: 1.0 (2026-01-16)
**Status**: Production-ready
