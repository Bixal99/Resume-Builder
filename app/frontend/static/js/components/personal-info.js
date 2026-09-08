// =============================================================================
// Personal Info Form Component
// =============================================================================

const PersonalInfoComponent = (() => {
    function render(container) {
        const s = ResumeStore.get();
        const isBlank = !s.first_name && !s.last_name;
        container.innerHTML = `
            ${isBlank ? `
            <div class="sample-callout-banner" style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 18px;">💡</span>
                    <span style="font-size: 13px; color: var(--color-text); font-weight: 500;">
                        Want to see how a complete resume looks? Quick-start with pre-filled sample data.
                    </span>
                </div>
                <button type="button" class="btn btn-sm btn-primary" id="btn-load-sample-banner" style="white-space: nowrap; font-size: 12px; padding: 6px 12px; background: var(--color-accent); border: none; cursor: pointer;">
                    ⚡ Load Sample Resume
                </button>
            </div>
            ` : ''}
            <h2 class="form-section-title">Personal Information</h2>
            <p class="form-section-subtitle">Let's start with your basic details.</p>

            <div class="photo-upload">
                <div class="photo-preview" id="photo-preview">
                    ${s.photo ? `<img src="${escapeAttr(s.photo)}" alt="Photo">` : '<span class="photo-preview-placeholder">👤</span>'}
                </div>
                <div class="photo-upload-controls">
                    <label class="btn btn-secondary btn-sm" for="photo-input">Upload Photo</label>
                    <input type="file" id="photo-input" accept="image/*" style="display:none">
                    ${s.photo ? '<button class="btn btn-ghost btn-sm" id="remove-photo">Remove</button>' : ''}
                    <span class="form-hint">Optional. JPG, PNG, or WebP. Max 5MB.</span>
                </div>
            </div>

            <div class="form-grid">
                <div class="form-group">
                    <label class="form-label" for="first_name">First Name</label>
                    <input class="form-input" id="first_name" value="${escapeAttr(s.first_name)}" placeholder="John" data-validate="required">
                    <span class="form-error"></span>
                </div>
                <div class="form-group">
                    <label class="form-label" for="last_name">Last Name</label>
                    <input class="form-input" id="last_name" value="${escapeAttr(s.last_name)}" placeholder="Doe" data-validate="required">
                    <span class="form-error"></span>
                </div>
                <div class="form-group full-width">
                    <label class="form-label" for="professional_title">Professional Title</label>
                    <input class="form-input" id="professional_title" value="${escapeAttr(s.professional_title)}" placeholder="Senior Software Engineer">
                </div>
                <div class="form-group">
                    <label class="form-label" for="email">Email</label>
                    <input class="form-input" id="email" type="email" value="${escapeAttr(s.email)}" placeholder="john@example.com" data-validate="email">
                    <span class="form-error"></span>
                </div>
                <div class="form-group">
                    <label class="form-label" for="phone">Phone</label>
                    <input class="form-input" id="phone" value="${escapeAttr(s.phone)}" placeholder="+1 (555) 123-4567" data-validate="phone">
                    <span class="form-error"></span>
                </div>
                <div class="form-group full-width">
                    <label class="form-label" for="address">Address</label>
                    <input class="form-input" id="address" value="${escapeAttr(s.address)}" placeholder="New York, NY">
                </div>
                <div class="form-group">
                    <label class="form-label" for="linkedin">LinkedIn URL</label>
                    <input class="form-input" id="linkedin" value="${escapeAttr(s.linkedin)}" placeholder="linkedin.com/in/johndoe">
                </div>
                <div class="form-group">
                    <label class="form-label" for="github">GitHub URL</label>
                    <input class="form-input" id="github" value="${escapeAttr(s.github)}" placeholder="github.com/johndoe">
                </div>
                <div class="form-group">
                    <label class="form-label" for="portfolio">Portfolio URL</label>
                    <input class="form-input" id="portfolio" value="${escapeAttr(s.portfolio)}" placeholder="johndoe.com">
                </div>
                <div class="form-group">
                    <label class="form-label" for="website">Website</label>
                    <input class="form-input" id="website" value="${escapeAttr(s.website)}" placeholder="myblog.com">
                </div>
                <div class="form-group">
                    <label class="form-label" for="nationality">Nationality</label>
                    <input class="form-input" id="nationality" value="${escapeAttr(s.nationality)}" placeholder="American">
                </div>
            </div>
        `;

        // Bind events
        const fields = ['first_name','last_name','professional_title','email','phone','address','linkedin','github','portfolio','website','nationality'];
        fields.forEach(f => {
            const el = container.querySelector(`#${f}`);
            if (el) {
                el.addEventListener('input', debounce(() => ResumeStore.set(f, el.value), 300));
                el.addEventListener('blur', () => ResumeStore.set(f, el.value));
            }
        });

        // Photo upload with client-side canvas compression (prevents LocalStorage QuotaExceededError)
        const photoInput = container.querySelector('#photo-input');
        if (photoInput) {
            photoInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (!file) return;
                if (file.size > 5 * 1024 * 1024) { showToast('File too large. Max 5MB.', 'error'); return; }
                const reader = new FileReader();
                reader.onload = (ev) => {
                    const img = new Image();
                    img.onload = () => {
                        try {
                            const canvas = document.createElement('canvas');
                            const maxDim = 360;
                            let w = img.width;
                            let h = img.height;
                            if (w > maxDim || h > maxDim) {
                                if (w > h) {
                                    h = Math.round((h * maxDim) / w);
                                    w = maxDim;
                                } else {
                                    w = Math.round((w * maxDim) / h);
                                    h = maxDim;
                                }
                            }
                            canvas.width = w;
                            canvas.height = h;
                            const ctx = canvas.getContext('2d');
                            ctx.drawImage(img, 0, 0, w, h);
                            const compressed = canvas.toDataURL('image/jpeg', 0.85);
                            ResumeStore.set('photo', compressed);
                        } catch (err) {
                            console.warn('Canvas compression failed, using original', err);
                            ResumeStore.set('photo', ev.target.result);
                        }
                        render(container);
                    };
                    img.onerror = () => {
                        showToast('Failed to parse image file.', 'error');
                    };
                    img.src = ev.target.result;
                };
                reader.readAsDataURL(file);
            });
        }

        const removePhoto = container.querySelector('#remove-photo');
        if (removePhoto) removePhoto.addEventListener('click', () => { ResumeStore.set('photo', null); render(container); });

        // Sample resume banner trigger
        container.querySelector('#btn-load-sample-banner')?.addEventListener('click', () => {
            document.getElementById('btn-profiles')?.click();
        });
    }

    return { render };
})();
