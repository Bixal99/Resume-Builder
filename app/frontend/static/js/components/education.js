// =============================================================================
// Education Form Component
// =============================================================================

const EducationComponent = (() => {
    let _container = null;

    function render(container) {
        _container = container;
        const items = ResumeStore.get('education') || [];
        items.forEach(item => {
            if (!item.id) item.id = ResumeStore.generateId('edu');
        });

        container.innerHTML = `
            <h2 class="form-section-title">Education</h2>
            <p class="form-section-subtitle">Add your educational background.</p>
            <div id="education-list">${items.map((item, i) => renderCard(item, i)).join('')}</div>
            <button class="add-entry-btn" id="add-education">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                Add Education
            </button>
        `;
        bindEvents(container);
        initDragDrop(container.querySelector('#education-list'), reorder);
    }

    function renderCard(item, index) {
        const title = item.degree || item.institution || `Education ${index + 1}`;
        const eduId = escapeAttr(item.id);

        return `
        <div class="entry-card" draggable="true" data-id="${eduId}">
            <div class="entry-card-header">
                <span class="entry-card-title"><span class="drag-handle">⠿</span> ${sanitizeHTML(title)}</span>
                <div class="entry-card-actions">
                    <button class="btn btn-icon btn-ghost btn-sm remove-entry" data-id="${eduId}" title="Remove">✕</button>
                </div>
            </div>
            <div class="entry-card-body">
                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Degree</label>
                        <input class="form-input edu-field" data-id="${eduId}" data-field="degree" value="${escapeAttr(item.degree || '')}" placeholder="Bachelor of Science">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Field of Study</label>
                        <input class="form-input edu-field" data-id="${eduId}" data-field="field_of_study" value="${escapeAttr(item.field_of_study || '')}" placeholder="Computer Science">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Institution</label>
                        <input class="form-input edu-field" data-id="${eduId}" data-field="institution" value="${escapeAttr(item.institution || '')}" placeholder="MIT">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Location</label>
                        <input class="form-input edu-field" data-id="${eduId}" data-field="location" value="${escapeAttr(item.location || '')}" placeholder="Cambridge, MA">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Start Date</label>
                        <input class="form-input edu-field" data-id="${eduId}" data-field="start_date" value="${escapeAttr(item.start_date || '')}" placeholder="Sep 2016">
                    </div>
                    <div class="form-group">
                        <label class="form-label">End Date</label>
                        <input class="form-input edu-field" data-id="${eduId}" data-field="end_date" value="${escapeAttr(item.end_date || '')}" placeholder="Jun 2020" ${item.is_current ? 'disabled' : ''}>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Grade / GPA</label>
                        <input class="form-input edu-field" data-id="${eduId}" data-field="grade" value="${escapeAttr(item.grade || '')}" placeholder="3.8/4.0">
                    </div>
                    <div class="form-group">
                        <div class="checkbox-row" style="margin-top: 28px;">
                            <input type="checkbox" id="edu_current_${eduId}" class="edu-current" data-id="${eduId}" ${item.is_current ? 'checked' : ''}>
                            <label for="edu_current_${eduId}">Currently studying</label>
                        </div>
                    </div>
                    <div class="form-group full-width">
                        <label class="form-label">Description (Optional)</label>
                        <textarea class="form-textarea edu-field" data-id="${eduId}" data-field="description" rows="2" placeholder="Relevant coursework, thesis, honors...">${sanitizeHTML(item.description || '')}</textarea>
                    </div>
                </div>
            </div>
        </div>`;
    }

    function bindEvents(container) {
        container.querySelector('#add-education')?.addEventListener('click', () => {
            const items = ResumeStore.get('education') || [];
            items.push({
                id: ResumeStore.generateId('edu'),
                degree: '',
                field_of_study: '',
                institution: '',
                location: '',
                start_date: '',
                end_date: '',
                is_current: false,
                grade: '',
                description: '',
                sort_order: items.length
            });
            ResumeStore.set('education', items);
            render(container);
        });

        if (container._eduEventsBound) return;
        container._eduEventsBound = true;

        container.addEventListener('input', (e) => {
            if (e.target.classList.contains('edu-field')) {
                const id = e.target.dataset.id;
                const field = e.target.dataset.field;
                const items = ResumeStore.get('education') || [];
                const item = items.find(e => e.id === id);
                if (item) {
                    item[field] = e.target.value;
                    ResumeStore.set('education', items);
                }
            }
        });

        container.addEventListener('change', (e) => {
            if (e.target.classList.contains('edu-current')) {
                const id = e.target.dataset.id;
                const items = ResumeStore.get('education') || [];
                const item = items.find(e => e.id === id);
                if (item) {
                    item.is_current = e.target.checked;
                    if (e.target.checked) item.end_date = '';
                    ResumeStore.set('education', items);
                    render(container);
                }
            }
        });

        container.addEventListener('click', async (e) => {
            const removeBtn = e.target.closest('.remove-entry');
            if (removeBtn) {
                const id = removeBtn.dataset.id;
                let items = ResumeStore.get('education') || [];
                const target = items.find(e => e.id === id);
                const entryName = target?.degree || target?.institution || 'this education entry';
                
                const confirmed = (typeof showConfirmDialog === 'function')
                    ? await showConfirmDialog({
                        title: 'Delete Education?',
                        message: `Remove "${entryName}"? This cannot be undone.`,
                        icon: '🎓',
                        confirmText: 'Delete',
                        isDanger: true
                    })
                    : confirm(`Remove "${entryName}"? This cannot be undone.`);

                if (!confirmed) return;
                items = items.filter(e => e.id !== id);
                ResumeStore.set('education', items);
                render(container);
            }
        });
    }

    function reorder(order) {
        if (!Array.isArray(order)) return;
        const items = ResumeStore.get('education') || [];
        const itemMap = new Map(items.map(e => [e.id, e]));
        const reordered = order.map(id => itemMap.get(id)).filter(Boolean);

        items.forEach(item => {
            if (!order.includes(item.id)) {
                reordered.push(item);
            }
        });

        reordered.forEach((e, idx) => { e.sort_order = idx; });
        ResumeStore.set('education', reordered);
        if (_container) render(_container);
    }

    return { render };
})();
