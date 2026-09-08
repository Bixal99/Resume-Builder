// =============================================================================
// Template Selector Component
// =============================================================================

const TemplateSelectorComponent = (() => {
    const templates = [
        { 
            id: 'modern', 
            name: 'Modern Professional', 
            thumb: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><line x1="8" y1="6" x2="16" y2="6" stroke-width="2"/><line x1="8" y1="10" x2="12" y2="10"/><line x1="8" y1="14" x2="16" y2="14"/><line x1="8" y1="18" x2="14" y2="18"/></svg>' 
        },
        { 
            id: 'executive', 
            name: 'Executive Elegance', 
            thumb: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="1"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="13" y1="7" x2="18" y2="7"/><line x1="13" y1="11" x2="16" y2="11"/><line x1="13" y1="15" x2="17" y2="15"/></svg>' 
        },
        { 
            id: 'contemporary', 
            name: 'Contemporary Clean', 
            thumb: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="4" y="2" width="16" height="20" rx="2"/><circle cx="12" cy="7" r="2"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="8" y1="16" x2="14" y2="16"/></svg>' 
        },
        { 
            id: 'ats', 
            name: 'Minimal ATS', 
            thumb: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>' 
        },
        { 
            id: 'tech', 
            name: 'Premium Tech', 
            thumb: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 8l2 2-2 2"/><line x1="12" y1="12" x2="16" y2="12"/><line x1="8" y1="16" x2="16" y2="16"/></svg>' 
        }
    ];

    function render(container) {
        const current = ResumeStore.get('template_id') || 'modern';
        
        const cardsHtml = templates.map(t => `
            <div class="template-card ${current === t.id ? 'selected' : ''}" data-template="${t.id}">
                <div class="template-card-thumb">
                    ${t.thumb}
                </div>
                <div class="template-card-info">
                    <div class="template-card-name">${t.name}</div>
                </div>
            </div>
        `).join('');

        container.innerHTML = `
            <h2 class="form-section-title">Choose a Template</h2>
            <p class="form-section-subtitle">Select a template for your resume. The preview will update in real-time.</p>
            <div class="template-grid" id="template-grid">
                ${cardsHtml}
            </div>
        `;

        // Clear any old click listener to avoid duplicate bindings, or just use the current container
        const grid = container.querySelector('#template-grid');
        if (grid) {
            grid.addEventListener('click', (e) => {
                const card = e.target.closest('.template-card');
                if (!card) return;
                const tid = card.dataset.template;
                ResumeStore.set('template_id', tid);
                grid.querySelectorAll('.template-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
            });
        }
    }

    return { render };
})();
