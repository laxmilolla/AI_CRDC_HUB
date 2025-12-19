# Playwright Fill Method Issues & Solutions Report

**Date:** December 18, 2025  
**Research Scope:** Common issues with Playwright's `fill()` method and proven solutions

---

## Executive Summary

Playwright's `fill()` method is designed to input text into form fields by focusing the element and triggering an `input` event. However, numerous users have reported instances where `fill()` fails silently—reporting success but leaving input fields empty. This report documents common causes and proven solutions.

---

## Common Issues Identified

### 1. **Version-Specific Bugs**
- **Issue:** After upgrading to Playwright version 1.53.1, `fill()` method ceased to work correctly
- **Symptom:** Fields remain empty despite `fill()` reporting success
- **Source:** [GitHub Issue #36395](https://github.com/microsoft/playwright/issues/36395)

### 2. **Browser-Specific Issues**
- **Issue:** Firefox-specific protocol errors with `Page.insertText`
- **Symptom:** Error: "Protocol error: Page.insertText"
- **Solution:** Switch to Chromium or WebKit
- **Source:** [Stack Overflow](https://stackoverflow.com/questions/66178835/playwright-fails-to-fill-input)

### 3. **Timing and Visibility Challenges**
- **Issue:** Element not immediately visible or interactable
- **Symptom:** `fill()` executes but field remains empty
- **Cause:** Dynamic content loading, hidden elements, or elements not yet attached to DOM

### 4. **Custom Input Components**
- **Issue:** Modern frameworks (React, Angular, Vue) use custom input components
- **Symptom:** `fill()` doesn't trigger framework event handlers
- **Cause:** Custom components may not respond to standard DOM events

### 5. **Element Focus Requirements**
- **Issue:** Some input fields require explicit focus before accepting input
- **Symptom:** `fill()` reports success but value doesn't appear
- **Cause:** Complex form validation or custom focus handlers

---

## Proven Solutions

### Solution 1: Use `type()` Method Instead of `fill()`

**When to use:** When `fill()` fails but you need character-by-character input simulation

```javascript
// Instead of:
await page.locator('input[name="email"]').fill('user@example.com');

// Use:
await page.locator('input[name="email"]').type('user@example.com');
```

**Pros:**
- Simulates real user typing
- Triggers all keyboard events (keydown, keypress, keyup, input)
- More reliable with custom input components

**Cons:**
- Slower (types character by character)
- May miss characters if typing speed is too fast
- First character may disappear in some cases

**Source:** [Stack Overflow](https://stackoverflow.com/questions/77511942/fill-method-doesnt-work-playwright-python)

---

### Solution 2: Explicit Focus Before Fill

**When to use:** When input fields require focus to accept input

```javascript
const emailInput = page.locator('input[name="email"]');
await emailInput.focus();
await emailInput.fill('user@example.com');
```

**Implementation in our code:**
- ✅ Already implemented in `mcp_client.py` `fill()` method
- Focus is called before fill operation

---

### Solution 3: Clear Field Before Fill

**When to use:** When fields retain previous values or don't accept new input

```javascript
const emailInput = page.locator('input[name="email"]');
await emailInput.clear();
await emailInput.fill('user@example.com');
```

**Implementation in our code:**
- ✅ Already implemented in `mcp_client.py` `fill()` method
- Field is cleared using JavaScript: `el.select(); el.value = '';`

---

### Solution 4: Use JavaScript Evaluation (Direct DOM Manipulation)

**When to use:** As a last resort when standard methods fail

```javascript
await page.evaluate((selector, text) => {
  const el = document.querySelector(selector);
  if (el) {
    el.focus();
    el.value = text;
    // Trigger events to notify framework
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }
}, 'input[name="email"]', 'user@example.com');
```

**Pros:**
- Bypasses Playwright's event system
- Direct DOM manipulation
- Can trigger custom events

**Cons:**
- May not trigger all framework event handlers
- Less "realistic" user simulation
- Requires manual event dispatching

**Source:** [MEPN Nams Blog](https://mepnnams.com/blog/playwright-cannot-click-hidden-element)

---

### Solution 5: Wait for Element Readiness

**When to use:** When elements are dynamically loaded

```javascript
// Wait for element to be visible
await page.locator('input[name="email"]').waitFor({ state: 'visible' });

// Or wait for element to be attached and visible
await page.waitForSelector('input[name="email"]', { state: 'visible' });

// Then fill
await page.locator('input[name="email"]').fill('user@example.com');
```

**Implementation in our code:**
- ✅ Already implemented via `wait_for_element()` method
- Used before fill operations in test execution

---

### Solution 6: Use Robust Locators

**When to use:** To improve test stability and reduce failures

```javascript
// Instead of CSS selector:
await page.locator('input[type="email"]').fill('user@example.com');

// Use role-based locator:
await page.getByRole('textbox', { name: 'Email' }).fill('user@example.com');

// Or label-based:
await page.getByLabel('Email').fill('user@example.com');
```

**Pros:**
- More resilient to UI changes
- Aligns with accessibility standards
- Better test maintainability

**Source:** [Better Stack](https://betterstack.com/community/guides/testing/avoid-flaky-playwright-tests/)

---

### Solution 7: Retry Logic with Verification

**When to use:** When fill operations are intermittently failing

```javascript
async function fillWithRetry(page, selector, text, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    await page.locator(selector).fill(text);
    
    // Verify the value was set
    const value = await page.locator(selector).inputValue();
    if (value === text) {
      return; // Success
    }
    
    // Wait before retry
    await page.waitForTimeout(500 * (i + 1));
  }
  throw new Error(`Failed to fill ${selector} after ${maxRetries} attempts`);
}
```

**Implementation in our code:**
- ✅ Already implemented in `mcp_client.py` `execute_step()` method
- Retries verification up to 3 times with increasing delays

---

### Solution 8: Switch Browser Engine

**When to use:** When issue is browser-specific

```javascript
// If Firefox fails, try Chromium:
const { chromium } = require('playwright');
const browser = await chromium.launch();

// Or WebKit:
const { webkit } = require('playwright');
const browser = await webkit.launch();
```

**Implementation in our code:**
- ✅ Already using Chromium explicitly in MCP server configuration

---

## Recommended Approach for Our System

Based on the research and our current implementation, here's the recommended hybrid approach:

### Current Implementation Status:
1. ✅ **Focus before fill** - Implemented
2. ✅ **Clear field before fill** - Implemented
3. ✅ **Wait for element** - Implemented via `wait_for_element()`
4. ✅ **Retry verification** - Implemented (3 attempts with increasing delays)
5. ✅ **Using Chromium** - Explicitly configured

### Recommended Enhancement:

**Add a fallback to JavaScript-based fill when standard fill fails:**

```python
async def fill(self, selector: str, text: str) -> str:
    """Fill input via MCP bridge with multiple fallback strategies"""
    
    # Strategy 1: Standard fill with focus and clear
    try:
        # Focus and clear (already implemented)
        # ... existing code ...
        
        result = await self._call_bridge("fill", {"selector": selector, "text": text})
        if result.get("success"):
            await asyncio.sleep(0.8)
            
            # Verify the fill worked
            actual_value = await self.evaluate(f"document.querySelector('{escaped_selector}')?.value || ''")
            if actual_value and text in str(actual_value):
                return f"Filled {selector}"
            
            # Strategy 2: If standard fill failed, try JavaScript-based fill
            self.logger.warning(f"Standard fill failed for {selector}, trying JavaScript-based fill")
            return await self._fill_with_javascript(selector, text)
            
    except Exception as e:
        self.logger.warning(f"Fill failed: {e}, trying JavaScript-based fill")
        return await self._fill_with_javascript(selector, text)

async def _fill_with_javascript(self, selector: str, text: str) -> str:
    """Fill input using JavaScript evaluation with event dispatching"""
    escaped_selector = selector.replace("'", "\\'")
    escaped_text = text.replace("'", "\\'").replace("\\", "\\\\")
    
    fill_code = f"""
    (function() {{
        const el = document.querySelector('{escaped_selector}');
        if (el) {{
            el.focus();
            el.value = '{escaped_text}';
            // Trigger events for framework compatibility
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            el.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true }}));
            el.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true }}));
            return true;
        }}
        return false;
    }})()
    """
    
    result = await self.evaluate(fill_code)
    await asyncio.sleep(0.5)
    
    # Verify
    actual_value = await self.evaluate(f"document.querySelector('{escaped_selector}')?.value || ''")
    if actual_value and text in str(actual_value):
        return f"Filled {selector} via JavaScript"
    else:
        raise RuntimeError(f"JavaScript-based fill also failed for {selector}")
```

---

## Best Practices Summary

1. **Always verify after fill** - Check that the value was actually set
2. **Use retry logic** - Implement retries with verification
3. **Focus before fill** - Explicitly focus elements before filling
4. **Clear before fill** - Clear fields to avoid stale values
5. **Wait for readiness** - Ensure elements are visible and interactable
6. **Have fallback strategies** - Use JavaScript-based fill as fallback
7. **Use robust locators** - Prefer role/label-based selectors
8. **Avoid fixed waits** - Use Playwright's auto-waiting when possible
9. **Test across browsers** - Verify behavior in different browser engines
10. **Keep Playwright updated** - Use latest stable version

---

## References

1. [GitHub Issue #36395 - Playwright fill() not working after upgrade](https://github.com/microsoft/playwright/issues/36395)
2. [Stack Overflow - Playwright fails to fill input](https://stackoverflow.com/questions/66178835/playwright-fails-to-fill-input)
3. [Stack Overflow - Fill method doesn't work Playwright Python](https://stackoverflow.com/questions/77511942/fill-method-doesnt-work-playwright-python)
4. [Blog - The Truth About Waiting in Playwright](https://blog.nashtechglobal.com/the-truth-about-waiting-in-playwright/)
5. [Better Stack - Avoid Flaky Playwright Tests](https://betterstack.com/community/guides/testing/avoid-flaky-playwright-tests/)
6. [MEPN Nams - Playwright Cannot Click Hidden Element](https://mepnnams.com/blog/playwright-cannot-click-hidden-element)

---

## Conclusion

The `fill()` method failures are often caused by:
- Timing issues (element not ready)
- Custom input components (React/Angular/Vue)
- Browser-specific bugs
- Missing focus/clear operations

Our current implementation already includes most best practices (focus, clear, retry, verification). The recommended enhancement is to add a JavaScript-based fallback when standard `fill()` fails, which should handle edge cases with custom input components like Google's login page.

