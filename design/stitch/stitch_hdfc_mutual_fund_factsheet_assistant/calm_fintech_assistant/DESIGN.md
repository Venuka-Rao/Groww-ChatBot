---
name: Calm Fintech Assistant
colors:
  surface: '#fbf8ff'
  surface-dim: '#d7d8f1'
  surface-bright: '#fbf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f2ff'
  surface-container: '#ececff'
  surface-container-high: '#e5e6ff'
  surface-container-highest: '#dfe1fa'
  on-surface: '#171a2c'
  on-surface-variant: '#3c4a43'
  inverse-surface: '#2c2f42'
  inverse-on-surface: '#f0efff'
  outline: '#6c7a73'
  outline-variant: '#bbcac1'
  surface-tint: '#006c50'
  primary: '#006c50'
  on-primary: '#ffffff'
  primary-container: '#04b488'
  on-primary-container: '#003e2d'
  inverse-primary: '#50ddae'
  secondary: '#386755'
  on-secondary: '#ffffff'
  secondary-container: '#baeed6'
  on-secondary-container: '#3e6d5b'
  tertiary: '#a13d35'
  on-tertiary: '#ffffff'
  tertiary-container: '#f37b6f'
  on-tertiary-container: '#6a1511'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#71fac9'
  primary-fixed-dim: '#50ddae'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#00513c'
  secondary-fixed: '#baeed6'
  secondary-fixed-dim: '#9fd1bb'
  on-secondary-fixed: '#002116'
  on-secondary-fixed-variant: '#1f4f3e'
  tertiary-fixed: '#ffdad6'
  tertiary-fixed-dim: '#ffb4ab'
  on-tertiary-fixed: '#410002'
  on-tertiary-fixed-variant: '#822620'
  background: '#fbf8ff'
  on-background: '#171a2c'
  surface-variant: '#dfe1fa'
  page-bg: '#FFFFFF'
  section-band: '#F0F0F2'
  card-surface: '#F8F8F8'
  border-subtle: '#E9E9EB'
  text-primary: '#44475B'
  text-secondary: '#7C7E8C'
  text-muted: '#A1A3AD'
  notice-bg: '#E9FAF3'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system delivers an intelligent, authoritative, yet approachable financial assistant experience tailored for reviewing mutual fund and investment factsheets (specifically HDFC scheme insights within a clean fintech ecosystem). The aesthetic embodies modern minimalism combined with utilitarian fintech clarity: high-legibility typographic hierarchies, disciplined neutral tones, quiet borders, and intentional emerald-green accents.

The tone is understated, transparent, and trustworthy. Visual distractions such as vibrant gradients, decorative drop-shadows, and multi-colored tagging are strictly eliminated. Instead, structure, precise negative space, and gentle tonal step-downs guide the investor through complex financial disclosures without cognitive fatigue.

## Colors

The palette is strictly restrained to maintain financial precision and eliminate cognitive friction. 

- **Primary Accent (`#04B488`):** The signature fintech green. Reserved exclusively for key interactive touchpoints (primary action buttons, selected states, active radio toggles) and positive key performance indicators.
- **Notice Wash (`#E9FAF3`):** Applied to callout containers, positive validation prompts, and scheme alert highlights.
- **Text Tiers:**
  - `#44475B`: Primary copy, numbers, headers, and values.
  - `#7C7E8C`: Secondary labels, disclaimers, timestamps, and contextual captions.
  - `#A1A3AD`: Faint metric descriptions, inactive placeholders, and table captions.
- **Surfaces & Layout:**
  - `#FFFFFF`: Default canvas background and button text over primary accent.
  - `#F0F0F2`: Horizontal section bands, table header fills, and structural dividers.
  - `#F8F8F8`: Elevated assistant answer cards, scheme metric containers, and nested callout cards.
  - `#E9E9EB`: Uniform 1px hairline borders.

No auxiliary accents (such as blue, orange, purple, or red) or gradient overlays are permitted.

## Typography

The typography relies on Inter for an objective, crystal-clear, and systematic presentation of complex mutual fund data and conversational AI insights.

- **Weight Hierarchy:** Headlines prioritize semi-bold (`600`) to anchor scanning; body text utilizes regular (`400`) for effortless sustained reading; labels and data points use medium (`500`) for structural clarity.
- **Tabular Figures:** When rendering NAV figures, AUM metrics, expense ratios, and historical returns, enforce tabular numeral alignment (`font-variant-numeric: tabular-nums`) to ensure strict vertical data tracking.

