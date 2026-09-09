// =============================================================================
// Live Preview Renderer & Page Budgeting Engine
// =============================================================================

const PreviewManager = (() => {
    let iframe = null;
    let zoomSelect = null;
    let updatePreview = null;
    let updatePageCount = null;
    let targetPages = 1; // Default target: 1-Page Budget

    function init() {
        iframe = document.getElementById('preview-iframe');
        zoomSelect = document.getElementById('preview-zoom');
        if (!iframe) return;

        // Target Page Toggle (1P vs 2P)
        const btnTarget1 = document.getElementById('target-1-page');
        const btnTarget2 = document.getElementById('target-2-page');

        if (btnTarget1 && btnTarget2) {
            btnTarget1.addEventListener('click', () => {
                targetPages = 1;
                btnTarget1.classList.add('active');
                btnTarget2.classList.remove('active');
                checkPageFullness();
            });
            btnTarget2.addEventListener('click', () => {
                targetPages = 2;
                btnTarget2.classList.add('active');
                btnTarget1.classList.remove('active');
                checkPageFullness();
            });
        }

        // Auto-Fit Content Button (Eliminates Page Budgeting Anxiety)
        const btnAutoFit = document.getElementById('btn-autofit-content');
        if (btnAutoFit) {
            btnAutoFit.addEventListener('click', autoFitContent);
        }

        function checkPageFullness() {
            if (!iframe) return;
            try {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                if (!doc) return;

                const pageEl = doc.querySelector('.resume-page') || doc.body;
                if (!pageEl) return;

                // Standard A4 height is ~1123px (297mm at 96 DPI)
                const pageHeight = 1123;
                const actualHeight = pageEl.scrollHeight || pageEl.offsetHeight;
                const totalTargetHeight = targetPages * pageHeight;
                const fullnessPct = Math.round((actualHeight / totalTargetHeight) * 100);

                const indicator = document.getElementById('preview-page-indicator');
                if (!indicator) return;

                indicator.style.display = 'inline-flex';

                if (actualHeight <= totalTargetHeight) {
                    indicator.className = 'page-fullness-badge optimal';
                    indicator.textContent = `${targetPages}P Budget: ${fullnessPct}% (Optimal)`;
                    indicator.title = `Your resume fits perfectly within the ${targetPages}-page budget.`;
                } else {
                    const overflowLines = Math.max(1, Math.round((actualHeight - totalTargetHeight) / 22));
                    indicator.className = 'page-fullness-badge overflow';
                    indicator.textContent = `⚠️ Spilling ~${overflowLines} line${overflowLines > 1 ? 's' : ''} (${fullnessPct}%)`;
                    indicator.title = `Resume is overflowing ${targetPages} page(s). Click "Auto-Fit Content" to automatically compress spacing.`;
                }
            } catch (e) {
                console.warn('Fullness check error:', e);
            }
        }

        function autoFitContent() {
            const doc = iframe?.contentDocument || iframe?.contentWindow?.document;
            const pageEl = doc?.querySelector('.resume-page') || doc?.body;
            const pageHeight = 1123;
            const actualHeight = pageEl ? (pageEl.scrollHeight || pageEl.offsetHeight) : 1200;
            const totalTargetHeight = targetPages * pageHeight;

            const currentTheme = ResumeStore.get('theme_settings') || {};

            if (actualHeight > totalTargetHeight) {
                // Determine how aggressively to compress
                const overflowPct = (actualHeight - totalTargetHeight) / totalTargetHeight;

                let newTheme = { ...currentTheme };

                if (overflowPct > 0.15) {
                    // Significant overflow: use compact margins, tight spacing, compact font scale
                    newTheme.section_spacing = 'compact';
                    newTheme.line_spacing = 'tight';
                    newTheme.font_size = 'compact';
                    newTheme.page_margin = 'compact';
                } else {
                    // Slight overflow (1-4 lines): compact spacing and tight line height
                    newTheme.section_spacing = 'compact';
                    newTheme.line_spacing = 'tight';
                    newTheme.font_size = 'normal';
                }

                ResumeStore.set('theme_settings', newTheme);
                ResumeStore.save();

                if (typeof showToast === 'function') {
                    showToast(`⚡ Auto-Fit applied! Balanced spacing & font scale to lock into ${targetPages} page(s).`, 'success');
                }
            } else if (actualHeight < totalTargetHeight * 0.75 && targetPages === 1) {
                // Plenty of room: can relax spacing
                const newTheme = {
                    ...currentTheme,
                    section_spacing: 'normal',
                    line_spacing: 'normal',
                    font_size: 'normal',
                    page_margin: 'normal'
                };
                ResumeStore.set('theme_settings', newTheme);
                ResumeStore.save();

                if (typeof showToast === 'function') {
                    showToast('Resume fits comfortably with standard spacing!', 'info');
                }
            } else {
                if (typeof showToast === 'function') {
                    showToast(`Resume already fits optimal within ${targetPages} page budget (${Math.round(actualHeight/totalTargetHeight*100)}%)!`, 'success');
                }
            }

            refresh();
        }

        updatePageCount = debounce(async (data) => {
            try {
                const res = await API.getPageCount(data);
                const pages = res.pages || 1;
                checkPageFullness();
            } catch (e) {
                console.warn('Page count update failed:', e);
            }
        }, 1200);

        let pendingHighlight = null;

        function applyHighlightToDoc(doc, fieldOrSection) {
            if (!doc || !fieldOrSection) return;
            
            // Ensure highlight CSS is present in iframe head
            if (!doc.getElementById('resumate-highlight-styles')) {
                const style = doc.createElement('style');
                style.id = 'resumate-highlight-styles';
                style.textContent = `
                    @keyframes templateFieldHighlight {
                        0% {
                            background-color: rgba(99, 102, 241, 0.32) !important;
                            outline: 2.5px solid #6366f1 !important;
                            box-shadow: 0 0 14px rgba(99, 102, 241, 0.4) !important;
                            border-radius: 4px;
                        }
                        50% {
                            background-color: rgba(16, 185, 129, 0.25) !important;
                            outline: 2.5px solid #10b981 !important;
                            box-shadow: 0 0 16px rgba(16, 185, 129, 0.45) !important;
                            border-radius: 4px;
                        }
                        100% {
                            background-color: transparent !important;
                            outline: 2.5px solid transparent !important;
                            box-shadow: none !important;
                        }
                    }
                    .template-field-highlight {
                        animation: templateFieldHighlight 2.4s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
                        position: relative;
                    }
                `;
                (doc.head || doc.body).appendChild(style);
            }

            let selector = '';
            switch (fieldOrSection) {
                case 'first_name':
                case 'last_name':
                    selector = '.resume-name, .header-content h1, .header-name';
                    break;
                case 'professional_title':
                    selector = '.resume-title, .header-content p, .header-title';
                    break;
                case 'email':
                    selector = 'a[href^="mailto:"], .contact-info, .header-contact';
                    break;
                case 'phone':
                case 'address':
                case 'location':
                case 'linkedin':
                case 'github':
                case 'portfolio':
                case 'website':
                    selector = '.contact-info, .header-contact';
                    break;
                case 'summary':
                    selector = '[data-section-type="summary"], .summary-text, .summary-section';
                    break;
                case 'experience':
                    selector = '[data-section-type="experience"], .experience-section';
                    break;
                case 'education':
                    selector = '[data-section-type="education"], .education-section';
                    break;
                case 'projects':
                    selector = '[data-section-type="projects"], .projects-section';
                    break;
                case 'skills':
                    selector = '[data-section-type="skills"], .skills-section';
                    break;
                case 'certifications':
                    selector = '[data-section-type="certifications"]';
                    break;
                case 'languages':
                    selector = '[data-section-type="languages"]';
                    break;
                default:
                    selector = `[data-section-type="${fieldOrSection}"]`;
            }

            const el = doc.querySelector(selector);
            if (el) {
                el.classList.remove('template-field-highlight');
                void el.offsetWidth;
                el.classList.add('template-field-highlight');
                try {
                    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } catch (e) {}
                setTimeout(() => {
                    if (el) el.classList.remove('template-field-highlight');
                }, 2500);
            }
        }

        function highlightField(fieldOrSection) {
            pendingHighlight = fieldOrSection;
            if (!iframe) return;
            try {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                if (doc) {
                    applyHighlightToDoc(doc, fieldOrSection);
                }
            } catch (e) {
                console.warn('Highlight field error:', e);
            }
        }

        updatePreview = debounce(async () => {
            try {
                const data = ResumeStore.getResumeData();
                const html = await API.getPreview(data);
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                doc.open();
                doc.write(html);
                doc.close();

                attachExternalLinkDelegation(doc);

                // Check fullness as soon as iframe document parses
                setTimeout(() => {
                    checkPageFullness();
                }, 100);

                // Re-apply any pending highlight to newly rendered template
                if (pendingHighlight) {
                    const currentHighlight = pendingHighlight;
                    setTimeout(() => {
                        const newDoc = iframe.contentDocument || iframe.contentWindow.document;
                        if (newDoc) {
                            applyHighlightToDoc(newDoc, currentHighlight);
                        }
                    }, 50);
                }

                updatePageCount(data);
            } catch (e) {
                console.warn('Preview update failed:', e);
            }
        }, 350);

        // Subscribe to store changes
        ResumeStore.subscribe(() => updatePreview());

        // Zoom control
        const applyZoom = () => {
            if (!zoomSelect || !iframe) return;
            const wrapper = document.getElementById('preview-iframe-wrapper');
            let scale = 1;
            
            if (zoomSelect.value === 'auto') {
                const container = document.getElementById('preview-container');
                const cw = container.clientWidth;
                scale = Math.min(1.2, Math.max(0.3, (cw - 40) / 794));
            } else {
                scale = parseFloat(zoomSelect.value);
            }
            
            iframe.style.transform = `scale(${scale})`;
            if (wrapper) {
                wrapper.style.width = `calc(210mm * ${scale})`;
                wrapper.style.minHeight = `calc(297mm * ${scale})`;
            }
        };

        if (zoomSelect) {
            zoomSelect.addEventListener('change', applyZoom);
            window.addEventListener('resize', debounce(applyZoom, 100));
        }

        // Initial preview
        updatePreview();
        setTimeout(applyZoom, 50);

        // Expose highlightField on PreviewManager object
        PreviewManager.highlightField = highlightField;
        PreviewManager.prepareForLiveExtraction = prepareForLiveExtraction;
        PreviewManager.updateFieldDirectly = updateFieldDirectly;
        PreviewManager.updateSectionDirectly = updateSectionDirectly;

        function injectHighlightStyles(doc) {
            if (!doc) return;
            if (!doc.getElementById('resumate-highlight-styles')) {
                const style = doc.createElement('style');
                style.id = 'resumate-highlight-styles';
                style.textContent = `
                    @keyframes templateFieldHighlight {
                        0% {
                            background-color: rgba(99, 102, 241, 0.35) !important;
                            outline: 2.5px solid #6366f1 !important;
                            box-shadow: 0 0 16px rgba(99, 102, 241, 0.45) !important;
                            border-radius: 4px;
                        }
                        50% {
                            background-color: rgba(16, 185, 129, 0.28) !important;
                            outline: 2.5px solid #10b981 !important;
                            box-shadow: 0 0 18px rgba(16, 185, 129, 0.5) !important;
                            border-radius: 4px;
                        }
                        100% {
                            background-color: transparent !important;
                            outline: 2.5px solid transparent !important;
                            box-shadow: none !important;
                        }
                    }
                    .template-field-highlight {
                        animation: templateFieldHighlight 2.4s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
                        position: relative;
                    }
                    @keyframes liveShimmer {
                        0% { background-position: -200% 0; }
                        100% { background-position: 200% 0; }
                    }
                    .live-slot-placeholder {
                        background: linear-gradient(90deg, rgba(99, 102, 241, 0.05) 0%, rgba(99, 102, 241, 0.16) 50%, rgba(99, 102, 241, 0.05) 100%);
                        background-size: 200% 100%;
                        animation: liveShimmer 2s infinite linear;
                        border: 1.5px dashed rgba(99, 102, 241, 0.38);
                        border-radius: 6px;
                        padding: 8px 14px;
                        margin-bottom: 12px;
                        color: #6366f1;
                        font-size: 0.85rem;
                        font-weight: 500;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        transition: all 0.35s ease;
                    }
                    .live-slot-placeholder.slot-name {
                        height: 38px;
                        font-size: 1.2rem;
                        font-weight: 700;
                    }
                    .live-slot-placeholder.slot-title {
                        height: 26px;
                        font-size: 0.95rem;
                        width: 60%;
                    }
                    .live-slot-placeholder.slot-contact {
                        height: 24px;
                        font-size: 0.8rem;
                        width: 85%;
                    }
                    .live-slot-placeholder.slot-section {
                        min-height: 48px;
                    }
                `;
                (doc.head || doc.body).appendChild(style);
            }
        }

        function escapeDocHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        function formatBulletsToHtml(text) {
            if (!text) return '';
            const lines = String(text).split('\n').map(l => l.trim()).filter(Boolean);
            const hasBullets = lines.some(l => l.startsWith('-') || l.startsWith('•') || l.startsWith('*'));
            if (hasBullets) {
                const items = lines.map(l => `<li>${escapeDocHtml(l.replace(/^[-•*]\s*/, ''))}</li>`).join('');
                return `<ul class="entry-list">${items}</ul>`;
            }
            return lines.map(l => `<p>${escapeDocHtml(l)}</p>`).join('');
        }

        function renderDocExperienceEntry(exp) {
            const title = escapeDocHtml(exp.position || exp.title || '');
            const company = escapeDocHtml(exp.company || '');
            const loc = exp.location ? ` · ${escapeDocHtml(exp.location)}` : '';
            const dateRange = `${exp.start_date || ''}${exp.start_date ? ' – ' : ''}${exp.is_current ? 'Present' : (exp.end_date || '')}`;
            
            let bulletsHtml = '';
            if (Array.isArray(exp.achievements) && exp.achievements.length > 0) {
                bulletsHtml = `<ul class="entry-list">${exp.achievements.map(a => `<li>${escapeDocHtml(a)}</li>`).join('')}</ul>`;
            } else if (exp.description) {
                bulletsHtml = `<div class="entry-description">${formatBulletsToHtml(exp.description)}</div>`;
            }
            
            return `
                <div class="entry">
                    <div class="entry-header">
                        <div class="entry-left">
                            <h3 class="entry-title">${title}</h3>
                            <p class="entry-subtitle">${company}${loc}</p>
                        </div>
                        <div class="entry-right">
                            <span class="entry-date">${dateRange}</span>
                        </div>
                    </div>
                    ${bulletsHtml}
                </div>
            `;
        }

        function renderDocEducationEntry(edu) {
            let d = (edu.degree || '').trim();
            let f = (edu.field_of_study || '').trim();
            if (d && (!f || !f.trim())) {
                const mIn = d.match(/^(.*?)\s+in\s+(.+)$/i);
                if (mIn) {
                    d = mIn[1].trim().replace(/[,.;]+$/, '');
                    f = mIn[2].trim().replace(/[,.;]+$/, '');
                } else {
                    const mDash = d.match(/^(.*?)\s+[-–—]\s+(.+)$/);
                    if (mDash) {
                        d = mDash[1].trim().replace(/[,.;]+$/, '');
                        f = mDash[2].trim().replace(/[,.;]+$/, '');
                    }
                }
            }
            const degree = escapeDocHtml(d);
            const field = f ? ` in ${escapeDocHtml(f)}` : '';
            const inst = escapeDocHtml(edu.institution || '');
            const loc = edu.location ? ` · ${escapeDocHtml(edu.location)}` : '';
            const dateRange = `${edu.start_date || ''}${edu.start_date ? ' – ' : ''}${edu.is_current ? 'Present' : (edu.end_date || '')}`;
            const grade = edu.grade ? `<span class="entry-badge">${escapeDocHtml(edu.grade)}</span>` : '';
            
            return `
                <div class="entry">
                    <div class="entry-header">
                        <div class="entry-left">
                            <h3 class="entry-title">${degree}${field}</h3>
                            <p class="entry-subtitle">${inst}${loc}</p>
                        </div>
                        <div class="entry-right">
                            <span class="entry-date">${dateRange}</span>
                            ${grade}
                        </div>
                    </div>
                    ${edu.description ? `<div class="entry-description">${formatBulletsToHtml(edu.description)}</div>` : ''}
                </div>
            `;
        }

        function formatExternalUrl(url) {
            if (!url) return '';
            url = String(url).trim();
            if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('mailto:') || url.startsWith('tel:')) {
                return url;
            }
            return 'https://' + url;
        }

        function attachExternalLinkDelegation(targetDoc) {
            if (!targetDoc || targetDoc._linkDelegationAttached) return;
            targetDoc._linkDelegationAttached = true;
            targetDoc.addEventListener('click', (e) => {
                const a = e.target.closest('a');
                if (!a) return;
                const href = a.getAttribute('href');
                if (!href || href === '#' || href.startsWith('javascript:')) return;
                if (href.startsWith('mailto:') || href.startsWith('tel:')) return;
                
                e.preventDefault();
                e.stopPropagation();
                let safeUrl = href.trim();
                if (!safeUrl.startsWith('http://') && !safeUrl.startsWith('https://')) {
                    safeUrl = 'https://' + safeUrl;
                }
                window.open(safeUrl, '_blank', 'noopener,noreferrer');
            }, true);
        }

        function normalizePreviewSkillCategory(cat) {
            if (!cat) return 'Technical Skills';
            const c = String(cat).trim().replace(/[:]+$/, '').toLowerCase();
            if (['technical', 'technical skills', 'skills', 'tech', 'programming', 'languages', 'programming languages', 'coding', 'core competencies', 'technical proficiencies'].includes(c)) {
                return 'Technical Skills';
            }
            if (['framework', 'frameworks', 'libraries', 'frameworks & libraries', 'frameworks and libraries', 'frameworks & tools', 'framework & library'].includes(c)) {
                return 'Frameworks & Libraries';
            }
            if (['tool', 'tools', 'tools & platforms', 'tools and platforms', 'platforms', 'developer tools', 'technologies', 'devops', 'software', 'environment'].includes(c)) {
                return 'Tools & Platforms';
            }
            if (['soft', 'soft skills', 'interpersonal', 'interpersonal skills', 'professional skills', 'management'].includes(c)) {
                return 'Soft Skills';
            }
            return String(cat).trim().replace(/[:]+$/, '');
        }

        function formatSkillCategoryTitle(cat) {
            const raw = escapeDocHtml(cat).replace(/[:]+$/, '');
            if (raw.toLowerCase() === 'frameworks &amp; libraries' || raw.toLowerCase() === 'frameworks & libraries') {
                return 'Frameworks &amp;<br>Libraries:';
            }
            if (raw.toLowerCase() === 'tools &amp; platforms' || raw.toLowerCase() === 'tools & platforms' || raw.toLowerCase() === 'tools') {
                return 'Tools &amp;<br>Platforms:';
            }
            return `${raw}:`;
        }

        function renderDocSkillsHtml(skills) {
            if (!Array.isArray(skills) || skills.length === 0) return '';
            const categories = {};
            const seenSkills = new Set();
            skills.forEach(s => {
                const name = typeof s === 'string' ? s : (s.name || '');
                if (!name || !name.trim()) return;
                const trimmedName = name.trim();
                const lowerName = trimmedName.toLowerCase();
                if (seenSkills.has(lowerName)) return;
                seenSkills.add(lowerName);

                const rawCat = (typeof s === 'object' && s.category) ? s.category : 'Technical Skills';
                const cat = normalizePreviewSkillCategory(rawCat);

                if (!categories[cat]) categories[cat] = [];
                categories[cat].push(trimmedName);
            });
            
            return `
                <div class="skills-grid">
                    ${Object.entries(categories).map(([cat, names]) => `
                        <div class="skill-category">
                            <h4 class="skill-category-title">${formatSkillCategoryTitle(cat)}</h4>
                            <div class="skill-tags">
                                ${names.map(n => `<span class="tag">${escapeDocHtml(n)}</span>`).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        function renderDocProjectEntry(proj) {
            const title = escapeDocHtml(proj.title || '');
            const gh = proj.github_url ? `<a href="${escapeDocHtml(formatExternalUrl(proj.github_url))}" class="entry-link" target="_blank" rel="noopener noreferrer">GitHub</a>` : '';
            const live = proj.live_url ? `<a href="${escapeDocHtml(formatExternalUrl(proj.live_url))}" class="entry-link" target="_blank" rel="noopener noreferrer">Live</a>` : '';
            const dateSpan = proj.date ? `<div class="entry-right"><span class="entry-date">${escapeDocHtml(proj.date)}</span></div>` : '';
            const techTags = Array.isArray(proj.technologies) && proj.technologies.length > 0
                ? `<div class="tech-tags">${proj.technologies.map(t => `<span class="tag">${escapeDocHtml(t)}</span>`).join('')}</div>`
                : '';
            const highlights = Array.isArray(proj.highlights) && proj.highlights.length > 0
                ? `<ul class="entry-list">${proj.highlights.map(h => `<li>${escapeDocHtml(h)}</li>`).join('')}</ul>`
                : (proj.description ? `<div class="entry-description">${formatBulletsToHtml(proj.description)}</div>` : '');
            
            return `
                <div class="entry">
                    <div class="entry-header">
                        <div class="entry-left">
                            <h3 class="entry-title">${title} ${gh} ${live}</h3>
                        </div>
                        ${dateSpan}
                    </div>
                    ${techTags}
                    ${highlights}
                </div>
            `;
        }

        function renderDocCertificationEntry(cert) {
            const name = escapeDocHtml(cert.name || '');
            const issuer = cert.issuer ? ` · ${escapeDocHtml(cert.issuer)}` : '';
            const date = cert.date || '';
            return `
                <div class="entry">
                    <div class="entry-header">
                        <div class="entry-left"><h3 class="entry-title">${name}</h3><p class="entry-subtitle">${issuer}</p></div>
                        <div class="entry-right"><span class="entry-date">${date}</span></div>
                    </div>
                </div>
            `;
        }

        function renderDocLanguagesHtml(languages) {
            if (!Array.isArray(languages)) return '';
            return `
                <div class="languages-list" style="display: flex; flex-wrap: wrap; gap: 8px;">
                    ${languages.map(l => `<span class="tag">${escapeDocHtml(l.name || '')}${l.fluency ? ` (${escapeDocHtml(l.fluency)})` : ''}</span>`).join('')}
                </div>
            `;
        }

        function triggerElHighlight(el) {
            if (!el) return;
            el.classList.remove('template-field-highlight');
            void el.offsetWidth;
            el.classList.add('template-field-highlight');
            try {
                el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } catch (e) {}
            setTimeout(() => {
                if (el) el.classList.remove('template-field-highlight');
            }, 2500);
        }

        function prepareForLiveExtraction() {
            if (!iframe) return;
            try {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                if (!doc) return;
                injectHighlightStyles(doc);

                let page = doc.querySelector('.resume-page');
                if (!page) {
                    page = doc.createElement('div');
                    page.className = 'resume-page';
                    page.setAttribute('data-page-size', 'A4');
                    doc.body.innerHTML = '';
                    doc.body.appendChild(page);
                }

                let header = page.querySelector('.resume-header');
                if (!header) {
                    header = doc.createElement('header');
                    header.className = 'resume-header';
                    page.insertBefore(header, page.firstChild);
                }

                let headerContent = header.querySelector('.header-content');
                if (!headerContent) {
                    headerContent = doc.createElement('div');
                    headerContent.className = 'header-content';
                    header.appendChild(headerContent);
                }

                // If no name currently, show clean placeholder slots
                if (!headerContent.querySelector('.resume-name')) {
                    headerContent.innerHTML = `
                        <div class="live-slot-placeholder slot-name" data-slot="name">
                            <span class="slot-shimmer">⚡ Extracting Name...</span>
                        </div>
                        <div class="live-slot-placeholder slot-title" data-slot="title">
                            <span class="slot-shimmer">⚡ Extracting Professional Title...</span>
                        </div>
                        <div class="live-slot-placeholder slot-contact" data-slot="contact">
                            <span class="slot-shimmer">⚡ Extracting Contact & Links...</span>
                        </div>
                    `;
                }

                // Placeholder for Summary
                if (!page.querySelector('[data-section-type="summary"]')) {
                    const sumSlot = doc.createElement('div');
                    sumSlot.className = 'live-slot-placeholder slot-section';
                    sumSlot.setAttribute('data-slot', 'summary');
                    sumSlot.innerHTML = `<span class="slot-shimmer">⚡ Extracting Professional Summary...</span>`;
                    page.appendChild(sumSlot);
                }

                // Placeholder for Experience
                if (!page.querySelector('[data-section-type="experience"]')) {
                    const expSlot = doc.createElement('div');
                    expSlot.className = 'live-slot-placeholder slot-section';
                    expSlot.setAttribute('data-slot', 'experience');
                    expSlot.innerHTML = `<span class="slot-shimmer">⚡ Extracting Work Experience & STAR Bullets...</span>`;
                    page.appendChild(expSlot);
                }

                // Placeholder for Education
                if (!page.querySelector('[data-section-type="education"]')) {
                    const eduSlot = doc.createElement('div');
                    eduSlot.className = 'live-slot-placeholder slot-section';
                    eduSlot.setAttribute('data-slot', 'education');
                    eduSlot.innerHTML = `<span class="slot-shimmer">⚡ Extracting Education...</span>`;
                    page.appendChild(eduSlot);
                }

                // Placeholder for Skills
                if (!page.querySelector('[data-section-type="skills"]')) {
                    const sklSlot = doc.createElement('div');
                    sklSlot.className = 'live-slot-placeholder slot-section';
                    sklSlot.setAttribute('data-slot', 'skills');
                    sklSlot.innerHTML = `<span class="slot-shimmer">⚡ Extracting Technical Skills...</span>`;
                    page.appendChild(sklSlot);
                }
            } catch (e) {
                console.warn('prepareForLiveExtraction error:', e);
            }
        }

        function updateFieldDirectly(field, value) {
            if (!iframe || !field || !value) return;
            try {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                if (!doc) return;
                injectHighlightStyles(doc);

                const page = doc.querySelector('.resume-page') || doc.body;
                let header = doc.querySelector('.resume-header');
                if (!header) {
                    header = doc.createElement('header');
                    header.className = 'resume-header';
                    page.insertBefore(header, page.firstChild);
                }
                let headerContent = header.querySelector('.header-content');
                if (!headerContent) {
                    headerContent = doc.createElement('div');
                    headerContent.className = 'header-content';
                    header.appendChild(headerContent);
                }

                // Helper to remove placeholder slot if present
                const removeSlot = (slotName) => {
                    const slot = doc.querySelector(`.live-slot-placeholder[data-slot="${slotName}"]`);
                    if (slot) slot.remove();
                };

                if (field === 'first_name' || field === 'last_name') {
                    removeSlot('name');
                    const storeState = (typeof ResumeStore !== 'undefined') ? ResumeStore.get() : {};
                    const fullName = [storeState.first_name || '', storeState.last_name || ''].filter(Boolean).join(' ') || value;
                    
                    let nameEl = headerContent.querySelector('.resume-name, .header-name, h1');
                    if (!nameEl) {
                        nameEl = doc.createElement('h1');
                        nameEl.className = 'resume-name';
                        headerContent.insertBefore(nameEl, headerContent.firstChild);
                    }
                    nameEl.textContent = fullName;
                    triggerElHighlight(nameEl);
                } else if (field === 'professional_title') {
                    removeSlot('title');
                    let titleEl = headerContent.querySelector('.resume-title, .header-title, p.resume-title');
                    if (!titleEl) {
                        titleEl = doc.createElement('p');
                        titleEl.className = 'resume-title';
                        const nameEl = headerContent.querySelector('.resume-name, .header-name, h1');
                        if (nameEl && nameEl.nextSibling) {
                            headerContent.insertBefore(titleEl, nameEl.nextSibling);
                        } else {
                            headerContent.appendChild(titleEl);
                        }
                    }
                    titleEl.textContent = value;
                    triggerElHighlight(titleEl);
                } else if (['email', 'phone', 'address', 'linkedin', 'github', 'portfolio', 'website'].includes(field)) {
                    removeSlot('contact');
                    let contactContainer = headerContent.querySelector('.contact-info, .header-contact');
                    if (!contactContainer) {
                        contactContainer = doc.createElement('div');
                        contactContainer.className = 'contact-info';
                        headerContent.appendChild(contactContainer);
                    }

                    // Check if item for this field already exists
                    let item = contactContainer.querySelector(`.contact-item[data-field="${field}"]`);
                    if (!item) {
                        item = doc.createElement('span');
                        item.className = 'contact-item';
                        item.setAttribute('data-field', field);
                        contactContainer.appendChild(item);
                    }

                    // Icon map
                    const iconSvgMap = {
                        email: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
                        phone: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
                        address: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
                        linkedin: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>',
                        github: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>',
                        portfolio: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
                        website: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'
                    };

                    const icon = iconSvgMap[field] || '';
                    if (field === 'email') {
                        item.innerHTML = `${icon}<a href="mailto:${escapeDocHtml(value)}">${escapeDocHtml(value)}</a>`;
                    } else if (['linkedin', 'github', 'portfolio', 'website'].includes(field)) {
                        const label = field.charAt(0).toUpperCase() + field.slice(1);
                        const safeUrl = formatExternalUrl(value);
                        item.innerHTML = `${icon}<a href="${escapeDocHtml(safeUrl)}" target="_blank" rel="noopener noreferrer">${label}</a>`;
                    } else {
                        item.innerHTML = `${icon}${escapeDocHtml(value)}`;
                    }
                    attachExternalLinkDelegation(doc);
                    triggerElHighlight(item);
                } else if (field === 'summary') {
                    removeSlot('summary');
                    let sumSec = page.querySelector('[data-section-type="summary"]');
                    if (!sumSec) {
                        sumSec = doc.createElement('section');
                        sumSec.className = 'resume-section';
                        sumSec.setAttribute('data-section-type', 'summary');
                        sumSec.innerHTML = `
                            <h2 class="section-title">Professional Summary</h2>
                            <div class="section-content">
                                <div class="summary-text"></div>
                            </div>
                        `;
                        const nextSec = page.querySelector('.resume-section');
                        if (nextSec) {
                            page.insertBefore(sumSec, nextSec);
                        } else {
                            page.appendChild(sumSec);
                        }
                    }
                    const textEl = sumSec.querySelector('.summary-text') || sumSec;
                    textEl.innerHTML = formatBulletsToHtml(value);
                    triggerElHighlight(sumSec);
                }
            } catch (e) {
                console.warn('updateFieldDirectly error:', e);
            }
        }

        function updateSectionDirectly(section, data) {
            if (!iframe || !section || !Array.isArray(data) || data.length === 0) return;
            try {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                if (!doc) return;
                injectHighlightStyles(doc);

                const page = doc.querySelector('.resume-page') || doc.body;
                
                // Remove placeholder slot for this section
                const slot = doc.querySelector(`.live-slot-placeholder[data-slot="${section}"]`);
                if (slot) slot.remove();

                const sectionTitles = {
                    experience: 'Work Experience',
                    education: 'Education',
                    projects: 'Projects',
                    skills: 'Skills',
                    certifications: 'Certifications',
                    languages: 'Languages',
                    awards: 'Honors & Awards',
                    volunteer: 'Volunteer Experience',
                    references: 'References'
                };

                let secEl = page.querySelector(`[data-section-type="${section}"]`);
                if (!secEl) {
                    secEl = doc.createElement('section');
                    secEl.className = 'resume-section';
                    secEl.setAttribute('data-section-type', section);
                    page.appendChild(secEl);
                }

                const title = sectionTitles[section] || (section.charAt(0).toUpperCase() + section.slice(1));
                let innerContent = '';

                if (section === 'experience') {
                    innerContent = data.map(renderDocExperienceEntry).join('');
                } else if (section === 'education') {
                    innerContent = data.map(renderDocEducationEntry).join('');
                } else if (section === 'skills') {
                    // If skills were already placed live one-by-one, ensure missing ones are added
                    const existingTags = secEl.querySelectorAll('.skill-tags .tag');
                    if (existingTags.length >= data.length && data.length > 0) {
                        triggerElHighlight(secEl);
                        return;
                    }
                    innerContent = renderDocSkillsHtml(data);
                } else if (section === 'projects') {
                    innerContent = data.map(renderDocProjectEntry).join('');
                } else if (section === 'certifications') {
                    innerContent = data.map(renderDocCertificationEntry).join('');
                } else if (section === 'languages') {
                    innerContent = renderDocLanguagesHtml(data);
                } else {
                    innerContent = data.map(item => `
                        <div class="entry">
                            <h3 class="entry-title">${escapeDocHtml(item.title || item.name || item.role || item.organization || '')}</h3>
                            ${item.description ? `<div class="entry-description">${escapeDocHtml(item.description)}</div>` : ''}
                        </div>
                    `).join('');
                }

                secEl.innerHTML = `
                    <h2 class="section-title">${title}</h2>
                    <div class="section-content">${innerContent}</div>
                `;

                attachExternalLinkDelegation(doc);
                triggerElHighlight(secEl);
            } catch (e) {
                console.warn('updateSectionDirectly error:', e);
            }
        }

        function addSkillDirectly(skill) {
            if (!iframe || !skill) return;
            try {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                if (!doc) return;
                injectHighlightStyles(doc);

                const page = doc.querySelector('.resume-page') || doc.body;

                // Remove placeholder slot for skills
                const slot = doc.querySelector('.live-slot-placeholder[data-slot="skills"]');
                if (slot) slot.remove();

                let secEl = page.querySelector('[data-section-type="skills"]');
                if (!secEl) {
                    secEl = doc.createElement('section');
                    secEl.className = 'resume-section';
                    secEl.setAttribute('data-section-type', 'skills');
                    secEl.innerHTML = `
                        <h2 class="section-title">Skills</h2>
                        <div class="section-content">
                            <div class="skills-grid"></div>
                        </div>
                    `;
                    page.appendChild(secEl);
                }

                let skillsGrid = secEl.querySelector('.skills-grid');
                if (!skillsGrid) {
                    let content = secEl.querySelector('.section-content');
                    if (!content) {
                        content = doc.createElement('div');
                        content.className = 'section-content';
                        secEl.appendChild(content);
                    }
                    skillsGrid = doc.createElement('div');
                    skillsGrid.className = 'skills-grid';
                    content.appendChild(skillsGrid);
                }

                const sName = typeof skill === 'string' ? skill : (skill.name || '');
                if (!sName || !sName.trim()) return;

                let category = normalizePreviewSkillCategory((typeof skill === 'object' && skill.category) ? skill.category : 'Technical Skills');

                const displayCat = category.replace(/_/g, ' ');

                // Find or create category container
                let catEl = null;
                const catHeaders = skillsGrid.querySelectorAll('.skill-category-title');
                catHeaders.forEach(h => {
                    const text = h.textContent.replace(/[:]+$/, '').replace(/\s+/g, ' ').trim().toLowerCase();
                    const targetText = displayCat.replace(/\s+/g, ' ').trim().toLowerCase();
                    if (text === targetText || text === category.toLowerCase() || text.includes(targetText)) {
                        catEl = h.closest('.skill-category');
                    }
                });

                if (!catEl) {
                    catEl = doc.createElement('div');
                    catEl.className = 'skill-category';
                    catEl.innerHTML = `
                        <h4 class="skill-category-title">${formatSkillCategoryTitle(displayCat)}</h4>
                        <div class="skill-tags"></div>
                    `;
                    skillsGrid.appendChild(catEl);
                }

                let tagsContainer = catEl.querySelector('.skill-tags');
                if (!tagsContainer) {
                    tagsContainer = doc.createElement('div');
                    tagsContainer.className = 'skill-tags';
                    catEl.appendChild(tagsContainer);
                }

                // Avoid duplicate tags
                const existingTags = tagsContainer.querySelectorAll('.tag');
                for (let t of existingTags) {
                    if (t.textContent.trim().toLowerCase() === sName.trim().toLowerCase()) {
                        return;
                    }
                }

                // Add new skill tag with live highlight animation
                const newTag = doc.createElement('span');
                newTag.className = 'tag template-field-highlight';
                newTag.textContent = sName.trim();
                tagsContainer.appendChild(newTag);

                try {
                    newTag.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } catch (e) {}

                setTimeout(() => {
                    if (newTag) newTag.classList.remove('template-field-highlight');
                }, 2500);
            } catch (e) {
                console.warn('addSkillDirectly error:', e);
            }
        }

        PreviewManager.prepareForLiveExtraction = prepareForLiveExtraction;
        PreviewManager.updateFieldDirectly = updateFieldDirectly;
        PreviewManager.updateSectionDirectly = updateSectionDirectly;
        PreviewManager.addSkillDirectly = addSkillDirectly;
        PreviewManager.highlightField = triggerElHighlight;
    }

    function refresh() { if (updatePreview) updatePreview(); }

    return { 
        init, 
        refresh,
        prepareForLiveExtraction: () => {
            if (PreviewManager.prepareForLiveExtraction) {
                PreviewManager.prepareForLiveExtraction();
            }
        },
        updateFieldDirectly: (field, value) => {
            if (PreviewManager.updateFieldDirectly) {
                PreviewManager.updateFieldDirectly(field, value);
            }
        },
        updateSectionDirectly: (section, data) => {
            if (PreviewManager.updateSectionDirectly) {
                PreviewManager.updateSectionDirectly(section, data);
            }
        },
        addSkillDirectly: (skill) => {
            if (PreviewManager.addSkillDirectly) {
                PreviewManager.addSkillDirectly(skill);
            }
        },
        highlightField: (field) => {
            if (PreviewManager.highlightField) {
                PreviewManager.highlightField(field);
            }
        }
    };
})();
