// =============================================================================
// Professional Summary Component
// =============================================================================

const SummaryComponent = (() => {
    const MAX_CHARS = 500;

    function render(container) {
        const s = ResumeStore.get();
        const len = (s.summary || '').length;
        const cls = len > MAX_CHARS ? 'danger' : len > MAX_CHARS * 0.8 ? 'warning' : '';

        container.innerHTML = `
            <h2 class="form-section-title">Professional Summary</h2>
            <p class="form-section-subtitle">Write a brief 2-4 sentence summary highlighting your key qualifications.</p>
            <div class="form-group">
                <textarea class="form-textarea" id="summary" rows="6" placeholder="Results-driven software engineer with 5+ years of experience building scalable web applications...">${sanitizeHTML(s.summary || '')}</textarea>
                <div class="char-counter ${cls}">${len} / ${MAX_CHARS}</div>
            </div>
            <div class="form-hint" style="margin-top: var(--space-4);">
                <strong>Tips:</strong> Keep it concise, mention your years of experience, key skills, and what value you bring.
            </div>
        `;

        const textarea = container.querySelector('#summary');
        textarea.addEventListener('input', debounce(() => {
            ResumeStore.set('summary', textarea.value);
            const l = textarea.value.length;
            const counter = container.querySelector('.char-counter');
            counter.textContent = `${l} / ${MAX_CHARS}`;
            counter.className = `char-counter ${l > MAX_CHARS ? 'danger' : l > MAX_CHARS * 0.8 ? 'warning' : ''}`;
        }, 300));
    }

    return { render };
})();
