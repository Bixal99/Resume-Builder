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

    // --- Intersection Observer for scroll animations ---
    const animateElements = document.querySelectorAll('[data-animate]');
    if (animateElements.length > 0) {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry, index) => {
                    if (entry.isIntersecting) {
                        // Stagger the animation delay
                        setTimeout(() => {
                            entry.target.classList.add('visible');
                        }, index * 100);
                        observer.unobserve(entry.target);
                    }
                });
            },
            {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px',
            }
        );

        animateElements.forEach(el => observer.observe(el));
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
});
