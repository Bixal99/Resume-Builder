// =============================================================================
// Review & Live ATS Keyword Matcher Component
// =============================================================================

const ReviewComponent = (() => {
    let lastJdText = '';

    function render(container) {
        const s = ResumeStore.get();
        const sections = [];

        // Personal
        sections.push(reviewSection('Personal Information', [
            ['Name', `${s.first_name || ''} ${s.last_name || ''}`.trim() || '—'],
            ['Title', s.professional_title || '—'],
            ['Email', s.email || '—'],
            ['Phone', s.phone || '—'],
            ['Address', s.address || '—'],
        ]));

        if (s.summary) sections.push(reviewSection('Summary', [['', s.summary.substring(0, 150) + (s.summary.length > 150 ? '...' : '')]]));

        if (s.experience.length) sections.push(reviewSection('Experience', s.experience.map(e => [e.position || 'Untitled', `${e.company || ''} ${e.start_date ? '· ' + e.start_date : ''}`])));
        if (s.education.length) sections.push(reviewSection('Education', s.education.map(e => [e.degree || 'Untitled', `${e.institution || ''}`])));
        if (s.projects.length) sections.push(reviewSection('Projects', s.projects.map(p => [p.title || 'Untitled', (p.technologies || []).join(', ')])));
        if (s.skills.length) sections.push(reviewSection('Skills', [[`${s.skills.length} skills`, s.skills.map(sk => sk.name).join(', ')]]));
        if (s.languages.length) sections.push(reviewSection('Languages', s.languages.map(l => [l.name, l.fluency || ''])));
        if (s.certifications.length) sections.push(reviewSection('Certifications', s.certifications.map(c => [c.name, c.issuer || ''])));

        container.innerHTML = `
            <h2 class="form-section-title">Review & ATS Check</h2>
            <p class="form-section-subtitle">Validate your resume and test it against applicant tracking system (ATS) filters.</p>

            <!-- ATS SCANNER CARD -->
            <div class="ats-scanner-card" style="background: var(--color-bg-subtle, #f8fafc); border: 1px solid var(--color-border); border-radius: var(--radius-lg, 12px); padding: var(--space-5, 20px); margin-bottom: var(--space-6, 24px);">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 20px;">🎯</span>
                        <h3 style="margin: 0; font-size: 16px; font-weight: 700; color: var(--color-text);">Live ATS Keyword Matcher</h3>
                    </div>
                    <span style="font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 6px; background: #ede9fe; color: #4338ca; border: 1px solid #c7d2fe;">Instant Analysis</span>
                </div>
                <p style="font-size: 13px; color: var(--color-text-secondary); margin-bottom: 12px; line-height: 1.4;">
                    Paste a job description below to calculate your keyword match score, uncover missing terms, and optimize for recruiter filters.
                </p>
                <div class="form-group" style="margin-bottom: 12px;">
                    <textarea id="ats-job-desc" class="form-input" rows="4" placeholder="Paste target job description, requirements, or qualifications here..." style="width: 100%; resize: vertical; font-size: 13px; line-height: 1.4;">${sanitizeHTML(lastJdText)}</textarea>
                </div>
                <div style="display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 16px;">
                    <button type="button" class="btn btn-secondary btn-sm" id="btn-clear-ats">Clear</button>
                    <button type="button" class="btn btn-primary btn-sm" id="btn-run-ats">Scan Job Description</button>
                </div>

                <!-- ATS RESULTS CONTAINER -->
                <div id="ats-results-wrapper">
                    ${lastJdText.trim() ? renderAtsResults(AtsScanner.analyze(lastJdText, ResumeStore.getResumeData())) : `
                        <div style="text-align: center; padding: 16px; color: var(--color-text-secondary); font-size: 13px; border: 1px dashed var(--color-border); border-radius: 8px;">
                            Paste a job description and click "Scan Job Description" to calculate your ATS readiness score.
                        </div>
                    `}
                </div>
            </div>

            <!-- REVIEW SECTIONS -->
            <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 12px; color: var(--color-text);">Resume Content Summary</h3>
            ${sections.join('')}

            <div style="text-align: center; margin-top: var(--space-8);">
                <p style="color: var(--color-success); font-weight: 600; font-size: var(--text-lg);">✅ Your resume is ready!</p>
                <p class="form-section-subtitle">Click "Next" to proceed to download, or go back to make changes.</p>
            </div>
        `;

        // Bind ATS event handlers
        const textarea = container.querySelector('#ats-job-desc');
        const btnRun = container.querySelector('#btn-run-ats');
        const btnClear = container.querySelector('#btn-clear-ats');
        const resultsWrapper = container.querySelector('#ats-results-wrapper');

        const doScan = () => {
            const text = textarea ? textarea.value : '';
            lastJdText = text;
            if (!text.trim()) {
                resultsWrapper.innerHTML = `
                    <div style="text-align: center; padding: 16px; color: var(--color-text-secondary); font-size: 13px; border: 1px dashed var(--color-border); border-radius: 8px;">
                        Paste a job description and click "Scan Job Description" to calculate your ATS readiness score.
                    </div>
                `;
                return;
            }

            if (typeof AtsScanner !== 'undefined') {
                const analysis = AtsScanner.analyze(text, ResumeStore.getResumeData());
                resultsWrapper.innerHTML = renderAtsResults(analysis);
            }
        };

        if (btnRun) btnRun.addEventListener('click', doScan);
        if (textarea) {
            textarea.addEventListener('input', debounce(() => {
                doScan();
            }, 600));
        }

        if (btnClear) {
            btnClear.addEventListener('click', () => {
                if (textarea) textarea.value = '';
                lastJdText = '';
                doScan();
            });
        }
    }

    function renderAtsResults(analysis) {
        if (!analysis) return '';

        const score = analysis.score || 0;
        const matched = analysis.matched || [];
        const missing = analysis.missing || [];
        const tips = analysis.tips || [];

        return `
            <div style="background: var(--color-bg, #ffffff); border: 1px solid var(--color-border); border-radius: 8px; padding: 16px;">
                <!-- SCORE HEADER -->
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--color-text-secondary); letter-spacing: 0.5px;">ATS Match Score</div>
                        <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 2px;">
                            <span style="font-size: 32px; font-weight: 800; color: ${analysis.ratingColor};">${score}%</span>
                            <span style="font-size: 14px; font-weight: 600; color: ${analysis.ratingColor};">${analysis.rating}</span>
                        </div>
                    </div>
                    <div style="flex: 1; max-width: 260px; min-width: 180px;">
                        <div style="height: 10px; border-radius: 5px; background: var(--color-border); overflow: hidden;">
                            <div style="height: 100%; width: ${score}%; background: ${analysis.ratingColor}; transition: width 0.4s ease;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--color-text-secondary); margin-top: 4px;">
                            <span>${matched.length} Matched</span>
                            <span>${missing.length} Missing</span>
                        </div>
                    </div>
                </div>

                <!-- KEYWORD BADGES -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                    <!-- MATCHED -->
                    <div style="padding: 10px 12px; background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 6px;">
                        <div style="font-size: 12px; font-weight: 700; color: var(--color-success, #10b981); margin-bottom: 8px; display: flex; align-items: center; gap: 4px;">
                            <span>✓ Matched Keywords (${matched.length})</span>
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px; max-height: 140px; overflow-y: auto;">
                            ${matched.length > 0 ? matched.map(m => `
                                <span style="font-size: 11px; font-weight: 500; background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; padding: 2px 8px; border-radius: 12px;">
                                    ${sanitizeHTML(m.keyword)} <strong style="opacity: 0.7;">×${m.count}</strong>
                                </span>
                            `).join('') : '<span style="font-size: 12px; color: var(--color-text-secondary);">No direct keywords matched yet.</span>'}
                        </div>
                    </div>

                    <!-- MISSING -->
                    <div style="padding: 10px 12px; background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 6px;">
                        <div style="font-size: 12px; font-weight: 700; color: var(--color-danger, #ef4444); margin-bottom: 8px; display: flex; align-items: center; gap: 4px;">
                            <span>! Missing Keywords (${missing.length})</span>
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px; max-height: 140px; overflow-y: auto;">
                            ${missing.length > 0 ? missing.map(m => `
                                <span style="font-size: 11px; font-weight: 500; background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; padding: 2px 8px; border-radius: 12px;" title="Frequently mentioned in job posting (${m.count}x)">
                                    + ${sanitizeHTML(m.keyword)}
                                </span>
                            `).join('') : '<span style="font-size: 12px; color: var(--color-success);">Great job! All top keywords are present in your resume.</span>'}
                        </div>
                    </div>
                </div>

                <!-- TIPS -->
                ${tips.length > 0 ? `
                    <div style="border-top: 1px solid var(--color-border); padding-top: 12px;">
                        <div style="font-size: 12px; font-weight: 700; color: var(--color-text); margin-bottom: 6px;">💡 Actionable Optimization Tips:</div>
                        <ul style="margin: 0; padding-left: 20px; font-size: 12px; color: var(--color-text-secondary); line-height: 1.5;">
                            ${tips.map(t => `<li>${sanitizeHTML(t)}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
    }

    function reviewSection(title, items) {
        return `
        <div class="review-section">
            <div class="review-section-header">
                <h3 class="review-section-title">${title}</h3>
            </div>
            ${items.map(([label, value]) => `
                <div class="review-item">
                    ${label ? `<span class="review-item-label">${sanitizeHTML(label)}</span>` : ''}
                    <span class="review-item-value">${sanitizeHTML(value || '—')}</span>
                </div>
            `).join('')}
        </div>`;
    }

    return { render };
})();
