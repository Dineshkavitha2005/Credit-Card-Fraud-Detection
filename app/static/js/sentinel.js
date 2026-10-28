/**
 * Sentinel - Global Frontend Controller & Utilities
 * Provides theme management (Light/Dark), drawer management, toast notifications,
 * keyboard shortcuts, Lucide icon hydration, network state monitoring, and Chart.js theme defaults.
 */

window.Sentinel = (function() {
  'use strict';

  // Theme state: selected preference ('system' | 'light' | 'dark') and resolved visual theme ('light' | 'dark')
  let selectedTheme = 'system';
  let resolvedTheme = 'light';
  let osMediaQuery = null;
  let osListenerAttached = false;

  function getSystemPreference() {
    if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }

  function resolveTheme(pref) {
    if (pref === 'system') {
      return getSystemPreference();
    }
    return pref === 'dark' ? 'dark' : 'light';
  }

  function handleOSThemeChange(e) {
    // CRITICAL: Only apply if selected theme is 'system'
    if (selectedTheme === 'system') {
      const newResolved = e.matches ? 'dark' : 'light';
      applyTheme(newResolved, 'system', false);
    }
  }

  function setupOSListener() {
    if (osListenerAttached || typeof window === 'undefined' || !window.matchMedia) return;
    try {
      osMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      if (osMediaQuery.addEventListener) {
        osMediaQuery.addEventListener('change', handleOSThemeChange);
      } else if (osMediaQuery.addListener) {
        osMediaQuery.addListener(handleOSThemeChange);
      }
      osListenerAttached = true;
    } catch (err) {
      console.warn('Sentinel: Failed to attach OS theme listener', err);
    }
  }

  // Initialize theme from storage or default to system
  function initTheme() {
    const savedTheme = typeof localStorage !== 'undefined' ? localStorage.getItem('sentinel_theme') : null;
    if (savedTheme === 'light' || savedTheme === 'dark' || savedTheme === 'system') {
      selectedTheme = savedTheme;
    } else {
      selectedTheme = 'system';
    }

    resolvedTheme = resolveTheme(selectedTheme);
    applyTheme(resolvedTheme, selectedTheme, false);
    setupOSListener();
  }

  function applyTheme(resolved, selected, persist = false) {
    resolvedTheme = resolved;
    if (selected) {
      selectedTheme = selected;
    }

    if (persist && typeof localStorage !== 'undefined') {
      // PERSIST ONLY USER SELECTION, NEVER RESOLVED THEME FOR SYSTEM
      localStorage.setItem('sentinel_theme', selectedTheme);
    }

    if (typeof document !== 'undefined' && document.documentElement) {
      if (resolvedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
      }
      document.documentElement.setAttribute('data-theme-preference', selectedTheme);
    }

    updateThemeUI();
    updateChartDefaults();

    // Notify any listening components/charts
    if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
      try {
        window.dispatchEvent(new CustomEvent('sentinel:themechange', {
          detail: {
            selectedTheme: selectedTheme,
            resolvedTheme: resolvedTheme
          }
        }));
      } catch (e) {}
    }
  }

  function setTheme(theme) {
    if (theme !== 'system' && theme !== 'light' && theme !== 'dark') {
      theme = 'system';
    }
    selectedTheme = theme;
    const resolved = resolveTheme(selectedTheme);
    applyTheme(resolved, selectedTheme, true);

    const labelMap = {
      system: `System (${resolved === 'dark' ? 'Dark' : 'Light'})`,
      light: 'Light',
      dark: 'Dark'
    };
    showToast(`Switched to ${labelMap[selectedTheme]} theme`, 'info', 2000);
    closeAllThemeMenus();
  }

  function toggleTheme() {
    // Cycle: system -> light -> dark -> system
    const cycle = { system: 'light', light: 'dark', dark: 'system' };
    const next = cycle[selectedTheme] || 'system';
    setTheme(next);
  }

  function getTheme() {
    // Retain backward compatibility: callers checking getTheme() === 'dark' get resolved theme
    return resolvedTheme;
  }

  function getSelectedTheme() {
    return selectedTheme;
  }

  function getResolvedTheme() {
    return resolvedTheme;
  }

  function updateThemeUI() {
    if (typeof document === 'undefined') return;

    // 1. Update all topbar & navbar toggle buttons
    const toggleBtns = document.querySelectorAll('.theme-toggle-btn');
    toggleBtns.forEach(btn => {
      let iconName = 'monitor';
      let titleText = `Appearance: System (${resolvedTheme === 'dark' ? 'Dark' : 'Light'})`;
      if (selectedTheme === 'light') {
        iconName = 'sun';
        titleText = 'Appearance: Light';
      } else if (selectedTheme === 'dark') {
        iconName = 'moon';
        titleText = 'Appearance: Dark';
      }

      btn.setAttribute('title', titleText);
      btn.setAttribute('aria-label', titleText);
      btn.setAttribute('data-selected-theme', selectedTheme);
      btn.setAttribute('data-resolved-theme', resolvedTheme);

      btn.innerHTML = `<i data-lucide="${iconName}" style="width:15px;height:15px;"></i>`;
    });

    // 2. Update all dropdown menu items (in base and public templates)
    const menuItems = document.querySelectorAll('.theme-menu-item');
    menuItems.forEach(item => {
      const choice = item.getAttribute('data-theme-choice');
      const isSelected = choice === selectedTheme;
      item.setAttribute('aria-checked', isSelected ? 'true' : 'false');
      if (isSelected) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
      const checkIcon = item.querySelector('.theme-check-icon');
      if (checkIcon) {
        checkIcon.style.display = isSelected ? 'inline-block' : 'none';
      }
    });

    // 3. Update Settings page segmented control buttons
    const segmentBtns = document.querySelectorAll('.theme-segment-btn');
    segmentBtns.forEach(btn => {
      const choice = btn.getAttribute('data-theme-value');
      const isSelected = choice === selectedTheme;
      btn.setAttribute('aria-checked', isSelected ? 'true' : 'false');
      if (isSelected) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // 4. Update Settings page description texts if present
    const descText = document.getElementById('theme-description-text');
    if (descText) {
      if (selectedTheme === 'system') {
        descText.textContent = 'Automatically follows your device preference.';
      } else if (selectedTheme === 'light') {
        descText.textContent = 'Always use clean, high-contrast light theme.';
      } else if (selectedTheme === 'dark') {
        descText.textContent = 'Always use quiet, dark fintech operations theme.';
      }
    }

    const resolvedInfo = document.getElementById('theme-resolved-info');
    if (resolvedInfo) {
      if (selectedTheme === 'system') {
        resolvedInfo.textContent = `Currently resolved to ${resolvedTheme === 'dark' ? 'Dark' : 'Light'} mode based on your device.`;
      } else {
        resolvedInfo.textContent = `Fixed to ${selectedTheme === 'dark' ? 'Dark' : 'Light'} mode (device preference ignored).`;
      }
    }

    initIcons();
  }

  function toggleThemeMenu(e) {
    if (e) {
      if (typeof e.stopPropagation === 'function') e.stopPropagation();
      if (typeof e.preventDefault === 'function') e.preventDefault();
    }
    const currentBtn = e && e.currentTarget ? e.currentTarget : document.getElementById('theme-toggle-btn');
    const container = currentBtn ? currentBtn.closest('.theme-selector-wrapper') : null;
    const menu = container ? container.querySelector('.theme-dropdown-menu') : document.getElementById('theme-dropdown');
    if (!menu) return;

    const isVisible = menu.style.display === 'block';
    closeAllThemeMenus();
    if (!isVisible) {
      menu.style.display = 'block';
      if (currentBtn) currentBtn.setAttribute('aria-expanded', 'true');
    }
  }

  function closeAllThemeMenus() {
    if (typeof document === 'undefined') return;
    const menus = document.querySelectorAll('.theme-dropdown-menu');
    menus.forEach(m => { m.style.display = 'none'; });
    const btns = document.querySelectorAll('.theme-toggle-btn');
    btns.forEach(b => { b.setAttribute('aria-expanded', 'false'); });
  }

  // Configure Chart.js Defaults based on theme
  function updateChartDefaults() {
    if (typeof window === 'undefined' || !window.Chart) return;
    const C = window.Chart;

    const isDark = resolvedTheme === 'dark';
    const textColor = isDark ? '#A6AAA4' : '#686C67';
    const gridColor = isDark ? '#242723' : '#ECEEEA';
    const tooltipBg = isDark ? '#222522' : '#181A18';
    const tooltipBorder = isDark ? '#2D302C' : '#262925';

    if (!C.defaults) return;
    if (!C.defaults.font) C.defaults.font = {};
    if (!C.defaults.plugins) C.defaults.plugins = {};
    if (!C.defaults.plugins.legend) C.defaults.plugins.legend = {};
    if (!C.defaults.plugins.legend.labels) C.defaults.plugins.legend.labels = {};
    if (!C.defaults.plugins.tooltip) C.defaults.plugins.tooltip = {};

    C.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    C.defaults.font.size = 12;
    C.defaults.color = textColor;
    C.defaults.plugins.legend.labels.usePointStyle = true;
    C.defaults.plugins.legend.labels.boxWidth = 8;
    C.defaults.plugins.legend.labels.boxHeight = 8;
    C.defaults.plugins.legend.labels.color = textColor;
    C.defaults.plugins.tooltip.backgroundColor = tooltipBg;
    C.defaults.plugins.tooltip.titleColor = '#FFFFFF';
    C.defaults.plugins.tooltip.bodyColor = isDark ? '#F0F2EE' : '#F1F2EF';
    C.defaults.plugins.tooltip.borderColor = tooltipBorder;
    C.defaults.plugins.tooltip.borderWidth = 1;
    C.defaults.plugins.tooltip.cornerRadius = 6;
    C.defaults.plugins.tooltip.padding = 10;
    C.defaults.plugins.tooltip.boxPadding = 4;
  }

  // Hydrate Lucide Icons
  function initIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  // Toast Notification System
  function showToast(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let iconName = 'info';
    if (type === 'success') iconName = 'check-circle';
    else if (type === 'error') iconName = 'alert-circle';
    else if (type === 'warning') iconName = 'alert-triangle';

    toast.innerHTML = `
      <i data-lucide="${iconName}" style="width:16px;height:16px;flex-shrink:0;"></i>
      <span style="flex:1;">${message}</span>
    `;

    container.appendChild(toast);
    initIcons();

    setTimeout(() => {
      toast.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(8px)';
      setTimeout(() => toast.remove(), 250);
    }, duration);
  }

  // Slide-Over Detail Drawer System
  function openDrawer(title, bodyHtml, footerHtml = '') {
    let backdrop = document.getElementById('sentinel-drawer-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'sentinel-drawer-backdrop';
      backdrop.className = 'drawer-backdrop';
      backdrop.innerHTML = `
        <div class="sentinel-drawer" id="sentinel-drawer-panel">
          <div class="drawer-header">
            <div class="drawer-title" id="sentinel-drawer-title">Details</div>
            <button class="drawer-close" onclick="Sentinel.closeDrawer()" aria-label="Close Drawer">
              <i data-lucide="x" style="width:16px;height:16px;"></i>
            </button>
          </div>
          <div class="drawer-body" id="sentinel-drawer-body"></div>
          <div class="drawer-footer" id="sentinel-drawer-footer"></div>
        </div>
      `;
      document.body.appendChild(backdrop);

      backdrop.addEventListener('click', function(e) {
        if (e.target === this) {
          closeDrawer();
        }
      });
    }

    document.getElementById('sentinel-drawer-title').innerHTML = title;
    document.getElementById('sentinel-drawer-body').innerHTML = bodyHtml;
    
    const footerEl = document.getElementById('sentinel-drawer-footer');
    if (footerHtml) {
      footerEl.innerHTML = footerHtml;
      footerEl.style.display = 'flex';
    } else {
      footerEl.innerHTML = '';
      footerEl.style.display = 'none';
    }

    backdrop.classList.add('active');
    document.body.style.overflow = 'hidden';
    initIcons();
  }

  // Active request controllers and sequence tracking
  const activeControllers = new Map();
  const activeSequences = new Map();

  /**
   * Determine if an error represents an expected cancellation.
   * Handles standard DOMException 'AbortError', WebKit/Safari TypeError: "Load failed"
   * when aborted, and DOMException code 20 (ABORT_ERR).
   * Preserves genuine network/offline failures when signal was not aborted.
   */
  function isAbortError(err, signal) {
    if (!err) return false;
    if (err.name === 'AbortError') return true;
    if (err.code === 20) return true;
    if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') return true;

    if (signal && signal.aborted) {
      if (err.name === 'TypeError') {
        const msg = String(err.message || '').toLowerCase();
        if (msg.includes('load failed') || msg.includes('abort') || msg.includes('cancel')) {
          return true;
        }
      }
      return true;
    }

    if (err.name === 'TypeError') {
      const msg = String(err.message || '').toLowerCase();
      if (msg.includes('user aborted') || msg.includes('fetch is aborted')) {
        return true;
      }
    }

    return false;
  }

  /**
   * Abort in-flight requests for a given key.
   */
  function abortRequests(key) {
    if (!key) return;
    if (activeControllers.has(key)) {
      try {
        const controller = activeControllers.get(key);
        controller.abort('Operation cancelled by Sentinel');
      } catch (e) {}
      activeControllers.delete(key);
    }
  }

  /**
   * Abort all active requests (e.g. on navigation / page teardown).
   */
  function abortAllRequests() {
    activeControllers.forEach((controller) => {
      try {
        controller.abort('Navigation in progress');
      } catch (e) {}
    });
    activeControllers.clear();
  }

  /**
   * Check if a response or sequence token is still the latest for its key.
   */
  function isLatest(key, target) {
    if (!key) return true;
    const currentSeq = activeSequences.get(key);
    if (currentSeq === undefined) return true;
    if (target === undefined || target === null) {
      return true;
    }
    if (typeof target === 'number') {
      return target === currentSeq;
    }
    if (typeof target === 'object') {
      if (typeof target._sentinelSeq === 'number') {
        return target._sentinelSeq === currentSeq;
      }
      return false;
    }
    return false;
  }

  /**
   * Execute a cancellable fetch request. If a prior request with the same key
   * is in flight, it is immediately aborted before the new one commences.
   * Prevents stale responses from overwriting newer state via sequence checking.
   */
  async function cancellableFetch(key, url, options = {}) {
    const requestKey = key || 'sentinel-global-request';

    // Abort previous in-flight request for this key
    abortRequests(requestKey);

    const controller = new AbortController();
    activeControllers.set(requestKey, controller);

    const seq = (activeSequences.get(requestKey) || 0) + 1;
    activeSequences.set(requestKey, seq);

    // Chaining consumer signal if provided
    if (options.signal) {
      if (options.signal.aborted) {
        controller.abort(options.signal.reason);
      } else {
        options.signal.addEventListener('abort', () => {
          controller.abort(options.signal.reason);
        }, { once: true });
      }
    }

    const fetchOptions = {
      ...options,
      signal: controller.signal
    };

    try {
      const res = await fetch(url, fetchOptions);

      // Verify sequence to prevent microtask race conditions
      if (activeSequences.get(requestKey) !== seq) {
        const staleErr = new Error('Stale response discarded');
        staleErr.name = 'AbortError';
        staleErr._sentinelKey = requestKey;
        staleErr._sentinelSeq = seq;
        throw staleErr;
      }

      res._sentinelKey = requestKey;
      res._sentinelSeq = seq;
      return res;
    } catch (err) {
      if (isAbortError(err, controller.signal)) {
        const abortErr = new Error('Request cancelled');
        abortErr.name = 'AbortError';
        abortErr.originalError = err;
        abortErr._sentinelKey = requestKey;
        abortErr._sentinelSeq = seq;
        throw abortErr;
      }
      throw err;
    } finally {
      if (activeControllers.get(requestKey) === controller) {
        activeControllers.delete(requestKey);
      }
    }
  }

  function closeDrawer() {
    const backdrop = document.getElementById('sentinel-drawer-backdrop');
    if (backdrop) {
      backdrop.classList.remove('active');
      document.body.style.overflow = '';
    }
    abortRequests('drawer-detail');
  }

  // Copy to Clipboard with Feedback
  async function copyToClipboard(text, successMsg = 'Copied to clipboard') {
    try {
      await navigator.clipboard.writeText(text);
      showToast(successMsg, 'success');
    } catch (e) {
      showToast('Failed to copy', 'error');
    }
  }

  // Formatting Helpers
  function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount || 0);
  }

  function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num || 0);
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? dateStr : d.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  // Mobile Sidebar Toggle
  function toggleSidebar() {
    const sidebar = document.getElementById('sentinel-sidebar');
    if (sidebar) {
      sidebar.classList.toggle('open');
    }
  }

  // Network State Listener
  function initNetworkMonitor() {
    function updateStatus() {
      const banner = document.getElementById('sentinel-offline-banner');
      if (banner) {
        if (!navigator.onLine) {
          banner.classList.add('active');
        } else {
          banner.classList.remove('active');
        }
      }
    }

    window.addEventListener('online', () => {
      updateStatus();
      showToast('Network connection restored', 'success');
    });

    window.addEventListener('offline', () => {
      updateStatus();
      showToast('You are currently offline', 'warning');
    });

    updateStatus();
  }

  // Global Keyboard Shortcuts
  function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Escape key closes open drawers or modals
      if (e.key === 'Escape') {
        closeDrawer();
        const activeModal = document.querySelector('.modal-overlay.active');
        if (activeModal) {
          activeModal.classList.remove('active');
        }
        const notifDropdown = document.getElementById('notif-dropdown');
        if (notifDropdown) notifDropdown.style.display = 'none';
        const userDropdown = document.getElementById('user-dropdown');
        if (userDropdown) userDropdown.style.display = 'none';
      }

      // Quick Search shortcut '/' (unless inside input/textarea)
      if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
        e.preventDefault();
        focusSearchInput();
      }
    });
  }

  // Global Quick Search trigger helper
  window.focusSearchInput = function() {
    const searchInputs = [
      document.getElementById('filter-search'),
      document.getElementById('search-input'),
      document.getElementById('searchInput'),
      document.getElementById('audit-search')
    ];
    for (const input of searchInputs) {
      if (input) {
        input.focus();
        input.select();
        return;
      }
    }
    window.location.href = '/transactions';
  };

  // Topbar dropdown toggles
  window.toggleNotifDropdown = function() {
    const dd = document.getElementById('notif-dropdown');
    const userDd = document.getElementById('user-dropdown');
    if (userDd) userDd.style.display = 'none';
    if (dd) {
      dd.style.display = dd.style.display === 'none' || !dd.style.display ? 'block' : 'none';
    }
  };

  window.toggleUserDropdown = function() {
    const dd = document.getElementById('user-dropdown');
    const notifDd = document.getElementById('notif-dropdown');
    if (notifDd) notifDd.style.display = 'none';
    if (dd) {
      dd.style.display = dd.style.display === 'none' || !dd.style.display ? 'block' : 'none';
    }
  };

  // Close dropdowns on outside click
  document.addEventListener('click', (e) => {
    const notifBtn = document.getElementById('notif-toggle-btn');
    const notifDd = document.getElementById('notif-dropdown');
    if (notifDd && notifBtn && !notifBtn.contains(e.target) && !notifDd.contains(e.target)) {
      notifDd.style.display = 'none';
    }

    const userBtn = document.getElementById('user-menu-btn');
    const userDd = document.getElementById('user-dropdown');
    if (userDd && userBtn && !userBtn.contains(e.target) && !userDd.contains(e.target)) {
      userDd.style.display = 'none';
    }

    // Close theme dropdown on click outside
    const themeWrappers = document.querySelectorAll('.theme-selector-wrapper');
    let insideTheme = false;
    themeWrappers.forEach(w => {
      if (w.contains(e.target)) insideTheme = true;
    });
    if (!insideTheme) {
      closeAllThemeMenus();
    }
  });

  // Close dropdowns on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeAllThemeMenus();
      const notifDd = document.getElementById('notif-dropdown');
      if (notifDd) notifDd.style.display = 'none';
      const userDd = document.getElementById('user-dropdown');
      if (userDd) userDd.style.display = 'none';
    }
  });

  // Auto-run core initialization on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initIcons();
    initNetworkMonitor();
    initKeyboardShortcuts();
  });

  // Teardown in-flight network requests on page navigation to prevent memory leaks
  window.addEventListener('beforeunload', () => abortAllRequests());
  window.addEventListener('pagehide', () => abortAllRequests());

  return {
    initTheme,
    applyTheme,
    setTheme,
    toggleTheme,
    toggleThemeMenu,
    closeThemeMenu: closeAllThemeMenus,
    getTheme,
    getSelectedTheme,
    getResolvedTheme,
    initIcons,
    showToast,
    openDrawer,
    closeDrawer,
    copyToClipboard,
    formatCurrency,
    formatNumber,
    formatDate,
    toggleSidebar,
    isAbortError,
    abortRequests,
    abortAllRequests,
    cancellableFetch,
    isLatest
  };
})();
