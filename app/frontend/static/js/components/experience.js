// =============================================================================
// Experience Form Component
// =============================================================================

const ExperienceComponent = (() => {
    let _container = null;

    function render(container) {
        _container = container;
        const items = ResumeStore.get('experience') || [];
        items.forEach(item => {
            if (!item.id) item.id = ResumeStore.generateId('exp');
        });

        container.innerHTML = `
            <h2 class="form-section-title">Work Experience</h2>
            <p class="form-section-subtitle">Add your relevant work experience, starting with the most recent.</p>
            <div id="experience-list">${items.map((item, i) => renderCard(item, i)).join('')}</div>
            <button class="add-entry-btn" id="add-experience">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                Add Experience
            </button>
        `;
        bindEvents(container);
        initDragDrop(container.querySelector('#experience-list'), reorder);
    }

    function renderCard(item, index) {
        const title = item.position || item.company || `Experience ${index + 1}`;
        const expId = escapeAttr(item.id);

        return `
        <div class="entry-card" draggable="true" data-id="${expId}">
            <div class="entry-card-header">
                <span class="entry-card-title"><span class="drag-handle">⠿</span> ${sanitizeHTML(title)}</span>
                <div class="entry-card-actions">
                    <button class="btn btn-icon btn-ghost btn-sm remove-entry" data-id="${expId}" title="Remove">✕</button>
                </div>
            </div>
            <div class="entry-card-body">
                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Job Title</label>
                        <input class="form-input exp-field" data-id="${expId}" data-field="position" value="${escapeAttr(item.position || '')}" placeholder="Software Engineer">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Company</label>
                        <input class="form-input exp-field" data-id="${expId}" data-field="company" value="${escapeAttr(item.company || '')}" placeholder="Google">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Location</label>
                        <input class="form-input exp-field" data-id="${expId}" data-field="location" value="${escapeAttr(item.location || '')}" placeholder="Mountain View, CA">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Start Date</label>
                        <input class="form-input exp-field" data-id="${expId}" data-field="start_date" value="${escapeAttr(item.start_date || '')}" placeholder="Jan 2020">
                    </div>
                    <div class="form-group">
                        <label class="form-label">End Date</label>
                        <input class="form-input exp-field" data-id="${expId}" data-field="end_date" value="${escapeAttr(item.end_date || '')}" placeholder="Present" ${item.is_current ? 'disabled' : ''}>
                    </div>
                    <div class="form-group">
                        <div class="checkbox-row" style="margin-top: 28px;">
                            <input type="checkbox" id="exp_current_${expId}" class="exp-current" data-id="${expId}" ${item.is_current ? 'checked' : ''}>
                            <label for="exp_current_${expId}">Current position</label>
                        </div>
                    </div>
                    <div class="form-group full-width">
                        <label class="form-label">Description</label>
                        <textarea class="form-textarea exp-field" data-id="${expId}" data-field="description" rows="2" placeholder="Brief role description...">${sanitizeHTML(item.description || '')}</textarea>
                    </div>
                    <div class="form-group full-width">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <label class="form-label" style="margin: 0;">Key Achievements</label>
                            <span style="font-size: 11px; color: var(--color-accent); font-weight: 600;">✨ STAR Method Enabled</span>
                        </div>
                        <div class="bullet-list" id="achievements-${expId}">
                            ${(item.achievements || []).map((a, ai) => `
                                <div class="bullet-item" style="display: flex; align-items: center; gap: 4px; margin-bottom: 6px;">
                                    <input class="form-input achievement-input" data-exp-id="${expId}" data-ai="${ai}" value="${escapeAttr(a)}" placeholder="Led project X, achieving Y% increase...">
                                    <button type="button" class="btn-star-polish" data-exp-id="${expId}" data-ai="${ai}" title="Polish with AI STAR Method & Quantifiable Metrics">
                                        ✨ AI STAR
                                    </button>
                                    <button class="btn btn-icon btn-ghost btn-sm remove-achievement" data-exp-id="${expId}" data-ai="${ai}">✕</button>
                                </div>
                            `).join('')}
                        </div>
                        <button class="btn btn-ghost btn-sm add-achievement" data-id="${expId}" style="margin-top:var(--space-2)">+ Add Achievement</button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    function bindEvents(container) {
        container.querySelector('#add-experience')?.addEventListener('click', () => {
            const items = ResumeStore.get('experience') || [];
            items.push({
                id: ResumeStore.generateId('exp'),
                position: '',
                company: '',
                location: '',
                start_date: '',
                end_date: '',
                is_current: false,
                description: '',
                achievements: [],
                sort_order: items.length
            });
            ResumeStore.set('experience', items);
            render(container);
        });

        if (container._expEventsBound) return;
        container._expEventsBound = true;

        container.addEventListener('input', (e) => {
            if (e.target.classList.contains('exp-field')) {
                const id = e.target.dataset.id;
                const field = e.target.dataset.field;
                const items = ResumeStore.get('experience') || [];
                const item = items.find(e => e.id === id);
                if (item) {
                    item[field] = e.target.value;
                    ResumeStore.set('experience', items);
                }
            }
            if (e.target.classList.contains('achievement-input')) {
                const expId = e.target.dataset.expId;
                const ai = parseInt(e.target.dataset.ai);
                const items = ResumeStore.get('experience') || [];
                const item = items.find(e => e.id === expId);
                if (item && Array.isArray(item.achievements) && item.achievements[ai] !== undefined) {
                    item.achievements[ai] = e.target.value;
                    ResumeStore.set('experience', items);
                }
            }
        });

        container.addEventListener('change', (e) => {
            if (e.target.classList.contains('exp-current')) {
                const id = e.target.dataset.id;
                const items = ResumeStore.get('experience') || [];
                const item = items.find(e => e.id === id);
                if (item) {
                    item.is_current = e.target.checked;
                    if (e.target.checked) item.end_date = '';
                    ResumeStore.set('experience', items);
                    render(container);
                }
            }
        });

        container.addEventListener('click', async (e) => {
            // Remove experience entry
            const removeBtn = e.target.closest('.remove-entry');
            if (removeBtn) {
                const id = removeBtn.dataset.id;
                let items = ResumeStore.get('experience') || [];
                const target = items.find(e => e.id === id);
                const entryName = target?.position || target?.company || 'this experience entry';
                
                const confirmed = (typeof showConfirmDialog === 'function')
                    ? await showConfirmDialog({
                        title: 'Delete Experience?',
                        message: `Remove "${entryName}"? This cannot be undone.`,
                        icon: '🗑️',
                        confirmText: 'Delete',
                        isDanger: true
                    })
                    : confirm(`Remove "${entryName}"? This cannot be undone.`);

                if (!confirmed) return;

                items = items.filter(e => e.id !== id);
                ResumeStore.set('experience', items);
                render(container);
                return;
            }

            // Add achievement
            const addAchBtn = e.target.closest('.add-achievement');
            if (addAchBtn) {
                const id = addAchBtn.dataset.id;
                const items = ResumeStore.get('experience') || [];
                const item = items.find(e => e.id === id);
                if (item) {
                    if (!Array.isArray(item.achievements)) item.achievements = [];
                    item.achievements.push('');
                    ResumeStore.set('experience', items);
                    render(container);
                }
                return;
            }

            // Polish with AI STAR Method
            const starBtn = e.target.closest('.btn-star-polish');
            if (starBtn) {
                const expId = starBtn.dataset.expId;
                const ai = parseInt(starBtn.dataset.ai);
                const items = ResumeStore.get('experience') || [];
                const item = items.find(e => e.id === expId);
                const bullet = (item && item.achievements) ? item.achievements[ai] : '';

                StarOptimizer.open({
                    bullet,
                    role: item?.position || '',
                    company: item?.company || '',
                    onApply: (newBullet) => {
                        if (item && item.achievements) {
                            item.achievements[ai] = newBullet;
                            ResumeStore.set('experience', items);
                            render(container);
                        }
                    }
                });
                return;
            }

            // Remove achievement
            const remAchBtn = e.target.closest('.remove-achievement');
            if (remAchBtn) {
                const expId = remAchBtn.dataset.expId;
                const ai = parseInt(remAchBtn.dataset.ai);
                const items = ResumeStore.get('experience') || [];
                const item = items.find(e => e.id === expId);
                if (item && Array.isArray(item.achievements)) {
                    item.achievements.splice(ai, 1);
                    ResumeStore.set('experience', items);
                    render(container);
                }
            }
        });
    }

    function reorder(order) {
        if (!Array.isArray(order)) return;
        const items = ResumeStore.get('experience') || [];
        const itemMap = new Map(items.map(e => [e.id, e]));
        const reordered = order.map(id => itemMap.get(id)).filter(Boolean);

        items.forEach(item => {
            if (!order.includes(item.id)) {
                reordered.push(item);
            }
        });

        reordered.forEach((e, idx) => { e.sort_order = idx; });
        ResumeStore.set('experience', reordered);
        if (_container) render(_container);
    }

    return { render };
})();

// =============================================================================
// AI STAR Method Bullet Optimizer Controller
// =============================================================================

const StarOptimizer = (() => {
    let currentBullet = '';
    let currentRole = '';
    let currentCompany = '';
    let currentMode = 'star';
    let onApplyCallback = null;
    let initialized = false;

    function init() {
        if (initialized) return;
        const modal = document.getElementById('star-optimizer-modal');
        const closeBtn = document.getElementById('star-optimizer-close');
        if (!modal) return;

        closeBtn?.addEventListener('click', () => modal.classList.remove('active'));
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.remove('active');
        });

        modal.querySelectorAll('.star-mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.querySelectorAll('.star-mode-btn').forEach(b => {
                    b.classList.remove('active');
                    b.classList.add('btn-ghost');
                });
                btn.classList.add('active');
                btn.classList.remove('btn-ghost');
                currentMode = btn.dataset.mode || 'star';
                fetchSuggestions();
            });
        });
        initialized = true;
    }

    async function fetchSuggestions() {
        const container = document.getElementById('star-suggestions-container');
        if (!container) return;

        container.innerHTML = `
            <div class="star-loading-state" style="text-align: center; padding: 22px; color: var(--color-text-secondary); font-size: 13px;">
                <span style="display: inline-block; animation: spin 1s linear infinite; margin-right: 6px;">⏳</span> Polishing with Qwen 2.5 72B STAR Engine...
            </div>`;

        try {
            const res = await API.optimizeBullet({
                bullet: currentBullet,
                role: currentRole,
                company: currentCompany,
                mode: currentMode
            });

            const suggestions = res.suggestions || [];
            if (suggestions.length === 0) {
                container.innerHTML = `<div style="color: #ef4444; padding: 12px; font-size: 12px;">No suggestions generated. Try another mode.</div>`;
                return;
            }

            container.innerHTML = suggestions.map((s, idx) => `
                <div class="star-suggestion-card">
                    <div class="star-suggestion-text">${sanitizeHTML(s)}</div>
                    <div class="star-card-actions">
                        <span class="star-metric-tag">${currentMode === 'metrics' ? '📊 Quantifiable Metrics' : currentMode === 'action_verbs' ? '⚡ Executive Action Verb' : '⭐ Full STAR Method'}</span>
                        <button type="button" class="btn btn-sm btn-primary btn-apply-star" data-idx="${idx}" style="font-size: 11px; padding: 3px 10px;">
                            Apply to Resume ✓
                        </button>
                    </div>
                </div>
            `).join('');

            container.querySelectorAll('.btn-apply-star').forEach(btn => {
                btn.addEventListener('click', () => {
                    const idx = parseInt(btn.dataset.idx);
                    const chosen = suggestions[idx];
                    if (chosen && typeof onApplyCallback === 'function') {
                        onApplyCallback(chosen);
                    }
                    const modal = document.getElementById('star-optimizer-modal');
                    if (modal) modal.classList.remove('active');
                    if (typeof showToast === 'function') {
                        showToast('STAR bullet applied to resume!', 'success');
                    }
                });
            });

        } catch (err) {
            container.innerHTML = `<div style="color: #ef4444; padding: 12px; font-size: 12px;">Failed to optimize bullet: ${err.message || 'Unknown error'}</div>`;
        }
    }

    function open({ bullet, role, company, onApply }) {
        init();
        currentBullet = (bullet || '').trim();
        currentRole = role || '';
        currentCompany = company || '';
        currentMode = 'star';
        onApplyCallback = onApply;

        if (!currentBullet) {
            if (typeof showToast === 'function') {
                showToast('Please type a draft bullet first to polish it!', 'info');
            }
            return;
        }

        const modal = document.getElementById('star-optimizer-modal');
        const origEl = document.getElementById('star-original-bullet');
        if (!modal || !origEl) return;

        origEl.textContent = `"${currentBullet}"`;
        
        modal.querySelectorAll('.star-mode-btn').forEach((b, i) => {
            if (i === 0) {
                b.classList.add('active');
                b.classList.remove('btn-ghost');
            } else {
                b.classList.remove('active');
                b.classList.add('btn-ghost');
            }
        });

        modal.classList.add('active');
        fetchSuggestions();
    }

    return { init, open };
})();

document.addEventListener('DOMContentLoaded', () => {
    StarOptimizer.init();
});
