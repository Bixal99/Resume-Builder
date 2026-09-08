// =============================================================================
// Projects Form Component
// =============================================================================

const ProjectsComponent = (() => {
    let _container = null;

    function render(container) {
        _container = container;
        const items = ResumeStore.get('projects') || [];
        // Ensure every item has an immutable unique ID
        items.forEach(item => {
            if (!item.id) item.id = ResumeStore.generateId('proj');
        });

        container.innerHTML = `
            <h2 class="form-section-title">Projects</h2>
            <p class="form-section-subtitle">Showcase your notable projects.</p>
            <div id="projects-list">${items.map((item, i) => renderCard(item, i)).join('')}</div>
            <button class="add-entry-btn" id="add-project">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                Add Project
            </button>
        `;
        bindEvents(container);
        initDragDrop(container.querySelector('#projects-list'), reorder);
    }

    function renderCard(item, index) {
        const title = item.title || `Project ${index + 1}`;
        const techs = item.technologies || [];
        const projId = escapeAttr(item.id);

        return `
        <div class="entry-card" draggable="true" data-id="${projId}">
            <div class="entry-card-header">
                <span class="entry-card-title"><span class="drag-handle">⠿</span> ${sanitizeHTML(title)}</span>
                <div class="entry-card-actions">
                    <button class="btn btn-icon btn-ghost btn-sm remove-entry" data-id="${projId}" title="Remove">✕</button>
                </div>
            </div>
            <div class="entry-card-body">
                <div class="form-grid">
                    <div class="form-group full-width">
                        <label class="form-label">Project Name</label>
                        <input class="form-input proj-field" data-id="${projId}" data-field="title" value="${escapeAttr(item.title || '')}" placeholder="My Awesome App">
                    </div>
                    <div class="form-group full-width">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <label class="form-label" style="margin:0;">Description</label>
                            <button type="button" class="btn-star-polish proj-star-btn" data-id="${projId}" title="Polish with AI STAR Method & Quantifiable Metrics">✨ AI STAR Polish</button>
                        </div>
                        <textarea class="form-textarea proj-field" data-id="${projId}" data-field="description" rows="2" placeholder="A brief description of the project...">${sanitizeHTML(item.description || '')}</textarea>
                    </div>
                    <div class="form-group">
                        <label class="form-label">GitHub URL</label>
                        <input class="form-input proj-field" data-id="${projId}" data-field="github_url" value="${escapeAttr(item.github_url || '')}" placeholder="github.com/user/repo">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Live URL</label>
                        <input class="form-input proj-field" data-id="${projId}" data-field="live_url" value="${escapeAttr(item.live_url || '')}" placeholder="myapp.com">
                    </div>
                    <div class="form-group full-width">
                        <label class="form-label">Technologies</label>
                        <div class="tags-input-container" id="tech-tags-${projId}">
                            ${techs.map(t => `<span class="tag tag-primary tag-removable" data-id="${projId}" data-tech="${escapeAttr(t)}">${sanitizeHTML(t)} <span class="tag-remove" data-id="${projId}" data-tech="${escapeAttr(t)}">✕</span></span>`).join('')}
                            <input type="text" class="tech-input" data-id="${projId}" placeholder="Type & press Enter or comma">
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
    }

    function addTechnologies(container, projId, rawText) {
        if (!rawText || !rawText.trim()) return;
        const tokens = rawText
            .split(/[,;\n\r\t•]+/)
            .map(t => t.trim().replace(/^[-*•]\s*/, ''))
            .filter(t => t.length > 0 && t.length <= 50);

        if (tokens.length === 0) return;

        const items = ResumeStore.get('projects') || [];
        const item = items.find(p => p.id === projId);
        if (!item) return;

        if (!Array.isArray(item.technologies)) {
            item.technologies = [];
        }

        const existingSet = new Set(item.technologies.map(t => t.toLowerCase()));
        let added = false;
        tokens.forEach(tok => {
            if (!existingSet.has(tok.toLowerCase())) {
                existingSet.add(tok.toLowerCase());
                item.technologies.push(tok);
                added = true;
            }
        });

        if (added) {
            ResumeStore.set('projects', items);
            render(container);
        }
    }

    function bindEvents(container) {
        container.querySelector('#add-project')?.addEventListener('click', () => {
            const items = ResumeStore.get('projects') || [];
            items.push({
                id: ResumeStore.generateId('proj'),
                title: '',
                description: '',
                technologies: [],
                github_url: '',
                live_url: '',
                highlights: [],
                sort_order: items.length
            });
            ResumeStore.set('projects', items);
            render(container);
        });

        if (container._projEventsBound) return;
        container._projEventsBound = true;

        container.addEventListener('input', (e) => {
            if (e.target.classList.contains('proj-field')) {
                const id = e.target.dataset.id;
                const field = e.target.dataset.field;
                const items = ResumeStore.get('projects') || [];
                const item = items.find(p => p.id === id);
                if (item) {
                    item[field] = e.target.value;
                    ResumeStore.set('projects', items);
                }
            }
        });

        container.addEventListener('keydown', (e) => {
            if (e.target.classList.contains('tech-input')) {
                if (e.key === 'Enter' || e.key === ',') {
                    e.preventDefault();
                    const projId = e.target.dataset.id;
                    const val = e.target.value;
                    e.target.value = '';
                    addTechnologies(container, projId, val);
                }
            }
        });

        container.addEventListener('paste', (e) => {
            if (e.target.classList.contains('tech-input')) {
                const pasteText = (e.clipboardData || window.clipboardData)?.getData('text');
                if (pasteText && /[,;\n\r\t•]/.test(pasteText)) {
                    e.preventDefault();
                    const projId = e.target.dataset.id;
                    e.target.value = '';
                    addTechnologies(container, projId, pasteText);
                }
            }
        });

        container.addEventListener('click', async (e) => {
            // Polish with AI STAR Method
            const projStarBtn = e.target.closest('.proj-star-btn');
            if (projStarBtn) {
                const id = projStarBtn.dataset.id;
                const items = ResumeStore.get('projects') || [];
                const item = items.find(p => p.id === id);
                if (typeof StarOptimizer !== 'undefined' && item) {
                    StarOptimizer.open({
                        bullet: item.description || '',
                        role: 'Project Contributor',
                        company: item.title || 'Project',
                        onApply: (newDesc) => {
                            item.description = newDesc;
                            ResumeStore.set('projects', items);
                            render(container);
                        }
                    });
                }
                return;
            }

            // Remove project entry
            const removeEntryBtn = e.target.closest('.remove-entry');
            if (removeEntryBtn) {
                const id = removeEntryBtn.dataset.id;
                let items = ResumeStore.get('projects') || [];
                const target = items.find(p => p.id === id);
                const projectName = target?.title || 'this project';
                
                const confirmed = (typeof showConfirmDialog === 'function')
                    ? await showConfirmDialog({
                        title: 'Delete Project?',
                        message: `Remove "${projectName}"? This cannot be undone.`,
                        icon: '💻',
                        confirmText: 'Delete',
                        isDanger: true
                    })
                    : confirm(`Remove "${projectName}"? This cannot be undone.`);

                if (!confirmed) return;

                items = items.filter(p => p.id !== id);
                ResumeStore.set('projects', items);
                render(container);
                return;
            }

            // Remove technology tag
            const tagRemoveBtn = e.target.closest('.tag-remove');
            if (tagRemoveBtn) {
                const id = tagRemoveBtn.dataset.id;
                const tech = tagRemoveBtn.dataset.tech;
                const items = ResumeStore.get('projects') || [];
                const item = items.find(p => p.id === id);
                if (item && Array.isArray(item.technologies)) {
                    item.technologies = item.technologies.filter(t => t !== tech);
                    ResumeStore.set('projects', items);
                    render(container);
                }
            }
        });
    }

    function reorder(order) {
        if (!Array.isArray(order)) return;
        const items = ResumeStore.get('projects') || [];
        const itemMap = new Map(items.map(p => [p.id, p]));
        const reordered = order.map(id => itemMap.get(id)).filter(Boolean);

        // Append any items that were not present in the order list
        items.forEach(item => {
            if (!order.includes(item.id)) {
                reordered.push(item);
            }
        });

        // Update sort_order
        reordered.forEach((p, idx) => { p.sort_order = idx; });
        ResumeStore.set('projects', reordered);
        if (_container) render(_container);
    }

    return { render };
})();
