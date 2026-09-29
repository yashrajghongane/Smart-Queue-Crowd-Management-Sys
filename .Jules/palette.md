## 2024-05-20 - Form Label & ARIA Accessibility
**Learning:** Missing `for` attributes on labels and `aria-label` attributes on icon-only buttons or placeholder-only inputs are common accessibility oversights that prevent screen readers from properly interpreting form elements.
**Action:** Always pair `for` attributes on `<label>` elements with their corresponding input `id`s, and provide explicit `aria-label`s for interactive elements that lack visible text content.
