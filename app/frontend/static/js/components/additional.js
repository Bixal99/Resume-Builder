// =============================================================================
// Additional Sections Component (Languages, Certifications, Awards, Volunteer, References)
// =============================================================================

const AdditionalComponent = (() => {
    const TABS = [
        { id: 'languages', label: 'Languages' },
        { id: 'certifications', label: 'Certifications' },
        { id: 'awards', label: 'Awards' },
        { id: 'volunteer', label: 'Volunteer' },
        { id: 'references', label: 'References' },
    ];
    let activeTab = 'languages';
    let _contentEl = null;

    function render(container) {
        container.innerHTML = `
            <h2 class="form-section-title">Additional Sections</h2>
            <p class="form-section-subtitle">Add optional sections to strengthen your resume.</p>
            <div class="tabs" id="additional-tabs">
                ${TABS.map(t => `<button class="tab ${t.id === activeTab ? 'active' : ''}" data-tab="${t.id}">${t.label}</button>`).join('')}
            </div>
            <div id="additional-content" style="margin-top: var(--space-6);"></div>
        `;

        container.querySelector('#additional-tabs')?.addEventListener('click', (e) => {
            const btn = e.target.closest('.tab');
            if (btn) {
                activeTab = btn.dataset.tab;
                render(container);
            }
        });

        _contentEl = container.querySelector('#additional-content');
        bindDelegatedEvents(_contentEl);
        renderActiveTab();
    }

    function renderActiveTab() {
        if (!_contentEl) return;
        switch (activeTab) {
            case 'languages': renderLanguages(_contentEl); break;
            case 'certifications': renderCertifications(_contentEl); break;
            case 'awards': renderAwards(_contentEl); break;
            case 'volunteer': renderVolunteer(_contentEl); break;
            case 'references': renderReferences(_contentEl); break;
        }
    }

    function ensureIds(key, prefix) {
        const items = ResumeStore.get(key) || [];
        items.forEach(it => {
            if (!it.id) it.id = ResumeStore.generateId(prefix);
        });
        return items;
    }

    // === LANGUAGES ===
    function renderLanguages(c) {
        const items = ensureIds('languages', 'lang');
        c.innerHTML = `
            <div id="lang-list">${items.map(it => `
                <div class="entry-card" data-id="${escapeAttr(it.id)}">
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Language</label>
                            <input class="form-input add-field" data-sec="languages" data-id="${escapeAttr(it.id)}" data-f="name" value="${escapeAttr(it.name || '')}" placeholder="English">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Fluency</label>
                            <select class="form-select add-field" data-sec="languages" data-id="${escapeAttr(it.id)}" data-f="fluency">
                                <option value="">Select level</option>
                                ${['Native','Fluent','Advanced','Intermediate','Beginner'].map(l => `<option value="${l}" ${it.fluency === l ? 'selected' : ''}>${l}</option>`).join('')}
                            </select>
                        </div>
                    </div>
                    <button class="btn btn-ghost btn-sm remove-additional" data-sec="languages" data-id="${escapeAttr(it.id)}" style="margin-top:var(--space-2)">Remove</button>
                </div>
            `).join('')}</div>
            <button class="add-entry-btn" id="add-lang"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> Add Language</button>
        `;
    }

    // === CERTIFICATIONS ===
    function renderCertifications(c) {
        const items = ensureIds('certifications', 'cert');
        c.innerHTML = `
            <div id="cert-list">${items.map(it => `
                <div class="entry-card" data-id="${escapeAttr(it.id)}">
                    <div class="form-grid">
                        <div class="form-group"><label class="form-label">Certification Name</label><input class="form-input add-field" data-sec="certifications" data-id="${escapeAttr(it.id)}" data-f="name" value="${escapeAttr(it.name || '')}" placeholder="AWS Solutions Architect"></div>
                        <div class="form-group"><label class="form-label">Issuer</label><input class="form-input add-field" data-sec="certifications" data-id="${escapeAttr(it.id)}" data-f="issuer" value="${escapeAttr(it.issuer || '')}" placeholder="Amazon Web Services"></div>
                        <div class="form-group"><label class="form-label">Date</label><input class="form-input add-field" data-sec="certifications" data-id="${escapeAttr(it.id)}" data-f="date" value="${escapeAttr(it.date || '')}" placeholder="Jan 2023"></div>
                        <div class="form-group"><label class="form-label">Credential URL</label><input class="form-input add-field" data-sec="certifications" data-id="${escapeAttr(it.id)}" data-f="credential_url" value="${escapeAttr(it.credential_url || '')}" placeholder="https://..."></div>
                    </div>
                    <button class="btn btn-ghost btn-sm remove-additional" data-sec="certifications" data-id="${escapeAttr(it.id)}" style="margin-top:var(--space-2)">Remove</button>
                </div>
            `).join('')}</div>
            <button class="add-entry-btn" id="add-cert"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> Add Certification</button>
        `;
    }

    // === AWARDS ===
    function renderAwards(c) {
        const items = ensureIds('awards', 'award');
        c.innerHTML = `
            <div id="award-list">${items.map(it => `
                <div class="entry-card" data-id="${escapeAttr(it.id)}">
                    <div class="form-grid">
                        <div class="form-group"><label class="form-label">Award Title</label><input class="form-input add-field" data-sec="awards" data-id="${escapeAttr(it.id)}" data-f="title" value="${escapeAttr(it.title || '')}" placeholder="Best Paper Award"></div>
                        <div class="form-group"><label class="form-label">Issuer</label><input class="form-input add-field" data-sec="awards" data-id="${escapeAttr(it.id)}" data-f="issuer" value="${escapeAttr(it.issuer || '')}" placeholder="IEEE"></div>
                        <div class="form-group"><label class="form-label">Date</label><input class="form-input add-field" data-sec="awards" data-id="${escapeAttr(it.id)}" data-f="date" value="${escapeAttr(it.date || '')}" placeholder="2023"></div>
                        <div class="form-group full-width"><label class="form-label">Description</label><textarea class="form-textarea add-field" data-sec="awards" data-id="${escapeAttr(it.id)}" data-f="description" rows="2">${sanitizeHTML(it.description || '')}</textarea></div>
                    </div>
                    <button class="btn btn-ghost btn-sm remove-additional" data-sec="awards" data-id="${escapeAttr(it.id)}" style="margin-top:var(--space-2)">Remove</button>
                </div>
            `).join('')}</div>
            <button class="add-entry-btn" id="add-award"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> Add Award</button>
        `;
    }

    // === VOLUNTEER ===
    function renderVolunteer(c) {
        const items = ensureIds('volunteer', 'vol');
        c.innerHTML = `
            <div id="vol-list">${items.map(it => `
                <div class="entry-card" data-id="${escapeAttr(it.id)}">
                    <div class="form-grid">
                        <div class="form-group"><label class="form-label">Organization</label><input class="form-input add-field" data-sec="volunteer" data-id="${escapeAttr(it.id)}" data-f="organization" value="${escapeAttr(it.organization || '')}"></div>
                        <div class="form-group"><label class="form-label">Role</label><input class="form-input add-field" data-sec="volunteer" data-id="${escapeAttr(it.id)}" data-f="role" value="${escapeAttr(it.role || '')}"></div>
                        <div class="form-group"><label class="form-label">Start Date</label><input class="form-input add-field" data-sec="volunteer" data-id="${escapeAttr(it.id)}" data-f="start_date" value="${escapeAttr(it.start_date || '')}"></div>
                        <div class="form-group"><label class="form-label">End Date</label><input class="form-input add-field" data-sec="volunteer" data-id="${escapeAttr(it.id)}" data-f="end_date" value="${escapeAttr(it.end_date || '')}"></div>
                        <div class="form-group full-width"><label class="form-label">Description</label><textarea class="form-textarea add-field" data-sec="volunteer" data-id="${escapeAttr(it.id)}" data-f="description" rows="2">${sanitizeHTML(it.description || '')}</textarea></div>
                    </div>
                    <button class="btn btn-ghost btn-sm remove-additional" data-sec="volunteer" data-id="${escapeAttr(it.id)}" style="margin-top:var(--space-2)">Remove</button>
                </div>
            `).join('')}</div>
            <button class="add-entry-btn" id="add-vol"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> Add Volunteer Experience</button>
        `;
    }

    // === REFERENCES ===
    function renderReferences(c) {
        const items = ensureIds('references', 'ref');
        c.innerHTML = `
            <div id="ref-list">${items.map(it => `
                <div class="entry-card" data-id="${escapeAttr(it.id)}">
                    <div class="form-grid">
                        <div class="form-group"><label class="form-label">Name</label><input class="form-input add-field" data-sec="references" data-id="${escapeAttr(it.id)}" data-f="name" value="${escapeAttr(it.name || '')}"></div>
                        <div class="form-group"><label class="form-label">Title</label><input class="form-input add-field" data-sec="references" data-id="${escapeAttr(it.id)}" data-f="title" value="${escapeAttr(it.title || '')}"></div>
                        <div class="form-group"><label class="form-label">Company</label><input class="form-input add-field" data-sec="references" data-id="${escapeAttr(it.id)}" data-f="company" value="${escapeAttr(it.company || '')}"></div>
                        <div class="form-group"><label class="form-label">Email</label><input class="form-input add-field" data-sec="references" data-id="${escapeAttr(it.id)}" data-f="email" value="${escapeAttr(it.email || '')}"></div>
                        <div class="form-group"><label class="form-label">Phone</label><input class="form-input add-field" data-sec="references" data-id="${escapeAttr(it.id)}" data-f="phone" value="${escapeAttr(it.phone || '')}"></div>
                        <div class="form-group"><label class="form-label">Relationship</label><input class="form-input add-field" data-sec="references" data-id="${escapeAttr(it.id)}" data-f="relationship_type" value="${escapeAttr(it.relationship_type || '')}" placeholder="Former Manager"></div>
                    </div>
                    <button class="btn btn-ghost btn-sm remove-additional" data-sec="references" data-id="${escapeAttr(it.id)}" style="margin-top:var(--space-2)">Remove</button>
                </div>
            `).join('')}</div>
            <button class="add-entry-btn" id="add-ref"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> Add Reference</button>
        `;
    }

    // === DELEGATED EVENT LISTENERS (BOUND ONCE) ===
    function bindDelegatedEvents(contentEl) {
        if (!contentEl || contentEl._boundEvents) return;
        contentEl._boundEvents = true;

        // Input & Change handling
        const handleFieldChange = (e) => {
            if (e.target.classList.contains('add-field')) {
                const sec = e.target.dataset.sec;
                const id = e.target.dataset.id;
                const field = e.target.dataset.f;
                const items = ResumeStore.get(sec) || [];
                const item = items.find(it => it.id === id);
                if (item) {
                    item[field] = e.target.value;
                    ResumeStore.set(sec, items);
                }
            }
        };

        contentEl.addEventListener('input', handleFieldChange);
        contentEl.addEventListener('change', handleFieldChange);

        // Click handling (Add & Remove)
        contentEl.addEventListener('click', (e) => {
            // Add button click
            const addBtn = e.target.closest('.add-entry-btn');
            if (addBtn) {
                const btnId = addBtn.id;
                if (btnId === 'add-lang') {
                    const items = ResumeStore.get('languages') || [];
                    items.push({ id: ResumeStore.generateId('lang'), name: '', fluency: '', sort_order: items.length });
                    ResumeStore.set('languages', items);
                    renderActiveTab();
                } else if (btnId === 'add-cert') {
                    const items = ResumeStore.get('certifications') || [];
                    items.push({ id: ResumeStore.generateId('cert'), name: '', issuer: '', date: '', credential_url: '', sort_order: items.length });
                    ResumeStore.set('certifications', items);
                    renderActiveTab();
                } else if (btnId === 'add-award') {
                    const items = ResumeStore.get('awards') || [];
                    items.push({ id: ResumeStore.generateId('award'), title: '', issuer: '', date: '', description: '', sort_order: items.length });
                    ResumeStore.set('awards', items);
                    renderActiveTab();
                } else if (btnId === 'add-vol') {
                    const items = ResumeStore.get('volunteer') || [];
                    items.push({ id: ResumeStore.generateId('vol'), organization: '', role: '', start_date: '', end_date: '', description: '', sort_order: items.length });
                    ResumeStore.set('volunteer', items);
                    renderActiveTab();
                } else if (btnId === 'add-ref') {
                    const items = ResumeStore.get('references') || [];
                    items.push({ id: ResumeStore.generateId('ref'), name: '', title: '', company: '', email: '', phone: '', relationship_type: '', sort_order: items.length });
                    ResumeStore.set('references', items);
                    renderActiveTab();
                }
                return;
            }

            // Remove button click
            const removeBtn = e.target.closest('.remove-additional');
            if (removeBtn) {
                const sec = removeBtn.dataset.sec;
                const id = removeBtn.dataset.id;
                let items = ResumeStore.get(sec) || [];
                items = items.filter(it => it.id !== id);
                ResumeStore.set(sec, items);
                renderActiveTab();
                return;
            }
        });
    }

    return { render };
})();
