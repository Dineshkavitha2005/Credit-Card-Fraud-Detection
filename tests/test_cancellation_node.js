/**
 * Node.js Test Suite for Sentinel AbortController & Request Lifecycle Management
 * Tests rapid filter changes, Safari/WebKit quirks, race condition prevention,
 * memory cleanup, and genuine error preservation.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

// 1. Mock minimal browser environment
global.window = global;
global.document = {
  documentElement: {
    setAttribute: () => {},
    removeAttribute: () => {}
  },
  body: {
    style: {},
    appendChild: () => {}
  },
  getElementById: () => null,
  querySelectorAll: () => [],
  addEventListener: () => {}
};
global.localStorage = {
  getItem: () => null,
  setItem: () => {}
};
global.navigator = {
  onLine: true,
  clipboard: {
    writeText: async () => {}
  }
};
global.location = { href: '' };

const eventListeners = new Map();
global.window.addEventListener = (event, fn) => {
  if (!eventListeners.has(event)) eventListeners.set(event, []);
  eventListeners.get(event).push(fn);
};

// Load sentinel.js code
const sentinelCode = fs.readFileSync(path.join(__dirname, '..', 'static', 'js', 'sentinel.js'), 'utf8');
eval(sentinelCode);

const Sentinel = global.window.Sentinel;
assert(Sentinel, 'Sentinel must be initialized on window');

async function runTests() {
  console.log('--- Running Sentinel Cancellation & Async Fetch Test Suite ---');

  // Test 1: isAbortError detection
  console.log('Test 1: isAbortError cancellation detection');
  
  // Standard DOMException / AbortError
  const stdAbort = new Error('The operation was aborted');
  stdAbort.name = 'AbortError';
  assert.strictEqual(Sentinel.isAbortError(stdAbort), true, 'Standard AbortError should be detected');

  const code20Abort = new Error('Abort error code 20');
  code20Abort.code = 20;
  assert.strictEqual(Sentinel.isAbortError(code20Abort), true, 'DOMException code 20 should be detected');

  // Safari / WebKit TypeError: "Load failed" when aborted
  const abortedSignal = { aborted: true, reason: 'Superseded' };
  const webKitAbort = new TypeError('Load failed');
  assert.strictEqual(Sentinel.isAbortError(webKitAbort, abortedSignal), true, 'Safari TypeError: Load failed with aborted signal must be detected');

  const webKitFetchAborted = new TypeError('Fetch is aborted');
  assert.strictEqual(Sentinel.isAbortError(webKitFetchAborted), true, 'WebKit Fetch is aborted must be detected');

  // Genuine network errors (when signal was NOT aborted)
  const nonAbortedSignal = { aborted: false };
  const genuineOffline = new TypeError('Load failed');
  assert.strictEqual(Sentinel.isAbortError(genuineOffline, nonAbortedSignal), false, 'Genuine network failure Load failed must NOT be treated as abort');

  const genuineFailedToFetch = new TypeError('Failed to fetch');
  assert.strictEqual(Sentinel.isAbortError(genuineFailedToFetch, nonAbortedSignal), false, 'Genuine Failed to fetch must NOT be treated as abort');

  const server500 = new Error('HTTP 500: Internal Server Error');
  assert.strictEqual(Sentinel.isAbortError(server500), false, 'Server 500 error must NOT be treated as abort');

  console.log('✓ Test 1 Passed: Cancellation errors detected; genuine network errors preserved.');

  // Test 2: Rapid Filter Changes / Request Supersession
  console.log('Test 2: Rapid filter changes abort previous in-flight requests');
  
  let fetchCallCount = 0;
  let abortedCalls = 0;

  global.fetch = (url, options) => {
    fetchCallCount++;
    const signal = options && options.signal;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        resolve({
          ok: true,
          status: 200,
          json: async () => ({ result: url })
        });
      }, 50);

      if (signal) {
        signal.addEventListener('abort', () => {
          clearTimeout(timer);
          abortedCalls++;
          const err = new Error('The user aborted a request.');
          err.name = 'AbortError';
          reject(err);
        });
      }
    });
  };

  // Dispatch 3 rapid requests for the same key
  const p1 = Sentinel.cancellableFetch('test-filter', '/api/data?query=a').catch(err => err);
  const p2 = Sentinel.cancellableFetch('test-filter', '/api/data?query=ab').catch(err => err);
  const p3 = Sentinel.cancellableFetch('test-filter', '/api/data?query=abc');

  const [res1, res2, res3] = await Promise.all([p1, p2, p3]);

  assert.strictEqual(Sentinel.isAbortError(res1), true, 'Request 1 must be aborted');
  assert.strictEqual(Sentinel.isAbortError(res2), true, 'Request 2 must be aborted');
  assert.strictEqual(res3.ok, true, 'Request 3 must succeed');
  assert.strictEqual(abortedCalls, 2, 'Two previous requests must have had abort triggered');

  console.log('✓ Test 2 Passed: Previous in-flight requests properly aborted upon rapid filter change.');

  // Test 3: Stale response protection (out-of-order resolution)
  console.log('Test 3: Stale response sequence guard prevents race conditions');
  
  // Simulate slow Request 1 and fast Request 2
  global.fetch = (url, options) => {
    return new Promise((resolve) => {
      const delay = url.includes('slow') ? 80 : 10;
      setTimeout(() => {
        resolve({
          ok: true,
          status: 200,
          json: async () => ({ data: url })
        });
      }, delay);
    });
  };

  const reqSlow = Sentinel.cancellableFetch('test-race', '/api/slow').catch(err => err);
  const reqFast = Sentinel.cancellableFetch('test-race', '/api/fast');

  const [slowRes, fastRes] = await Promise.all([reqSlow, reqFast]);

  assert.strictEqual(Sentinel.isAbortError(slowRes), true, 'Superseded slow response discarded with AbortError');
  assert.strictEqual(fastRes.ok, true, 'Latest response preserved');
  assert.strictEqual(Sentinel.isLatest('test-race', fastRes), true, 'Fast response is marked as latest sequence');
  assert.strictEqual(Sentinel.isLatest('test-race', slowRes), false, 'Slow response is not latest sequence');

  console.log('✓ Test 3 Passed: Out-of-order stale responses discarded by sequence guard.');

  // Test 4: Detail drawer inspect & drawer close abort
  console.log('Test 4: Detail drawer inspection abort on close');
  let drawerAborted = false;
  global.fetch = (url, options) => {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => resolve({ ok: true, json: async () => ({}) }), 100);
      if (options.signal) {
        options.signal.addEventListener('abort', () => {
          clearTimeout(timer);
          drawerAborted = true;
          const err = new Error('Drawer closed');
          err.name = 'AbortError';
          reject(err);
        });
      }
    });
  };

  const drawerPromise = Sentinel.cancellableFetch('drawer-detail', '/api/transactions/TX-999/details').catch(err => err);
  // User closes drawer before fetch completes
  Sentinel.closeDrawer();
  const drawerRes = await drawerPromise;

  assert.strictEqual(drawerAborted, true, 'Drawer close must abort in-flight detail fetch');
  assert.strictEqual(Sentinel.isAbortError(drawerRes), true, 'Drawer detail error must be recognized as AbortError');

  console.log('✓ Test 4 Passed: Drawer close successfully aborts pending detail request.');

  // Test 5: Page unload teardown
  console.log('Test 5: Navigation/unload aborts all active requests');
  let unloadAborted = 0;
  global.fetch = (url, options) => {
    return new Promise((resolve, reject) => {
      if (options.signal) {
        options.signal.addEventListener('abort', () => {
          unloadAborted++;
          const err = new Error('Navigation in progress');
          err.name = 'AbortError';
          reject(err);
        });
      }
    });
  };

  const navReq1 = Sentinel.cancellableFetch('page-req-1', '/api/1').catch(err => err);
  const navReq2 = Sentinel.cancellableFetch('page-req-2', '/api/2').catch(err => err);

  Sentinel.abortAllRequests();
  await Promise.all([navReq1, navReq2]);

  assert.strictEqual(unloadAborted, 2, 'All active requests must be aborted on unload');
  console.log('✓ Test 5 Passed: All active requests aborted on navigation/unload.');

  console.log('\n================ ALL NODE TESTS PASSED ================');
}

runTests().catch(err => {
  console.error('Test Suite Failed:', err);
  process.exit(1);
});
