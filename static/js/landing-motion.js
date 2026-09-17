/**
 * Sentinel Landing Page — Motion & Interaction Controller
 * Restrained, production-grade interactions for real-time transaction surveillance.
 * Strict compliance with prefers-reduced-motion.
 */

(function() {
    'use strict';

    // Respect reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 1. Sticky Navigation Scroll State
    function initStickyNav() {
        const header = document.querySelector('.sentinel-nav-header');
        if (!header) return;

        function updateNav() {
            if (window.scrollY > 20) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        }

        window.addEventListener('scroll', updateNav, { passive: true });
        updateNav();
    }

    // 2. Live Transaction Stream Animation
    function initLiveTransactionStream() {
        const streamContainer = document.getElementById('hero-tx-stream');
        if (!streamContainer) return;

        const transactions = [
            { scheme: 'VISA', pan: '•••• 4921', amount: '$842.00', risk: 'LOW RISK', score: '12', status: 'ALLOW', statusClass: 'status-allowed', badgeClass: 'badge-allowed' },
            { scheme: 'MASTERCARD', pan: '•••• 7812', amount: '$124.50', risk: 'LOW RISK', score: '08', status: 'ALLOW', statusClass: 'status-allowed', badgeClass: 'badge-allowed' },
            { scheme: 'AMEX', pan: '•••• 3349', amount: '$4,920.00', risk: 'HIGH RISK', score: '93', status: 'BLOCK', statusClass: 'status-blocked', badgeClass: 'badge-blocked', alert: true },
            { scheme: 'VISA', pan: '•••• 1928', amount: '$310.00', risk: 'LOW RISK', score: '19', status: 'ALLOW', statusClass: 'status-allowed', badgeClass: 'badge-allowed' },
            { scheme: 'MASTERCARD', pan: '•••• 6401', amount: '$1,420.00', risk: 'MED RISK', score: '62', status: 'REVIEW', statusClass: 'status-review', badgeClass: 'badge-review' }
        ];

        let index = 0;
        const triggerCard = document.getElementById('hero-trigger-result');

        function cycleStream() {
            if (prefersReducedMotion) return;

            // Highlight the AMEX high-risk block specifically
            const tx = transactions[index % transactions.length];
            index++;

            if (tx.alert && triggerCard) {
                triggerCard.classList.add('pulse-alert');
                setTimeout(() => triggerCard.classList.remove('pulse-alert'), 1200);
            }
        }

        // Run subtle cycling if user does not have reduced motion active
        if (!prefersReducedMotion) {
            setInterval(cycleStream, 4000);
        }
    }

    // 3. Live Detection Workbench Scenarios
    const SCENARIOS = {
        velocity: {
            merchant: 'Amazon Marketplace',
            amount: '₹48,920.00',
            location: 'Chennai, IN',
            device: 'Unknown (Headless Chrome / Linux)',
            velocity: '7 transactions / 2 min',
            channel: 'Card-Not-Present (eCommerce)',
            signals: {
                velocity: { level: 'HIGH', class: 'signal-high' },
                location: { level: 'MEDIUM', class: 'signal-med' },
                device: { level: 'HIGH', class: 'signal-high' },
                amount: { level: 'HIGH', class: 'signal-high' }
            },
            mlScore: '0.87',
            ruleScore: '0.91',
            finalScore: 93,
            decision: 'BLOCK TRANSACTION',
            decisionClass: 'decision-blocked',
            rationale: 'Velocity surge (>5 tx / 2 min) + datacenter proxy IP fingerprint.'
        },
        stuffing: {
            merchant: 'Steam Games Digital',
            amount: '₹99.00',
            location: 'Bucharest, RO',
            device: 'Emulated Mobile (Android 10)',
            velocity: '24 transactions / 3 min',
            channel: 'Card-Not-Present (API Ingress)',
            signals: {
                velocity: { level: 'CRITICAL', class: 'signal-high' },
                location: { level: 'HIGH', class: 'signal-high' },
                device: { level: 'HIGH', class: 'signal-high' },
                amount: { level: 'LOW', class: 'signal-low' }
            },
            mlScore: '0.94',
            ruleScore: '0.96',
            finalScore: 97,
            decision: 'BLOCK TRANSACTION',
            decisionClass: 'decision-blocked',
            rationale: 'Distributed card testing bot pattern detected across multiple PAN fragments.'
        },
        legitimate: {
            merchant: 'Starbucks Coffee',
            amount: '₹420.00',
            location: 'Mumbai, IN',
            device: 'Apple iPhone 15 Pro (Safari)',
            velocity: '1 transaction / 24 hr',
            channel: 'EMV Contactless Token',
            signals: {
                velocity: { level: 'LOW', class: 'signal-low' },
                location: { level: 'LOW', class: 'signal-low' },
                device: { level: 'VERIFIED', class: 'signal-low' },
                amount: { level: 'NORMAL', class: 'signal-low' }
            },
            mlScore: '0.04',
            ruleScore: '0.08',
            finalScore: 6,
            decision: 'ALLOW TRANSACTION',
            decisionClass: 'decision-allowed',
            rationale: 'All features conform to cardholder historical spending profile and trusted device hash.'
        }
    };

    function initDetectionWorkbench() {
        const buttons = document.querySelectorAll('.scenario-btn');
        if (!buttons.length) return;

        buttons.forEach(btn => {
            btn.addEventListener('click', function() {
                buttons.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                const key = this.getAttribute('data-scenario');
                applyScenario(SCENARIOS[key]);
            });
        });
    }

    function applyScenario(data) {
        if (!data) return;

        // Telemetry Left
        const elMerchant = document.getElementById('wb-merchant');
        const elAmount = document.getElementById('wb-amount');
        const elLocation = document.getElementById('wb-location');
        const elDevice = document.getElementById('wb-device');
        const elVelocity = document.getElementById('wb-velocity');

        if (elMerchant) elMerchant.textContent = data.merchant;
        if (elAmount) elAmount.textContent = data.amount;
        if (elLocation) elLocation.textContent = data.location;
        if (elDevice) elDevice.textContent = data.device;
        if (elVelocity) elVelocity.textContent = data.velocity;

        // Signals Right
        updateSignal('wb-sig-velocity', data.signals.velocity);
        updateSignal('wb-sig-location', data.signals.location);
        updateSignal('wb-sig-device', data.signals.device);
        updateSignal('wb-sig-amount', data.signals.amount);

        // Scores
        const elMl = document.getElementById('wb-ml-score');
        const elRule = document.getElementById('wb-rule-score');
        const elFinal = document.getElementById('wb-final-score');
        const elBar = document.getElementById('wb-score-bar');
        const elDecision = document.getElementById('wb-decision');
        const elRationale = document.getElementById('wb-rationale');

        if (elMl) elMl.textContent = data.mlScore;
        if (elRule) elRule.textContent = data.ruleScore;
        if (elFinal) elFinal.textContent = data.finalScore;
        if (elBar) elBar.style.width = data.finalScore + '%';
        
        if (elDecision) {
            elDecision.textContent = data.decision;
            elDecision.className = 'decision-badge ' + data.decisionClass;
        }

        if (elRationale) elRationale.textContent = data.rationale;
    }

    function updateSignal(elementId, signalData) {
        const el = document.getElementById(elementId);
        if (!el || !signalData) return;
        el.textContent = signalData.level;
        el.className = 'signal-pill ' + signalData.class;
    }

    // 4. Product Console Tabs
    function initConsoleTabs() {
        const tabs = document.querySelectorAll('.console-tab');
        const views = document.querySelectorAll('.console-view-panel');
        if (!tabs.length) return;

        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const target = this.getAttribute('data-tab');
                tabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');

                views.forEach(view => {
                    if (view.id === 'view-' + target) {
                        view.classList.add('active');
                    } else {
                        view.classList.remove('active');
                    }
                });
            });
        });
    }

    // 5. Scroll-linked Pipeline Step Observer
    function initPipelineObserver() {
        const steps = document.querySelectorAll('.pipeline-row-item');
        if (!steps.length || prefersReducedMotion) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('in-view');
                }
            });
        }, { threshold: 0.2 });

        steps.forEach(step => observer.observe(step));
    }

    // Initialize all controllers on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initStickyNav();
            initLiveTransactionStream();
            initDetectionWorkbench();
            initConsoleTabs();
            initPipelineObserver();
        });
    } else {
        initStickyNav();
        initLiveTransactionStream();
        initDetectionWorkbench();
        initConsoleTabs();
        initPipelineObserver();
    }
})();
