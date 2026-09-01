/**
 * Sentinel - Global Frontend Controller & Utilities
 * Provides theme management (Light/Dark), drawer management, toast notifications,
 * keyboard shortcuts, Lucide icon hydration, network state monitoring, and Chart.js theme defaults.
 */

window.Sentinel = (function() {
  'use strict';

  // Active theme tracking
  let currentTheme = 'light';

  // Initialize theme from storage or OS preference
  function initTheme() {
    const savedTheme = localStorage.getItem('sentinel_theme');
    if (savedTheme) {
      currentTheme = savedTheme;
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      currentTheme = 'dark';
    } else {
      currentTheme = 'light';
    }

    applyTheme(currentTheme);

    // Listen for OS theme changes if not explicitly overridden
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('sentinel_theme')) {
          applyTheme(e.matches ? 'dark' : 'light');
        }
      });
    }
  }

  function applyTheme(theme) {
    currentTheme = theme;
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }

    updateThemeToggleUI();
    updateChartDefaults();
  }

  function toggleTheme() {
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('sentinel_theme', nextTheme);
    applyTheme(nextTheme);
    showToast(`Switched to ${nextTheme === 'dark' ? 'Dark' : 'Light'} theme`, 'info', 2000);
  }

  function getTheme() {
    return currentTheme;
  }

  function updateThemeToggleUI() {
    const toggleBtns = document.querySelectorAll('.theme-toggle-btn');
    toggleBtns.forEach(btn => {
      if (currentTheme === 'dark') {
        btn.innerHTML = `<i data-lucide="sun" style="width:15px;height:15px;"></i>`;
        btn.setAttribute('title', 'Switch to Light Mode');
        btn.setAttribute('aria-label', 'Switch to Light Mode');
      } else {
        btn.innerHTML = `<i data-lucide="moon" style="width:15px;height:15px;"></i>`;
        btn.setAttribute('title', 'Switch to Dark Mode');
        btn.setAttribute('aria-label', 'Switch to Dark Mode');
      }
    });
    initIcons();
  }

  // Configure Chart.js Defaults based on theme
  function updateChartDefaults() {
    if (!window.Chart) return;

    const isDark = currentTheme === 'dark';
    const textColor = isDark ? '#A6AAA4' : '#686C67';
    const gridColor = isDark ? '#242723' : '#ECEEEA';
    const tooltipBg = isDark ? '#222522' : '#181A18';
    const tooltipBorder = isDark ? '#2D302C' : '#262925';

    Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = textColor;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 8;
    Chart.defaults.plugins.legend.labels.boxHeight = 8;
    Chart.defaults.plugins.legend.labels.color = textColor;
    Chart.defaults.plugins.tooltip.backgroundColor = tooltipBg;
    Chart.defaults.plugins.tooltip.titleColor = '#FFFFFF';
    Chart.defaults.plugins.tooltip.bodyColor = isDark ? '#F0F2EE' : '#F1F2EF';
    Chart.defaults.plugins.tooltip.borderColor = tooltipBorder;
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.cornerRadius = 6;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.boxPadding = 4;
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
    toggleTheme,
    getTheme,
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
