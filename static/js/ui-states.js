/**
 * FraudShield UI States Engine
 * Reusable, accessible, responsive UI states management utility
 */

(function (window, document) {
    'use strict';

    const UIState = {
        slowNetworkThresholdMs: 2500,
        activeSlowTimers: new Map(),

        /**
         * Initialize Global Event Listeners & Containers
         */
        init() {
            this.setupOfflineHandling();
            this.ensureA11yAnnouncer();
            this.ensureModalContainers();
            this.ensureSlowNetworkBanner();
        },

        /**
         * Announce status updates to screen readers
         */
        announce(message, priority = 'polite') {
            let announcer = document.getElementById('a11y-status-announcer');
            if (!announcer) {
                announcer = document.createElement('div');
                announcer.id = 'a11y-status-announcer';
                announcer.className = 'sr-only';
                announcer.setAttribute('aria-live', priority);
                announcer.setAttribute('aria-atomic', 'true');
                document.body.appendChild(announcer);
            }
            announcer.textContent = '';
            setTimeout(() => {
                announcer.textContent = message;
            }, 50);
        },

        ensureA11yAnnouncer() {
            if (!document.getElementById('a11y-status-announcer')) {
                const el = document.createElement('div');
                el.id = 'a11y-status-announcer';
                el.className = 'sr-only';
                el.setAttribute('aria-live', 'polite');
                el.setAttribute('aria-atomic', 'true');
                document.body.appendChild(el);
            }
        },

        ensureSlowNetworkBanner() {
            if (!document.getElementById('slow-network-banner')) {
                const banner = document.createElement('div');
                banner.id = 'slow-network-banner';
                banner.className = 'slow-network-banner';
                banner.setAttribute('role', 'status');
                banner.innerHTML = `
                    <div class="spinner-small"></div>
                    <span>This is taking longer than expected...</span>
                `;
                document.body.appendChild(banner);
            }
        },

        ensureModalContainers() {
            // Permission Denied (403) Modal
            if (!document.getElementById('ui-modal-forbidden')) {
                const modal = document.createElement('div');
                modal.id = 'ui-modal-forbidden';
                modal.className = 'ui-state-modal-overlay';
                modal.setAttribute('role', 'dialog');
                modal.setAttribute('aria-modal', 'true');
                modal.setAttribute('aria-labelledby', 'ui-modal-forbidden-title');
                modal.innerHTML = `
                    <div class="ui-state-modal-card">
                        <div class="ui-state-modal-icon forbidden">
                            <i class="fas fa-shield-halved"></i>
                        </div>
                        <h3 class="ui-state-modal-title" id="ui-modal-forbidden-title">Access Denied</h3>
                        <p class="ui-state-modal-desc" id="ui-modal-forbidden-desc">You do not have administrative privileges or authorized permission to perform this action.</p>
                        <div style="display:flex;gap:12px;justify-content:center;">
                            <button class="btn btn-primary" onclick="UIState.closeForbiddenModal()">
                                <i class="fas fa-home"></i> Return to Dashboard
                            </button>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);
            }

            // Session Expired (401) Modal
            if (!document.getElementById('ui-modal-expired')) {
                const modal = document.createElement('div');
                modal.id = 'ui-modal-expired';
                modal.className = 'ui-state-modal-overlay';
                modal.setAttribute('role', 'alertdialog');
                modal.setAttribute('aria-modal', 'true');
                modal.setAttribute('aria-labelledby', 'ui-modal-expired-title');
                modal.innerHTML = `
                    <div class="ui-state-modal-card">
                        <div class="ui-state-modal-icon expired">
                            <i class="fas fa-lock"></i>
                        </div>
                        <h3 class="ui-state-modal-title" id="ui-modal-expired-title">Session Expired</h3>
                        <p class="ui-state-modal-desc">Your session has timed out for security reasons. Please sign in again to continue.</p>
                        <div style="display:flex;gap:12px;justify-content:center;">
                            <button class="btn btn-primary" id="ui-modal-expired-btn">
                                <i class="fas fa-sign-in-alt"></i> Sign In Again
                            </button>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);
            }
        },

        /* ----------------------------------------------------------------------
           4. OFFLINE / NO INTERNET HANDLING
           ---------------------------------------------------------------------- */
        setupOfflineHandling() {
            let offlineBanner = document.getElementById('offline-banner');
            if (!offlineBanner) {
                offlineBanner = document.createElement('div');
                offlineBanner.id = 'offline-banner';
                offlineBanner.className = 'offline-banner';
                offlineBanner.setAttribute('role', 'alert');
                offlineBanner.setAttribute('aria-live', 'assertive');
                offlineBanner.innerHTML = `
                    <i class="fas fa-wifi-slash"></i>
                    <span>You're currently offline. Some features and live fraud checks may be unavailable.</span>
                `;
                document.body.prepend(offlineBanner);
            }

            const updateOnlineStatus = () => {
                const isOnline = navigator.onLine;
                const statusDot = document.querySelector('.status-indicator');
                
                if (!isOnline) {
                    offlineBanner.classList.remove('restored');
                    offlineBanner.classList.add('active');
                    offlineBanner.innerHTML = `
                        <i class="fas fa-wifi-slash"></i>
                        <span>You're offline. Some features may be unavailable until connection is restored.</span>
                    `;
                    if (statusDot) {
                        statusDot.innerHTML = '<span class="offline-indicator-dot"></span> System Offline';
                        statusDot.style.color = 'var(--danger, #ef4444)';
                    }
                    this.announce("You are currently offline. Network dependent actions are disabled.", "assertive");
                } else {
                    if (offlineBanner.classList.contains('active')) {
                        offlineBanner.classList.add('restored');
                        offlineBanner.innerHTML = `
                            <i class="fas fa-check-circle"></i>
                            <span>Back online! Connection restored.</span>
                        `;
                        if (statusDot) {
                            statusDot.innerHTML = '<span class="status-dot"></span> System Online';
                            statusDot.style.color = 'var(--success, #10b981)';
                        }
                        this.announce("Back online. Connection restored.", "polite");
                        setTimeout(() => {
                            offlineBanner.classList.remove('active', 'restored');
                        }, 3500);
                    }
                }
            };

            window.addEventListener('offline', updateOnlineStatus);
            window.addEventListener('online', updateOnlineStatus);
            if (!navigator.onLine) {
                updateOnlineStatus();
            }
        },

        /* ----------------------------------------------------------------------
           1. EMPTY STATE RENDERER
           ---------------------------------------------------------------------- */
        renderEmptyState({
            icon = 'fa-folder-open',
            title = 'No Data Available',
            message = 'There is currently no information to display.',
            primaryAction = null,
            secondaryAction = null,
            className = ''
        } = {}) {
            let actionsHtml = '';
            if (primaryAction || secondaryAction) {
                actionsHtml = `<div class="empty-actions">`;
                if (primaryAction) {
                    actionsHtml += `
                        <button class="btn btn-primary ${primaryAction.className || ''}" 
                                onclick="${primaryAction.onClick || ''}" 
                                ${primaryAction.attributes || ''}>
                            ${primaryAction.icon ? `<i class="fas ${primaryAction.icon}"></i>` : ''}
                            ${primaryAction.label}
                        </button>
                    `;
                }
                if (secondaryAction) {
                    actionsHtml += `
                        <button class="btn btn-outline ${secondaryAction.className || ''}" 
                                onclick="${secondaryAction.onClick || ''}" 
                                ${secondaryAction.attributes || ''}>
                            ${secondaryAction.icon ? `<i class="fas ${secondaryAction.icon}"></i>` : ''}
                            ${secondaryAction.label}
                        </button>
                    `;
                }
                actionsHtml += `</div>`;
            }

            return `
                <div class="ui-state-empty ${className}" role="status">
                    <div class="empty-icon-wrap">
                        <i class="fas ${icon}"></i>
                    </div>
                    <h3 class="empty-title">${title}</h3>
                    <p class="empty-desc">${message}</p>
                    ${actionsHtml}
                </div>
            `;
        },

        showEmpty(container, options = {}) {
            const el = typeof container === 'string' ? document.querySelector(container) : container;
            if (el) {
                el.innerHTML = this.renderEmptyState(options);
                this.announce(options.title || 'No data available');
            }
        },

        /* ----------------------------------------------------------------------
           6. NO SEARCH RESULTS STATE RENDERER
           ---------------------------------------------------------------------- */
        renderNoResults({
            query = '',
            filterSummary = '',
            title = 'No Results Found',
            message = null,
            onClear = 'resetFilters()',
            clearLabel = 'Clear Filters'
        } = {}) {
            const defaultMsg = query
                ? `We couldn't find any records matching <span class="no-results-query">"${this.escapeHtml(query)}"</span>.`
                : (filterSummary || 'No records match your active filter criteria.');

            return `
                <div class="ui-state-no-results" role="status">
                    <div class="no-results-icon">
                        <i class="fas fa-search-minus"></i>
                    </div>
                    <h3 class="no-results-title">${title}</h3>
                    <p class="no-results-desc">${message || defaultMsg}</p>
                    <div class="empty-actions">
                        <button class="btn btn-outline btn-sm" onclick="${onClear}">
                            <i class="fas fa-times-circle"></i> ${clearLabel}
                        </button>
                    </div>
                </div>
            `;
        },

        showNoResults(container, options = {}) {
            const el = typeof container === 'string' ? document.querySelector(container) : container;
            if (el) {
                el.innerHTML = this.renderNoResults(options);
                this.announce(`No search results found.`);
            }
        },

        /* ----------------------------------------------------------------------
           3. ERROR STATE RENDERER
           ---------------------------------------------------------------------- */
        renderErrorState({
            title = 'Unable to Load Data',
            message = 'We encountered an error while processing your request. Please try again.',
            onRetry = null,
            icon = 'fa-triangle-exclamation',
            className = ''
        } = {}) {
            const retryHtml = onRetry ? `
                <button class="btn-retry" onclick="${onRetry}">
                    <i class="fas fa-rotate-right"></i> Try Again
                </button>
            ` : '';

            return `
                <div class="ui-state-error ${className}" role="alert">
                    <div class="error-icon-wrap">
                        <i class="fas ${icon}"></i>
                    </div>
                    <h3 class="error-title">${title}</h3>
                    <p class="error-desc">${message}</p>
                    ${retryHtml}
                </div>
            `;
        },

        showError(container, options = {}) {
            const el = typeof container === 'string' ? document.querySelector(container) : container;
            if (el) {
                el.innerHTML = this.renderErrorState(options);
                this.announce(options.title || 'Error occurred', 'assertive');
            }
        },

        /* ----------------------------------------------------------------------
           2. SKELETON LOADERS
           ---------------------------------------------------------------------- */
        renderTableSkeletons(columns = 6, rows = 5) {
            let html = '';
            for (let r = 0; r < rows; r++) {
                html += `<tr class="skeleton-table-row">`;
                for (let c = 0; c < columns; c++) {
                    const width = c === 0 ? '70%' : (c === 1 ? '90%' : '50%');
                    html += `<td><span class="skeleton-box skeleton-text" style="width:${width};"></span></td>`;
                }
                html += `</tr>`;
            }
            return html;
        },

        renderCardSkeletons(count = 4) {
            let html = '';
            for (let i = 0; i < count; i++) {
                html += `
                    <div class="skeleton-card">
                        <div class="skeleton-card-header">
                            <span class="skeleton-box skeleton-circle"></span>
                            <span class="skeleton-box skeleton-text short"></span>
                        </div>
                        <span class="skeleton-box skeleton-text heading"></span>
                        <span class="skeleton-box skeleton-text short"></span>
                    </div>
                `;
            }
            return html;
        },

        showLoading(container, type = 'table', options = {}) {
            const el = typeof container === 'string' ? document.querySelector(container) : container;
            if (!el) return;

            if (type === 'table') {
                el.innerHTML = this.renderTableSkeletons(options.cols || 6, options.rows || 5);
            } else if (type === 'cards') {
                el.innerHTML = this.renderCardSkeletons(options.count || 4);
            } else {
                el.innerHTML = `<div class="spinner" role="status" aria-label="Loading content"></div>`;
            }
            this.announce("Loading content...", "polite");
        },

        /* ----------------------------------------------------------------------
           BUTTON LOADING & DOUBLE SUBMISSION PREVENTION
           ---------------------------------------------------------------------- */
        setButtonLoading(button, isLoading = true, loadingText = 'Processing...') {
            const btn = typeof button === 'string' ? document.querySelector(button) : button;
            if (!btn) return;

            if (isLoading) {
                btn.dataset.originalHtml = btn.innerHTML;
                btn.disabled = true;
                btn.classList.add('is-loading');
                btn.innerHTML = `<span class="btn-spinner" aria-hidden="true"></span>${loadingText}`;
            } else {
                btn.disabled = false;
                btn.classList.remove('is-loading');
                if (btn.dataset.originalHtml) {
                    btn.innerHTML = btn.dataset.originalHtml;
                }
            }
        },

        preventDoubleSubmit(formElement, submitButton, loadingText = 'Submitting...') {
            const form = typeof formElement === 'string' ? document.querySelector(formElement) : formElement;
            const btn = typeof submitButton === 'string' ? document.querySelector(submitButton) : submitButton;
            if (!form) return;

            form.addEventListener('submit', (e) => {
                if (form.dataset.submitting === 'true') {
                    e.preventDefault();
                    return false;
                }
                form.dataset.submitting = 'true';
                if (btn) {
                    this.setButtonLoading(btn, true, loadingText);
                }
            });
        },

        /* ----------------------------------------------------------------------
           7. 403 & 8. 401 MODAL CONTROLS
           ---------------------------------------------------------------------- */
        showForbiddenModal(message = null, redirectUrl = '/dashboard') {
            this.ensureModalContainers();
            const modal = document.getElementById('ui-modal-forbidden');
            if (message) {
                const desc = document.getElementById('ui-modal-forbidden-desc');
                if (desc) desc.textContent = message;
            }
            if (modal) modal.classList.add('active');
            this.announce("Access Denied: You do not have permission to access this resource.", "assertive");
        },

        closeForbiddenModal(redirectUrl = '/dashboard') {
            const modal = document.getElementById('ui-modal-forbidden');
            if (modal) modal.classList.remove('active');
            if (redirectUrl) window.location.href = redirectUrl;
        },

        showSessionExpiredModal(loginUrl = '/login') {
            this.ensureModalContainers();
            const modal = document.getElementById('ui-modal-expired');
            const btn = document.getElementById('ui-modal-expired-btn');
            if (btn) {
                btn.onclick = () => {
                    const currentPath = encodeURIComponent(window.location.pathname + window.location.search);
                    window.location.href = `${loginUrl}?next=${currentPath}`;
                };
            }
            if (modal) modal.classList.add('active');
            this.announce("Your session has expired. Please sign in again.", "assertive");
        },

        /* ----------------------------------------------------------------------
           9. FORM VALIDATION HELPERS
           ---------------------------------------------------------------------- */
        setFieldState(input, isValid, message = '') {
            const el = typeof input === 'string' ? document.querySelector(input) : input;
            if (!el) return;

            const formGroup = el.closest('.form-group') || el.parentElement;
            let feedback = formGroup ? formGroup.querySelector('.field-feedback') : null;

            if (!feedback && formGroup) {
                feedback = document.createElement('div');
                feedback.className = 'field-feedback';
                formGroup.appendChild(feedback);
            }

            if (isValid) {
                el.classList.remove('is-invalid');
                el.classList.add('is-valid');
                if (formGroup) formGroup.classList.remove('has-error');
                if (feedback) {
                    feedback.className = 'field-feedback success';
                    feedback.innerHTML = message ? `<i class="fas fa-check"></i> ${message}` : '';
                }
            } else {
                el.classList.remove('is-valid');
                el.classList.add('is-invalid');
                if (formGroup) formGroup.classList.add('has-error');
                if (feedback) {
                    feedback.className = 'field-feedback error';
                    feedback.innerHTML = `<i class="fas fa-circle-exclamation"></i> ${message}`;
                }
            }
        },

        clearFieldState(input) {
            const el = typeof input === 'string' ? document.querySelector(input) : input;
            if (!el) return;
            el.classList.remove('is-invalid', 'is-valid');
            const formGroup = el.closest('.form-group') || el.parentElement;
            if (formGroup) {
                formGroup.classList.remove('has-error');
                const feedback = formGroup.querySelector('.field-feedback');
                if (feedback) feedback.remove();
            }
        },

        /* ----------------------------------------------------------------------
           10. TOAST NOTIFICATIONS (ENHANCED)
           ---------------------------------------------------------------------- */
        showToast(message, type = 'info', duration = 4000) {
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.className = 'toast-container';
                document.body.appendChild(container);
            }

            const toast = document.createElement('div');
            const icons = {
                success: 'fa-check-circle',
                error: 'fa-exclamation-circle',
                warning: 'fa-triangle-exclamation',
                info: 'fa-circle-info'
            };

            toast.className = `toast ${type}`;
            toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
            toast.innerHTML = `<i class="fas ${icons[type] || 'fa-circle-info'}"></i><span>${this.escapeHtml(message)}</span>`;
            container.appendChild(toast);

            this.announce(`${type}: ${message}`, type === 'error' ? 'assertive' : 'polite');

            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        },

        /* ----------------------------------------------------------------------
           API CALL INTERCEPTOR (HANDLES SLOW NETWORK, 401, 403, 500, OFFLINE)
           ---------------------------------------------------------------------- */
        async apiCall(url, options = {}) {
            // Check offline state before initiating request
            if (!navigator.onLine) {
                const offlineErr = 'You are currently offline. Please check your internet connection.';
                this.showToast(offlineErr, 'error');
                throw new Error(offlineErr);
            }

            const requestId = Symbol('request');
            const slowBanner = document.getElementById('slow-network-banner');

            // Slow network threshold timer (>2.5s)
            const slowTimer = setTimeout(() => {
                if (slowBanner) {
                    slowBanner.classList.add('active');
                }
            }, this.slowNetworkThresholdMs);

            this.activeSlowTimers.set(requestId, slowTimer);

            try {
                const res = await fetch(url, {
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        ...options.headers
                    },
                    ...options
                });

                // Clear slow network timer
                clearTimeout(slowTimer);
                this.activeSlowTimers.delete(requestId);
                if (this.activeSlowTimers.size === 0 && slowBanner) {
                    slowBanner.classList.remove('active');
                }

                // Handle 401 Unauthorized -> Session Expired
                if (res.status === 401) {
                    this.showSessionExpiredModal('/login');
                    throw new Error('Your session has expired. Please sign in again.');
                }

                // Handle 403 Forbidden -> Permission Denied
                if (res.status === 403) {
                    let errData = {};
                    try { errData = await res.clone().json(); } catch (e) {}
                    const msg = errData.error || errData.message || 'Access Forbidden';
                    this.showForbiddenModal(msg);
                    throw new Error(msg);
                }

                const isJson = (res.headers.get('content-type') || '').includes('application/json');
                const data = isJson ? await res.json() : await res.text();

                if (!res.ok) {
                    const errorMsg = (typeof data === 'object' && data.error) 
                        ? data.error 
                        : (typeof data === 'object' && data.message ? data.message : `HTTP ${res.status}: Request failed`);
                    throw new Error(errorMsg);
                }

                return data;
            } catch (err) {
                // Ensure slow timer cleanup
                clearTimeout(slowTimer);
                this.activeSlowTimers.delete(requestId);
                if (this.activeSlowTimers.size === 0 && slowBanner) {
                    slowBanner.classList.remove('active');
                }

                // Don't toast if it was already handled by session expired or 403 modal
                if (!err.message.includes('session has expired') && !err.message.includes('Access Forbidden')) {
                    this.showToast(err.message || 'An unexpected error occurred', 'error');
                }
                throw err;
            }
        },

        escapeHtml(str) {
            if (str == null) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }
    };

    // Auto-init on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => UIState.init());
    } else {
        UIState.init();
    }

    // Expose to window
    window.UIState = UIState;

})(window, document);
