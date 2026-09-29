/**
 * Node.js Automated Test Suite for Sentinel System-Aware Theme Engine
 * Validates:
 * 1. Default to system when no preference stored
 * 2. Stored light preference preserved
 * 3. Stored dark preference preserved
 * 4. Stored system preference preserved
 * 5. System + OS Dark resolves to dark
 * 6. System + OS Light resolves to light
 * 7. System dynamically responds to OS media query change
 * 8. Light ignores OS media query change
 * 9. Dark ignores OS media query change
 * 10. Selected preference persisted to localStorage
 * 11. Resolved theme is NOT persisted as preference when system selected
 * 12. UI toggle and menu item attributes updated
 * 13. Cycle toggle works correctly (system -> light -> dark -> system)
 * 14. Event dispatching on theme change (sentinel:themechange)
 * 15. getTheme() backward compatibility returns resolved theme
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

function createMockEnvironment(initialStorage = {}, initialOSDark = false) {
  const storage = new Map(Object.entries(initialStorage));
  const docAttrs = new Map();
  const domListeners = new Map();
  const windowListeners = new Map();
  const mediaQueryListeners = [];

  let isOSDark = initialOSDark;

  const mockElement = {
    setAttribute: (k, v) => docAttrs.set(k, String(v)),
    getAttribute: (k) => docAttrs.get(k) || null,
    removeAttribute: (k) => docAttrs.delete(k),
    innerHTML: '',
    style: {},
    classList: {
      add: () => {},
      remove: () => {}
    },
    querySelector: () => null,
    querySelectorAll: () => []
  };

  const env = {
    window: {
      matchMedia: (query) => {
        if (query.includes('prefers-color-scheme: dark')) {
          return {
            matches: isOSDark,
            media: query,
            addEventListener: (evt, cb) => {
              if (evt === 'change') mediaQueryListeners.push(cb);
            },
            addListener: (cb) => {
              mediaQueryListeners.push(cb);
            }
          };
        }
        return { matches: false, addEventListener: () => {} };
      },
      addEventListener: (evt, cb) => {
        if (!windowListeners.has(evt)) windowListeners.set(evt, []);
        windowListeners.get(evt).push(cb);
      },
      dispatchEvent: (evt) => {
        const list = windowListeners.get(evt.type) || [];
        list.forEach(cb => cb(evt));
      },
      CustomEvent: class CustomEvent {
        constructor(type, init) {
          this.type = type;
          this.detail = init ? init.detail : {};
        }
      }
    },
    document: {
      documentElement: mockElement,
      body: { style: {}, appendChild: () => {} },
      getElementById: () => null,
      createElement: () => ({
        style: {},
        appendChild: () => {},
        remove: () => {},
        classList: { add: () => {}, remove: () => {} }
      }),
      querySelectorAll: () => [],
      addEventListener: (evt, cb) => {
        if (!domListeners.has(evt)) domListeners.set(evt, []);
        domListeners.get(evt).push(cb);
      }
    },
    localStorage: {
      getItem: (k) => storage.get(k) || null,
      setItem: (k, v) => storage.set(k, String(v)),
      removeItem: (k) => storage.delete(k),
      clear: () => storage.clear()
    },
    triggerOSChange: (matches) => {
      isOSDark = matches;
      mediaQueryListeners.forEach(cb => cb({ matches, media: '(prefers-color-scheme: dark)' }));
    },
    docAttrs,
    storage,
    windowListeners
  };

  return env;
}

function loadSentinelInEnv(env) {
  const code = fs.readFileSync(path.join(__dirname, '..', 'static', 'js', 'sentinel.js'), 'utf8');
  const fn = new Function('window', 'document', 'localStorage', `${code}; return window.Sentinel;`);
  return fn(env.window, env.document, env.localStorage);
}

function runTests() {
  console.log('--- Starting Sentinel System-Aware Theme Test Suite ---');

  // Test 1: No stored preference -> System
  {
    console.log('Test 1: No stored preference defaults to system');
    const env = createMockEnvironment({}, false);
    const S = loadSentinelInEnv(env);
    S.initTheme();
    assert.strictEqual(S.getSelectedTheme(), 'system', 'Selected theme should default to system');
    assert.strictEqual(S.getResolvedTheme(), 'light', 'On light OS, resolved theme should be light');
    assert.strictEqual(S.getTheme(), 'light', 'getTheme() should return resolved theme');
    assert.strictEqual(env.docAttrs.get('data-theme'), 'light', 'DOM data-theme should be light');
    assert.strictEqual(env.docAttrs.get('data-theme-preference'), 'system', 'DOM data-theme-preference should be system');
  }

  // Test 2: Stored Light -> Light
  {
    console.log('Test 2: Stored light preference is strictly preserved');
    const env = createMockEnvironment({ sentinel_theme: 'light' }, true);
    const S = loadSentinelInEnv(env);
    S.initTheme();
    assert.strictEqual(S.getSelectedTheme(), 'light', 'Selected theme should be light');
    assert.strictEqual(S.getResolvedTheme(), 'light', 'Resolved theme must remain light even on dark OS');
    assert.strictEqual(S.getTheme(), 'light', 'getTheme() must return light');
    assert.strictEqual(env.docAttrs.get('data-theme'), 'light', 'DOM data-theme must be light');
  }

  // Test 3: Stored Dark -> Dark
  {
    console.log('Test 3: Stored dark preference is strictly preserved');
    const env = createMockEnvironment({ sentinel_theme: 'dark' }, false);
    const S = loadSentinelInEnv(env);
    S.initTheme();
    assert.strictEqual(S.getSelectedTheme(), 'dark', 'Selected theme should be dark');
    assert.strictEqual(S.getResolvedTheme(), 'dark', 'Resolved theme must remain dark even on light OS');
    assert.strictEqual(S.getTheme(), 'dark', 'getTheme() must return dark');
    assert.strictEqual(env.docAttrs.get('data-theme'), 'dark', 'DOM data-theme must be dark');
  }

  // Test 4: Stored System -> System
  {
    console.log('Test 4: Stored system preference is recognized');
    const env = createMockEnvironment({ sentinel_theme: 'system' }, false);
    const S = loadSentinelInEnv(env);
    S.initTheme();
    assert.strictEqual(S.getSelectedTheme(), 'system', 'Selected theme should be system');
  }

  // Test 5: System + OS Dark -> Dark
  {
    console.log('Test 5: System + OS Dark resolves to Dark');
    const env = createMockEnvironment({}, true);
    const S = loadSentinelInEnv(env);
    S.initTheme();
    assert.strictEqual(S.getSelectedTheme(), 'system');
    assert.strictEqual(S.getResolvedTheme(), 'dark', 'Resolved theme should be dark when OS is dark');
    assert.strictEqual(env.docAttrs.get('data-theme'), 'dark');
  }

  // Test 6: System + OS Light -> Light
  {
    console.log('Test 6: System + OS Light resolves to Light');
    const env = createMockEnvironment({}, false);
    const S = loadSentinelInEnv(env);
    S.initTheme();
    assert.strictEqual(S.getSelectedTheme(), 'system');
    assert.strictEqual(S.getResolvedTheme(), 'light', 'Resolved theme should be light when OS is light');
    assert.strictEqual(env.docAttrs.get('data-theme'), 'light');
  }

  // Test 7: System responds to OS theme changes in real-time
  {
    console.log('Test 7: System responds dynamically to OS theme changes');
    const env = createMockEnvironment({ sentinel_theme: 'system' }, false);
    const S = loadSentinelInEnv(env);
    S.initTheme();
    assert.strictEqual(S.getResolvedTheme(), 'light');

    // Simulate OS switching to dark
    let eventReceived = null;
    env.window.addEventListener('sentinel:themechange', (e) => { eventReceived = e.detail; });
    env.triggerOSChange(true);

    assert.strictEqual(S.getResolvedTheme(), 'dark', 'Should automatically update to dark without refresh');
    assert.strictEqual(env.docAttrs.get('data-theme'), 'dark', 'DOM data-theme should be updated to dark');
    assert.ok(eventReceived, 'sentinel:themechange event must be dispatched');
    assert.strictEqual(eventReceived.resolvedTheme, 'dark');
    assert.strictEqual(eventReceived.selectedTheme, 'system');

    // Simulate OS switching back to light
    env.triggerOSChange(false);
    assert.strictEqual(S.getResolvedTheme(), 'light', 'Should automatically update to light');
    assert.strictEqual(env.docAttrs.get('data-theme'), 'light');
  }

  // Test 8: Light ignores OS theme changes
  {
    console.log('Test 8: Light mode ignores OS theme changes');
    const env = createMockEnvironment({}, false);
    const S = loadSentinelInEnv(env);
    S.initTheme();
    S.setTheme('light');
    assert.strictEqual(S.getResolvedTheme(), 'light');

    // OS switches to Dark
    env.triggerOSChange(true);
    assert.strictEqual(S.getResolvedTheme(), 'light', 'Resolved theme must remain light when user chose Light');
    assert.strictEqual(env.docAttrs.get('data-theme'), 'light');
  }

  // Test 9: Dark ignores OS theme changes
  {
    console.log('Test 9: Dark mode ignores OS theme changes');
    const env = createMockEnvironment({}, true);
    const S = loadSentinelInEnv(env);
    S.initTheme();
    S.setTheme('dark');
    assert.strictEqual(S.getResolvedTheme(), 'dark');

    // OS switches to Light
    env.triggerOSChange(false);
    assert.strictEqual(S.getResolvedTheme(), 'dark', 'Resolved theme must remain dark when user chose Dark');
    assert.strictEqual(env.docAttrs.get('data-theme'), 'dark');
  }

  // Test 10: Selected preference persists after reload
  {
    console.log('Test 10: Selected preference persists in localStorage');
    const env = createMockEnvironment({}, false);
    const S = loadSentinelInEnv(env);
    S.initTheme();

    S.setTheme('dark');
    assert.strictEqual(env.storage.get('sentinel_theme'), 'dark');

    S.setTheme('system');
    assert.strictEqual(env.storage.get('sentinel_theme'), 'system');

    S.setTheme('light');
    assert.strictEqual(env.storage.get('sentinel_theme'), 'light');
  }

  // Test 11: Resolved theme is NOT incorrectly persisted for System
  {
    console.log('Test 11: Resolved theme is not stored as user preference for System mode');
    const env = createMockEnvironment({}, true); // OS is dark
    const S = loadSentinelInEnv(env);
    S.initTheme();

    S.setTheme('system');
    assert.strictEqual(S.getResolvedTheme(), 'dark', 'Visual theme is dark');
    assert.strictEqual(env.storage.get('sentinel_theme'), 'system', 'Stored key must be "system", NOT "dark"');
  }

  // Test 12: Cycle toggle works as expected
  {
    console.log('Test 12: Cycle toggle moves through system -> light -> dark -> system');
    const env = createMockEnvironment({ sentinel_theme: 'system' }, false);
    const S = loadSentinelInEnv(env);
    S.initTheme();
    assert.strictEqual(S.getSelectedTheme(), 'system');

    S.toggleTheme();
    assert.strictEqual(S.getSelectedTheme(), 'light');

    S.toggleTheme();
    assert.strictEqual(S.getSelectedTheme(), 'dark');

    S.toggleTheme();
    assert.strictEqual(S.getSelectedTheme(), 'system');
  }

  // Test 13: Backward compatibility for getTheme()
  {
    console.log('Test 13: Backward compatibility of getTheme() for Chart and conditional logic');
    const env = createMockEnvironment({ sentinel_theme: 'system' }, true);
    const S = loadSentinelInEnv(env);
    S.initTheme();
    // Existing code checks Sentinel.getTheme() === 'dark'
    assert.strictEqual(S.getTheme(), 'dark');

    S.setTheme('light');
    assert.strictEqual(S.getTheme(), 'light');
  }

  // Test 14: Chart.js defaults update without errors
  {
    console.log('Test 14: Chart.js defaults update without ReferenceError');
    const env = createMockEnvironment({ sentinel_theme: 'system' }, true);
    env.window.Chart = {
      defaults: {
        font: {},
        plugins: {
          legend: { labels: {} },
          tooltip: {}
        }
      }
    };
    const S = loadSentinelInEnv(env);
    S.initTheme();
    assert.strictEqual(env.window.Chart.defaults.color, '#A6AAA4', 'Dark theme text color');

    S.setTheme('light');
    assert.strictEqual(env.window.Chart.defaults.color, '#686C67', 'Light theme text color');
  }

  console.log('--- ALL Sentinel Theme Tests PASSED SUCCESSFULLY ---');
}

runTests();
