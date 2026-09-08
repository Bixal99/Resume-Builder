// =============================================================================
// Arrange Sections Step Component
// =============================================================================

const ArrangeComponent = (() => {
    const SECTION_LABELS = {
        summary: 'Profile Summary',
        experience: 'Work Experience',
        education: 'Education',
        projects: 'Projects',
        skills: 'Skills',
        certifications: 'Certifications',
        languages: 'Languages',
        awards: 'Awards',
        volunteer: 'Volunteer Work',
        references: 'References'
    };

    function render(container) {
        if (!container) return;
        const order = ResumeStore.get('section_order') || [];
        const hidden = ResumeStore.get('hidden_sections') || [];

        container.innerHTML = `
            <h2 class="form-section-title">Arrange Sections</h2>
            <p class="form-section-subtitle">Customize the layout of your CV by dragging sections up or down. Toggle visibility using the eye icon.</p>
            <div class="arrange-list" id="arrange-list">
                ${order.map(secId => {
                    const isHidden = hidden.includes(secId);
                    return `
                    <div class="arrange-item-card${isHidden ? ' hidden-state' : ''}" data-id="${secId}">
                        <div class="arrange-drag-handle">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="9" y1="5" x2="9" y2="19"/><line x1="15" y1="5" x2="15" y2="19"/></svg>
                        </div>
                        <div class="arrange-info">
                            <span class="arrange-title">${SECTION_LABELS[secId] || secId}</span>
                            <span class="arrange-status-badge">${isHidden ? 'Hidden' : 'Visible'}</span>
                        </div>
                        <button type="button" class="btn-toggle-visibility" data-id="${secId}" title="${isHidden ? 'Show section' : 'Hide section'}">
                            ${isHidden ? 
                                `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>` :
                                `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`
                            }
                        </button>
                    </div>`;
                }).join('')}
            </div>
            
            <div style="margin-top: var(--space-8);">
                <h2 class="form-section-title">Document Settings</h2>
                <p class="form-section-subtitle">Fine-tune the spacing and alignment of your CV.</p>
                <div class="form-grid">
                    <div class="form-group">
                        <label class="form-label">Section Spacing</label>
                        <select id="setting-section-spacing" class="form-input">
                            <option value="compact">Compact</option>
                            <option value="normal" selected>Normal</option>
                            <option value="relaxed">Relaxed</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Line Spacing</label>
                        <select id="setting-line-spacing" class="form-input">
                            <option value="tight">Tight</option>
                            <option value="normal" selected>Normal</option>
                            <option value="loose">Loose</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Font Family</label>
                        <select id="setting-font-family" class="form-input">
                            <option value="default" selected>Default</option>
                            <option value="Arial, sans-serif">Arial</option>
                            <option value="'Poppins', sans-serif">Poppins</option>
                            <option value="'Roboto', sans-serif">Roboto</option>
                            <option value="'Open Sans', sans-serif">Open Sans</option>
                            <option value="'Lato', sans-serif">Lato</option>
                            <option value="'Montserrat', sans-serif">Montserrat</option>
                            <option value="'Oswald', sans-serif">Oswald</option>
                            <option value="'Merriweather', serif">Merriweather</option>
                            <option value="'Playfair Display', serif">Playfair Display</option>
                            <option value="'Lora', serif">Lora</option>
                            <option value="Georgia, serif">Georgia</option>
                            <option value="'Times New Roman', Times, serif">Times New Roman</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Text Alignment</label>
                        <select id="setting-alignment" class="form-input">
                            <option value="left" selected>Left Aligned</option>
                            <option value="justify">Justified</option>
                        </select>
                    </div>
                </div>
            </div>
        `;

        const listContainer = container.querySelector('#arrange-list');
        initDragDrop(listContainer, (newOrder) => {
            ResumeStore.set('section_order', newOrder);
            const stepperNav = document.getElementById('stepper-nav');
            if (stepperNav) StepperComponent.render(stepperNav);
        });

        // Toggle visibility - attach to the newly created list so it dies on re-render
        const arrangeList = container.querySelector('.arrange-list');
        if (arrangeList) {
            arrangeList.addEventListener('click', (e) => {
                const btn = e.target.closest('.btn-toggle-visibility');
                if (btn) {
                    const secId = btn.dataset.id;
                    let currentHidden = [...ResumeStore.get('hidden_sections') || []];
                    if (currentHidden.includes(secId)) {
                        currentHidden = currentHidden.filter(id => id !== secId);
                    } else {
                        currentHidden.push(secId);
                    }
                    ResumeStore.set('hidden_sections', currentHidden);
                    
                    // Re-render this component
                    render(container);
                    
                    // Re-render stepper to reflect changes
                    const stepperNav = document.getElementById('stepper-nav');
                    if (stepperNav && window.StepperComponent) {
                        StepperComponent.render(stepperNav);
                    }
                }
            });
        }
        
        // Settings Listeners
        const themeSettings = ResumeStore.get('theme_settings') || { section_spacing: 'normal', line_spacing: 'normal', text_alignment: 'left', font_family: 'default' };
        
        const secSpacing = container.querySelector('#setting-section-spacing');
        const lineSpacing = container.querySelector('#setting-line-spacing');
        const align = container.querySelector('#setting-alignment');
        const fontFamily = container.querySelector('#setting-font-family');
        
        if (secSpacing) secSpacing.value = themeSettings.section_spacing || 'normal';
        if (lineSpacing) lineSpacing.value = themeSettings.line_spacing || 'normal';
        if (align) align.value = themeSettings.text_alignment || 'left';
        if (fontFamily) fontFamily.value = themeSettings.font_family || 'default';
        
        const saveSettings = () => {
            ResumeStore.set('theme_settings', {
                section_spacing: secSpacing ? secSpacing.value : 'normal',
                line_spacing: lineSpacing ? lineSpacing.value : 'normal',
                text_alignment: align ? align.value : 'left',
                font_family: fontFamily ? fontFamily.value : 'default'
            });
            // Update preview immediately
            if (window.PreviewComponent) {
                PreviewComponent.refresh();
            }
        };
        
        if (secSpacing) secSpacing.addEventListener('change', saveSettings);
        if (lineSpacing) lineSpacing.addEventListener('change', saveSettings);
        if (align) align.addEventListener('change', saveSettings);
        if (fontFamily) fontFamily.addEventListener('change', saveSettings);
    }

    // Pointer-events based touch-friendly drag and drop
    function initDragDrop(container, onReorder) {
        let activeEl = null;

        container.addEventListener('pointerdown', e => {
            const handle = e.target.closest('.arrange-drag-handle');
            if (!handle) return;
            e.preventDefault();
            const card = handle.closest('.arrange-item-card');
            if (!card) return;

            activeEl = card;
            activeEl.classList.add('dragging');
            activeEl.setPointerCapture(e.pointerId);
        });

        container.addEventListener('pointermove', e => {
            if (!activeEl) return;
            e.preventDefault();

            const y = e.clientY;
            const siblings = Array.from(container.querySelectorAll('.arrange-item-card:not(.dragging)'));

            const nextSibling = siblings.find(sibling => {
                const box = sibling.getBoundingClientRect();
                const midpoint = box.top + box.height / 2;
                return y < midpoint;
            });

            if (nextSibling) {
                container.insertBefore(activeEl, nextSibling);
            } else {
                container.appendChild(activeEl);
            }
        });

        const endDrag = e => {
            if (!activeEl) return;
            activeEl.classList.remove('dragging');
            try {
                activeEl.releasePointerCapture(e.pointerId);
            } catch (err) { /* ignore */ }
            activeEl = null;

            const order = Array.from(container.querySelectorAll('.arrange-item-card')).map(c => c.dataset.id);
            if (onReorder) onReorder(order);
        };

        container.addEventListener('pointerup', endDrag);
        container.addEventListener('pointercancel', endDrag);
    }

    return { render };
})();
