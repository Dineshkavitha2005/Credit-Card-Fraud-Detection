/**
 * Sentinel Landing Page — Dynamic Scrolling Animations & Interactions Engine
 * Provides:
 * 1. Top Reading/Scroll Progress Bar (#scroll-progress-bar)
 * 2. Floating Navbar Scroll Morphing (.omrix-navbar.scrolled)
 * 3. Dynamic Section ScrollSpy (.omrix-nav-item.active)
 * 4. Interactive Back-to-Top Floating Button with Circular SVG Progress Ring
 * 5. Hardware-Accelerated Scroll Reveal System with Stagger Waves (IntersectionObserver)
 * 6. Background Ambient Glow Aura Scroll Parallax
 * 7. Interactive Number Telemetry Shimmer & Counters on Viewport Entry
 * 8. Smooth Anchor Navigation with Proper Offsets
 * 9. Accessibility & Graceful Degradation (prefers-reduced-motion)
 */

(function () {
  'use strict';

  // Check user preference for reduced motion
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // =========================================================================
  // 1. Top Scroll Progress Bar & Back-to-Top Progress Ring
  // =========================================================================
  function initScrollProgress() {
    const progressBar = document.getElementById('scroll-progress-bar');
    const backToTopBtn = document.getElementById('back-to-top');
    const backToTopRing = document.getElementById('back-to-top-ring');
    const circumference = 2 * Math.PI * 20; // r = 20 => ~125.66

    if (backToTopRing) {
      backToTopRing.style.strokeDasharray = `${circumference} ${circumference}`;
      backToTopRing.style.strokeDashoffset = `${circumference}`;
    }

    let ticking = false;

    function onScroll() {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
          const docHeight = document.documentElement.scrollHeight - window.innerHeight;
          const scrollPercent = docHeight > 0 ? Math.min(100, Math.max(0, (scrollTop / docHeight) * 100)) : 0;

          // Update Top Progress Bar
          if (progressBar) {
            progressBar.style.width = `${scrollPercent}%`;
          }

          // Update Back to Top Button Visibility & Circular Ring
          if (backToTopBtn) {
            if (scrollTop > 350) {
              backToTopBtn.classList.add('visible');
            } else {
              backToTopBtn.classList.remove('visible');
            }

            if (backToTopRing) {
              const offset = circumference - (scrollPercent / 100) * circumference;
              backToTopRing.style.strokeDashoffset = `${offset}`;
            }
          }

          ticking = false;
        });
        ticking = true;
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    if (backToTopBtn) {
      backToTopBtn.addEventListener('click', () => {
        window.scrollTo({
          top: 0,
          behavior: prefersReducedMotion ? 'auto' : 'smooth'
        });
      });
    }
  }

  // =========================================================================
  // 2. Floating Navbar Scroll Morphing
  // =========================================================================
  function initNavbarScroll() {
    const navbar = document.getElementById('main-header') || document.querySelector('.omrix-navbar');
    if (!navbar) return;

    let ticking = false;

    function updateNav() {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      if (scrollTop > 24) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
      ticking = false;
    }

    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(updateNav);
        ticking = true;
      }
    }, { passive: true });

    updateNav();
  }

  // =========================================================================
  // 3. ScrollSpy Navigation (Active Nav Item on Scroll)
  // =========================================================================
  function initScrollSpy() {
    const navLinks = document.querySelectorAll('.omrix-nav-item');
    if (!navLinks.length) return;

    const sectionIds = ['hero', 'how-it-works', 'features', 'testimonials', 'pricing', 'faq', 'resources'];
    const sections = sectionIds
      .map(id => document.getElementById(id))
      .filter(el => el !== null);

    if (!sections.length) return;

    let ticking = false;

    function highlightNav() {
      const scrollPos = (window.pageYOffset || document.documentElement.scrollTop) + 160;

      let currentSectionId = '';
      for (let i = 0; i < sections.length; i++) {
        const section = sections[i];
        const top = section.offsetTop;
        const height = section.offsetHeight;
        if (scrollPos >= top && scrollPos < top + height) {
          currentSectionId = section.id;
          break;
        }
      }

      if (!currentSectionId && sections.length > 0 && scrollPos < sections[0].offsetTop) {
        currentSectionId = sections[0].id;
      }

      navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === `#${currentSectionId}`) {
          link.classList.add('active');
        } else {
          link.classList.remove('active');
        }
      });

      ticking = false;
    }

    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(highlightNav);
        ticking = true;
      }
    }, { passive: true });

    highlightNav();
  }

  // =========================================================================
  // 4. Background Ambient Glow Aura Scroll Parallax
  // =========================================================================
  function initAuraParallax() {
    if (prefersReducedMotion) return;
    const aura = document.querySelector('.aura-glow-center');
    if (!aura) return;

    let ticking = false;

    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const scrollY = window.pageYOffset || document.documentElement.scrollTop;
          aura.style.transform = `translate3d(0, ${scrollY * 0.12}px, 0)`;
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  // =========================================================================
  // 5. Scroll Reveal System using IntersectionObserver
  // =========================================================================
  function initScrollReveal() {
    // Prime scroll animation mode on body
    document.body.classList.add('scroll-animated');

    if (prefersReducedMotion) {
      document.querySelectorAll(
        '.scroll-reveal, .scroll-reveal-scale, .scroll-reveal-left, .scroll-reveal-right, .scroll-reveal-hero-mockup'
      ).forEach(el => {
        el.classList.add('is-revealed');
      });
      return;
    }

    // Auto-detect and register sections if explicit classes aren't yet added
    // Section headers & eyebrow labels
    document.querySelectorAll('.section-header, .section-eyebrow, .marquee-title, .hero-pill-badge, .hero-title, .hero-subtext, .hero-cta-group, .hero-guarantees-row').forEach(el => {
      if (!el.classList.contains('scroll-reveal')) {
        el.classList.add('scroll-reveal');
      }
    });

    // Step cards stagger
    document.querySelectorAll('.step-card').forEach((card, index) => {
      if (!card.classList.contains('scroll-reveal')) {
        card.classList.add('scroll-reveal');
        card.classList.add(`delay-${Math.min(index + 1, 6)}`);
      }
    });

    // Bento cards stagger
    document.querySelectorAll('.bento-card').forEach((card, index) => {
      if (!card.classList.contains('scroll-reveal') && !card.classList.contains('scroll-reveal-scale')) {
        if (card.classList.contains('span-2') && index === 0) {
          card.classList.add('scroll-reveal-scale');
        } else {
          card.classList.add('scroll-reveal');
          card.classList.add(`delay-${Math.min(index + 1, 6)}`);
        }
      }
    });

    // Testimonials spotlight & cards
    const quote = document.querySelector('.featured-quote-card');
    if (quote && !quote.classList.contains('scroll-reveal-scale')) {
      quote.classList.add('scroll-reveal-scale');
    }
    document.querySelectorAll('.testimonial-item-card').forEach((card, index) => {
      if (!card.classList.contains('scroll-reveal')) {
        card.classList.add('scroll-reveal');
        card.classList.add(`delay-${Math.min(index + 1, 6)}`);
      }
    });

    // Pricing toggle & cards
    const pricingToggle = document.querySelector('.pricing-toggle-wrap');
    if (pricingToggle && !pricingToggle.classList.contains('scroll-reveal')) {
      pricingToggle.classList.add('scroll-reveal');
    }
    document.querySelectorAll('.pricing-card').forEach((card, index) => {
      if (!card.classList.contains('scroll-reveal')) {
        card.classList.add('scroll-reveal');
        card.classList.add(`delay-${Math.min(index + 1, 6)}`);
      }
    });

    // FAQ Accordion items
    const faqCol = document.querySelector('.faq-left-col');
    if (faqCol && !faqCol.classList.contains('scroll-reveal-left')) {
      faqCol.classList.add('scroll-reveal-left');
    }
    document.querySelectorAll('.accordion-item').forEach((item, index) => {
      if (!item.classList.contains('scroll-reveal')) {
        item.classList.add('scroll-reveal');
        item.classList.add(`delay-${Math.min(index + 1, 6)}`);
      }
    });

    // Resource cards
    document.querySelectorAll('.resource-card').forEach((card, index) => {
      if (!card.classList.contains('scroll-reveal')) {
        card.classList.add('scroll-reveal');
        card.classList.add(`delay-${Math.min(index + 1, 6)}`);
      }
    });

    // CTA Banner Card
    const ctaCard = document.querySelector('.cta-banner-card');
    if (ctaCard && !ctaCard.classList.contains('scroll-reveal-scale')) {
      ctaCard.classList.add('scroll-reveal-scale');
    }

    // Hero Mockup Cockpit
    const heroMockup = document.querySelector('.hero-mockup-wrapper');
    if (heroMockup && !heroMockup.classList.contains('scroll-reveal-hero-mockup')) {
      heroMockup.classList.add('scroll-reveal-hero-mockup');
    }

    // Intersection Observer for all reveal elements
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        }
      });
    }, {
      root: null,
      threshold: 0.08,
      rootMargin: '0px 0px -40px 0px'
    });

    const revealElements = document.querySelectorAll(
      '.scroll-reveal, .scroll-reveal-scale, .scroll-reveal-left, .scroll-reveal-right, .scroll-reveal-hero-mockup'
    );
    revealElements.forEach(el => revealObserver.observe(el));
  }

  // =========================================================================
  // 6. Telemetry & Metric Pulse Shimmer on Viewport Entry
  // =========================================================================
  function initTelemetryEffects() {
    const telemRow = document.querySelector('.cockpit-telemetry-row');
    if (!telemRow) return;

    const telemObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.querySelectorAll('.telem-value').forEach((val, idx) => {
            val.classList.add('pulse-glow');
            setTimeout(() => val.classList.remove('pulse-glow'), 1200 + idx * 200);
          });
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2 });

    telemObserver.observe(telemRow);
  }

  // =========================================================================
  // Initialize on DOM Ready
  // =========================================================================
  function init() {
    initScrollProgress();
    initNavbarScroll();
    initScrollSpy();
    initAuraParallax();
    initScrollReveal();
    initTelemetryEffects();
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
