// =============================================================================
// Professional Resume Builder — Landing Page Interactions
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // --- Navbar scroll effect ---
    const nav = document.getElementById('main-nav');
    const handleScroll = () => {
        if (window.scrollY > 50) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    // --- Mobile nav toggle ---
    const navToggle = document.getElementById('nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (navToggle) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('open');
        });

        // Close on link click
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('open');
            });
        });
    }

    // --- Smooth scroll for anchor links ---
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const target = document.querySelector(anchor.getAttribute('href'));
            if (target) {
                const offset = 80;
                const top = target.getBoundingClientRect().top + window.scrollY - offset;
                window.scrollTo({ top, behavior: 'smooth' });
            }
        });
    });

    // --- FAQ Accordion Interactivity ---
    const faqCards = document.querySelectorAll('.faq-card');
    faqCards.forEach(card => {
        const trigger = card.querySelector('.faq-card-trigger');
        if (trigger) {
            trigger.addEventListener('click', () => {
                const isCollapsed = card.classList.contains('collapsed');
                if (isCollapsed) {
                    card.classList.remove('collapsed');
                    card.classList.add('active');
                    trigger.setAttribute('aria-expanded', 'true');
                    const ans = card.querySelector('.faq-answer-container');
                    if (ans) ans.style.maxHeight = (ans.scrollHeight + 30) + 'px';
                } else {
                    card.classList.add('collapsed');
                    card.classList.remove('active');
                    trigger.setAttribute('aria-expanded', 'false');
                    const ans = card.querySelector('.faq-answer-container');
                    if (ans) ans.style.maxHeight = '0px';
                }
            });
        }
    });

    // --- GSAP & ScrollTrigger Animations ---
    if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
        gsap.registerPlugin(ScrollTrigger);

        // Hero Entrance Timeline
        const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
        heroTl
            .from('.hero-badge-capsule', { y: -20, opacity: 0, duration: 0.6 })
            .from('.hero-title', { y: 35, opacity: 0, duration: 0.8 }, '-=0.4')
            .from('.hero-description', { y: 25, opacity: 0, duration: 0.7 }, '-=0.5')
            .from('.hero-cta-group', { y: 20, opacity: 0, duration: 0.6 }, '-=0.4')
            .from('.hero-stats', { y: 20, opacity: 0, duration: 0.6 }, '-=0.4')
            .from('.hero-interactive-studio', { scale: 0.96, y: 35, opacity: 0, duration: 0.9 }, '-=0.6');

        // Social Proof Cloud
        gsap.from('.logo-cloud-grid .company-badge', {
            scrollTrigger: {
                trigger: '.social-proof-section',
                start: 'top 88%',
                toggleActions: 'play none none none'
            },
            y: 20,
            opacity: 0,
            duration: 0.5,
            stagger: 0.08,
            ease: 'power2.out'
        });

        // Features Grid Cards
        gsap.from('.features-grid .feature-card', {
            scrollTrigger: {
                trigger: '.features-grid',
                start: 'top 85%',
                toggleActions: 'play none none none'
            },
            y: 40,
            opacity: 0,
            scale: 0.97,
            duration: 0.7,
            stagger: 0.1,
            ease: 'power3.out'
        });

        // 3-Step Workflow Cards
        gsap.from('.steps-grid .step-card', {
            scrollTrigger: {
                trigger: '.steps-grid',
                start: 'top 85%',
                toggleActions: 'play none none none'
            },
            y: 45,
            opacity: 0,
            duration: 0.75,
            stagger: 0.15,
            ease: 'power3.out'
        });

        gsap.from('.steps-grid .step-connector', {
            scrollTrigger: {
                trigger: '.steps-grid',
                start: 'top 85%',
                toggleActions: 'play none none none'
            },
            scale: 0.6,
            opacity: 0,
            duration: 0.5,
            stagger: 0.15,
            delay: 0.2,
            ease: 'back.out(1.7)'
        });

        // Comparison Table Rows
        gsap.from('.comparison-table tbody tr', {
            scrollTrigger: {
                trigger: '.comparison-table-wrapper',
                start: 'top 85%',
                toggleActions: 'play none none none'
            },
            x: -25,
            opacity: 0,
            duration: 0.5,
            stagger: 0.08,
            ease: 'power2.out'
        });

        // Starter Profiles
        gsap.from('.template-showcase .starter-card', {
            scrollTrigger: {
                trigger: '.template-showcase',
                start: 'top 85%',
                toggleActions: 'play none none none'
            },
            y: 45,
            opacity: 0,
            scale: 0.97,
            duration: 0.75,
            stagger: 0.14,
            ease: 'power3.out'
        });

        // FAQ Cards
        gsap.from('.faq-accordion-grid .faq-card', {
            scrollTrigger: {
                trigger: '.faq-accordion-grid',
                start: 'top 85%',
                toggleActions: 'play none none none'
            },
            y: 35,
            opacity: 0,
            duration: 0.65,
            stagger: 0.12,
            ease: 'power3.out'
        });

        // CTA Section Card
        gsap.from('.cta-card', {
            scrollTrigger: {
                trigger: '.cta-section',
                start: 'top 82%',
                toggleActions: 'play none none none'
            },
            scale: 0.94,
            y: 30,
            opacity: 0,
            duration: 0.8,
            ease: 'power3.out'
        });
    } else {
        // Fallback Intersection Observer if GSAP is unavailable
        const animateElements = document.querySelectorAll('[data-animate]');
        if (animateElements.length > 0) {
            const observer = new IntersectionObserver(
                (entries) => {
                    entries.forEach((entry, index) => {
                        if (entry.isIntersecting) {
                            setTimeout(() => {
                                entry.target.classList.add('visible');
                            }, index * 80);
                            observer.unobserve(entry.target);
                        }
                    });
                },
                { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
            );
            animateElements.forEach(el => observer.observe(el));
        }
    }

    // --- Launch Pre-filled Sample from Landing Page ---
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-launch-sample');
        if (btn) {
            e.preventDefault();
            const sampleId = btn.dataset.sampleId;
            if (typeof SAMPLE_RESUMES !== 'undefined') {
                const sample = SAMPLE_RESUMES.find(s => s.id === sampleId);
                if (sample) {
                    ResumeStore.load();
                    ResumeStore.createProfile(sample.name);
                    const cloned = JSON.parse(JSON.stringify(sample.data));
                    ResumeStore.set(cloned);
                    ResumeStore.save();
                    window.location.href = '/builder';
                    return;
                }
            }
            window.location.href = '/builder';
        }
    });

    // --- Hero Studio Showcase & Color Palette Switcher ---
    const themeTabs = document.querySelectorAll('.showcase-theme-tab');
    const showcaseDoc = document.getElementById('showcase-doc');
    const swatches = document.querySelectorAll('.swatch-btn');

    const themeColorMap = {
        contemporary: '#2563eb',
        modern: '#0d9488',
        minimalist: '#1e293b',
        harvard: '#881337'
    };

    if (themeTabs.length > 0 && showcaseDoc) {
        themeTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                themeTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const theme = tab.dataset.theme || 'contemporary';
                showcaseDoc.className = `studio-document-sheet theme-${theme}`;

                const mappedColor = themeColorMap[theme];
                if (mappedColor) {
                    showcaseDoc.style.setProperty('--doc-accent', mappedColor);
                    swatches.forEach(s => {
                        if (s.dataset.color === mappedColor) {
                            s.classList.add('active');
                        } else {
                            s.classList.remove('active');
                        }
                    });
                }
            });
        });
    }

    if (swatches.length > 0 && showcaseDoc) {
        swatches.forEach(swatch => {
            swatch.addEventListener('click', () => {
                swatches.forEach(s => s.classList.remove('active'));
                swatch.classList.add('active');
                const color = swatch.dataset.color || '#2563eb';
                showcaseDoc.style.setProperty('--doc-accent', color);
            });
        });
    }
});