## Layout & Spacing

The layout utilizes a structured 12-column fluid grid system on desktop, collapsing to a 4-column system on mobile viewports.

- **Max Content Width:** Constrained to 1200px for balanced readability, centering the assistant feed and scheme facts panel.
- **Rhythm & Safe Margins:** Outer margin sits at 2rem (32px) on desktop screens and compresses gracefully to 1rem (16px) on mobile displays.
- **Section Banding:** Full-width alternating bands (`#F0F0F2`) provide horizontal separation between overview metadata, AI analysis blocks, and risk factor disclosures.
- **Padding:** Internal card padding is strictly uniform: standard cards and assistant query modules leverage `1.5rem` (24px) on desktop and `1rem` (16px) on mobile.

## Elevation & Depth

This design system avoids all heavy, diffused drop shadows. Hierarchy and depth are achieved exclusively through surface-tier shifts and crisp 1px borders.

- **Layer 0 (Canvas):** Base background `#FFFFFF`.
- **Layer 1 (Recessed/Banded Sections):** Band background `#F0F0F2`, seamlessly transitioning full-width bands without border definitions.
- **Layer 2 (Surfaces & Cards):** Cards sit on `#F8F8F8` with a crisp border: `1px solid #E9E9EB`.
- **Layer 3 (Assistant Callout & Highlights):** Answer modules utilize `#FFFFFF` or `#F8F8F8` with `1px solid #E9E9EB` and, optionally, a quiet hairline outline (`outline: 1px solid rgba(4, 180, 136, 0.08)`).
- **Notices & Banners:** Tinted fill `#E9FAF3` with a tonal border `1px solid rgba(4, 180, 136, 0.2)`.

## Shapes

The design system maintains a dual-radius philosophy:
- **Base Components (8px / `rounded-md`):** Buttons, chips, text inputs, search selectors, filter pills, dropdowns, and mini data-points.
- **Assistant Answer Surfaces (16px / `rounded-xl`):** Dedicated assistant prompt outputs, response summary containers, and large modular factsheet review cards.
- **Badges & Micro Status:** Minimalist 4px (`rounded-sm`) for compact statutory tags or NAV badges.

## Components

### Buttons
- **Primary:** Filled `#04B488` background, `#FFFFFF` text, `font-weight: 500`, border-radius 8px. Hover state: `filter: brightness(0.96)`. Active state: `filter: brightness(0.92)`.
- **Secondary / Outlined:** `#FFFFFF` background, `#44475B` text, `1px solid #E9E9EB` border, border-radius 8px. Hover state: `#F8F8F8` surface fill.
- **Ghost:** Transparent background, `#7C7E8C` text. Hover state: `#F0F0F2` background, `#44475B` text.

### Chips & Filters
- **Default:** `#FFFFFF` or `#F8F8F8` background, `1px solid #E9E9EB` border, `#7C7E8C` text, border-radius 8px, padding `6px 12px`.
- **Selected:** `#E9FAF3` background, `1px solid #04B488` border, `#04B488` text, `font-weight: 500`.

### Assistant Answer Card
- Distinct 16px corner radius (`rounded-xl`).
- Background: `#F8F8F8` (or `#FFFFFF` nested inside a `#F0F0F2` band).
- Border: `1px solid #E9E9EB`.
- Header: Displays scheme title with subtle `#7C7E8C` sub-label and an optional `#E9FAF3` badge for verification status.
- Text: Answer body in `#44475B`, secondary citations in `#7C7E8C`.

### Form Fields & Search Inputs
- Background: `#FFFFFF`.
- Border: `1px solid #E9E9EB`, radius 8px, padding `10px 14px`.
- Focus State: `border-color: #04B488`, `outline: 1px solid #04B488`.
- Placeholder: Text color `#A1A3AD`.

### Checkboxes & Radio Buttons
- Unselected: `1px solid #E9E9EB` border, `#FFFFFF` background.
- Selected: `#04B488` background and border, with a clean `#FFFFFF` inner indicator.
- Radius: Radio is fully circular (50%); Checkbox has a 4px corner radius.

### Factsheet Data Tables
- Row dividers: `1px solid #E9E9EB`.
- Headers: `#F0F0F2` background, `#7C7E8C` label-sm text, left/right aligned depending on text or metric.
- Value cells: `#44475B` body-md text with tabular figure alignment.