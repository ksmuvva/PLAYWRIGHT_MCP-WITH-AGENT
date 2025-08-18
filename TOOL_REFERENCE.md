# Playwright MCP Tools Reference

## Common Tool Name Corrections

### ❌ Incorrect → ✅ Correct

**Text Extraction:**
- ❌ `playwright_get_text` → ✅ `playwright_get_visible_text`
- ❌ `playwright_extract_text` → ✅ `playwright_get_visible_text`

**Form Filling:**
- ❌ `playwright_fill(selector, value="text")` → ✅ `playwright_fill(selector, text="text")`
- ❌ `playwright_type` → ✅ `playwright_fill`
- ⚠️  **CRITICAL**: Always use `text` parameter, never `value` parameter!

**Element Interaction:**
- ✅ `playwright_click` - Click elements
- ✅ `playwright_fill` - Fill form fields (use `text` parameter, not `value`)
- ✅ `playwright_press_key` - Press keyboard keys

**Content Extraction:**
- ✅ `playwright_get_visible_text` - Extract visible text from elements
- ✅ `playwright_get_visible_html` - Extract HTML content
- ✅ `playwright_screenshot` - Take screenshots

**Navigation:**
- ✅ `playwright_navigate` - Navigate to URLs
- ✅ `playwright_wait_for_element` - Wait for elements to appear

## Common Selector Patterns

**DuckDuckGo:**
- Search input: `input[name='q']` or `#search_form_input_homepage`
- Search results: `article h2 a` or `[data-testid='result-title-a']`

**General:**
- Form inputs: `input[name='field']`, `#field-id`
- Buttons: `button[type='submit']`, `.btn-class`
- Links: `a[href*='keyword']`, `a:has-text('Link Text')`
