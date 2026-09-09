// =============================================================================
// Education Form Component
// =============================================================================

const EducationComponent = (() => {
    let _container = null;

    function splitDegreeAndField(degree, fieldOfStudy) {
        let d = (degree || '').trim();
        let f = (fieldOfStudy || '').trim();
        if (!d) return { degree: d, field_of_study: f };

        if (f) {
            d = d.replace(new RegExp('\\s+(?:in|–|-|—)\\s+' + f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[.\\s]*$', 'i'), '').trim();
            return { degree: d, field_of_study: f };
        }

        // Pattern 1: "... in <field>" (e.g. "Bachelor of Science in Computer Science")
        const mIn = d.match(/^(.*?)\s+in\s+(.+)$/i);
        if (mIn) {
            return { degree: mIn[1].trim().replace(/[,.;]+$/, ''), field_of_study: mIn[2].trim().replace(/[,.;]+$/, '') };
        }

        // Pattern 2: "... - <field>" or "... – <field>"
        const mDash = d.match(/^(.*?)\s+[-–—]\s+(.+)$/);
        if (mDash) {
            return { degree: mDash[1].trim().replace(/[,.;]+$/, ''), field_of_study: mDash[2].trim().replace(/[,.;]+$/, '') };
        }

        // Pattern 3: "... ( <field> )"
        const mParen = d.match(/^(.*?)\s*\(([^)]+)\)\s*$/);
        if (mParen) {
            return { degree: mParen[1].trim(), field_of_study: mParen[2].trim() };
        }

        // Pattern 4: "BS Computer Science", "BSc Computer Science", etc.
        const mAbbrev = d.match(/^(B\.?S\.?c?|M\.?S\.?c?|B\.?Tech|M\.?Tech|B\.?E\.?|M\.?E\.?|B\.?A\.?|M\.?A\.?|Ph\.?D\.?)\s+(.+)$/i);
        if (mAbbrev) {
            return { degree: mAbbrev[1].trim(), field_of_study: mAbbrev[2].trim() };
        }

        // Pattern 5: "Bachelor of Science Computer Science"
        const mFull = d.match(/^(Bachelor\s+of\s+\w+|Master\s+of\s+\w+|Associate\s+of\s+\w+)\s+(.+)$/i);
        if (mFull) {
            return { degree: mFull[1].trim(), field_of_study: mFull[2].trim() };
        }

        return { degree: d, field_of_study: f };
    }

    function render(container) {
        _container = container;
        const items = ResumeStore.get('education') || [];
        let modified = false;
        items.forEach(item => {
            if (!item.id) {
                item.id = ResumeStore.generateId('edu');
                modified = true;
            }
            if (item.degree && (!item.field_of_study || !item.field_of_study.trim())) {
                const split = splitDegreeAndField(item.degree, item.field_of_study);
                if (split.field_of_study) {
                    item.degree = split.degree;
                    item.field_of_study = split.field_of_study;
                    modified = true;
                }
            }
        });
        if (modified) {
            ResumeStore.set('education', items);
        }

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
                    if (field === 'degree' && (!item.field_of_study || !item.field_of_study.trim())) {
                        const split = splitDegreeAndField(item.degree, item.field_of_study);
                        if (split.field_of_study) {
                            item.degree = split.degree;
                            item.field_of_study = split.field_of_study;
                            e.target.value = split.degree;
                            const fInput = container.querySelector(`.edu-field[data-id="${id}"][data-field="field_of_study"]`);
                            if (fInput) fInput.value = split.field_of_study;
                        }
                    }
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
