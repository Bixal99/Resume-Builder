// =============================================================================
// Profiles Modal & Role Variant Manager (Solves Application Fragmentation)
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    const profilesModal = document.getElementById('profiles-modal-overlay');
    if (!profilesModal) return;

    const btnProfiles = document.getElementById('btn-profiles');
    const btnRoleVariant = document.getElementById('btn-role-variant');
    const currentRoleBadge = document.getElementById('current-role-badge');
    const heroCtaBtn = document.getElementById('hero-cta-btn');
    const navCtaBtn = document.getElementById('nav-cta-btn');
    const ctaBottomBtn = document.getElementById('cta-bottom-btn');
    
    const btnCloseProfiles = document.getElementById('profiles-modal-close');
    const profilesListContainer = document.getElementById('profiles-list-container');
    const btnCreateProfile = document.getElementById('btn-create-profile');
    const inputNewProfile = document.getElementById('new-profile-name');

    const isLandingPage = window.location.pathname === '/' || window.location.pathname === '/index.html';

    function updateHeaderRoleBadge() {
        if (!currentRoleBadge) return;
        const active = ResumeStore.getActiveProfile();
        if (active) {
            const label = active.target_role || active.name || 'Default CV';
            currentRoleBadge.textContent = label.length > 22 ? label.substring(0, 20) + '...' : label;
        }
    }

    const renderProfilesList = () => {
        if (!profilesListContainer) return;
        
        // Ensure profiles are initialized before rendering
        if (ResumeStore.getProfiles().length === 0) {
            ResumeStore.load(); 
        }

        const profiles = ResumeStore.getProfiles();
        const activeId = ResumeStore.getActiveProfileId();
        
        const myProfilesHtml = `
            <div style="margin-bottom: 8px; font-weight: 600; font-size: 12px; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.5px;">
                Your Role Variants (${profiles.length})
            </div>
            ${profiles.map(p => `
                <div class="profile-list-item ${p.id === activeId ? 'active' : ''}" data-id="${p.id}">
                    <div class="profile-info">
                        <div class="profile-name">
                            <span>${escapeAttr(p.name)}</span>
                            ${p.target_role ? `<span style="font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 6px; background: #eff6ff; color: #2563eb; border: 1px solid #dbeafe;">🎯 ${escapeAttr(p.target_role)}</span>` : ''}
                        </div>
                        <div class="profile-date">Updated: ${new Date(p.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; flex-shrink: 0;">
                        <button type="button" class="btn-clone-profile" data-id="${p.id}" title="Duplicate this resume version for another role application">
                            📑 Clone
                        </button>
                        ${p.id === activeId ? `<span class="profile-badge">✓ Active</span>` : `<button type="button" class="btn-delete-profile" data-id="${p.id}" title="Delete Resume">🗑️</button>`}
                    </div>
                </div>
            `).join('')}
        `;

        const sampleResumes = (typeof SAMPLE_RESUMES !== 'undefined') ? SAMPLE_RESUMES : [];
        const sampleProfilesHtml = sampleResumes.length > 0 ? `
            <div style="margin-top: 18px; margin-bottom: 8px; font-weight: 600; font-size: 12px; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.5px;">
                🚀 Quick-Start with Sample Templates
            </div>
            <div class="sample-templates-list" style="display: flex; flex-direction: column; gap: 8px;">
                ${sampleResumes.map(s => `
                    <div class="sample-template-card" data-sample-id="${s.id}" style="padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-subtle, #f8fafc); cursor: pointer; transition: all 0.2s ease; display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1; padding-right: 10px;">
                            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 2px;">
                                <span style="font-weight: 600; font-size: 13px; color: var(--color-text);">${s.name}</span>
                                <span style="font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: #ede9fe; color: #4338ca; border: 1px solid #ddd6fe;">${s.badge}</span>
                            </div>
                            <div style="font-size: 11px; color: var(--color-text-secondary); line-height: 1.3;">${s.description}</div>
                        </div>
                        <button class="btn btn-sm btn-secondary btn-load-sample" data-sample-id="${s.id}" style="white-space: nowrap; font-size: 12px; padding: 4px 10px;">Use Template</button>
                    </div>
                `).join('')}
            </div>
        ` : '';

        profilesListContainer.innerHTML = myProfilesHtml + sampleProfilesHtml;
        updateHeaderRoleBadge();
    };

    const openProfilesModal = (e) => {
        if(e) e.preventDefault();
        renderProfilesList();
        profilesModal.classList.add('active');
    };

    // Attach to builder page buttons
    if (btnProfiles) btnProfiles.addEventListener('click', openProfilesModal);
    if (btnRoleVariant) btnRoleVariant.addEventListener('click', openProfilesModal);

    // Attach to landing page buttons
    if (heroCtaBtn) heroCtaBtn.addEventListener('click', openProfilesModal);
    if (navCtaBtn) navCtaBtn.addEventListener('click', openProfilesModal);
    if (ctaBottomBtn) ctaBottomBtn.addEventListener('click', openProfilesModal);

    const closeProfilesModal = () => {
        profilesModal.classList.remove('active');
        if(inputNewProfile) inputNewProfile.value = '';
    };

    if (btnCloseProfiles) btnCloseProfiles.addEventListener('click', closeProfilesModal);
    profilesModal.addEventListener('click', (e) => {
        if (e.target === profilesModal) closeProfilesModal();
    });

    // Handle profile selection, cloning, and deletion
    if (profilesListContainer) {
        profilesListContainer.addEventListener('click', async (e) => {
            // Clone / Duplicate for Role
            const cloneBtn = e.target.closest('.btn-clone-profile');
            if (cloneBtn) {
                e.stopPropagation();
                const sourceId = cloneBtn.dataset.id;
                const src = ResumeStore.getProfiles().find(p => p.id === sourceId);
                const defaultName = src ? `${src.name} (Role Variant)` : 'New Variant';

                const roleName = (typeof showPromptDialog === 'function')
                    ? await showPromptDialog({
                        title: 'Clone for Target Role',
                        message: `Create a duplicate of "${src ? src.name : 'Resume'}" customized for a specific role:`,
                        icon: '🎯',
                        defaultValue: defaultName,
                        placeholder: 'e.g. Senior Frontend Engineer @ Stripe',
                        confirmText: 'Clone Resume'
                    })
                    : prompt(`Enter a role/job title for this new variant:`, defaultName);

                if (roleName) {
                    ResumeStore.cloneProfile(sourceId, roleName, roleName);
                    renderProfilesList();
                    updateHeaderRoleBadge();
                    if (typeof showToast === 'function') {
                        showToast(`Cloned into "${roleName}" variant without affecting original!`, 'success');
                    }
                }
                return;
            }

            // Delete profile
            const deleteBtn = e.target.closest('.btn-delete-profile');
            if (deleteBtn) {
                e.stopPropagation();
                const profileId = deleteBtn.dataset.id;
                const targetProfile = ResumeStore.getProfiles().find(p => p.id === profileId);
                const targetName = targetProfile ? targetProfile.name : 'this resume';

                const confirmed = (typeof showConfirmDialog === 'function')
                    ? await showConfirmDialog({
                        title: 'Delete Resume Variant?',
                        message: `Are you sure you want to delete "${targetName}"? This action cannot be undone.`,
                        icon: '🗑️',
                        confirmText: 'Delete Resume',
                        isDanger: true
                    })
                    : confirm(`Are you sure you want to delete this resume?`);

                if (confirmed) {
                    ResumeStore.deleteProfile(profileId);
                    renderProfilesList();
                    updateHeaderRoleBadge();
                    if (typeof showToast === 'function') {
                        showToast(`Deleted "${targetName}"`, 'info');
                    }
                }
                return;
            }

            // Handle sample template selection
            const sampleCard = e.target.closest('.sample-template-card');
            if (sampleCard) {
                const sampleId = sampleCard.dataset.sampleId;
                const sample = (typeof SAMPLE_RESUMES !== 'undefined') ? SAMPLE_RESUMES.find(s => s.id === sampleId) : null;
                if (sample) {
                    const profileName = `${sample.name}`;
                    ResumeStore.createProfile(profileName);
                    const clonedData = JSON.parse(JSON.stringify(sample.data));
                    ResumeStore.set(clonedData);
                    ResumeStore.save();
                    closeProfilesModal();
                    updateHeaderRoleBadge();
                    if (isLandingPage) {
                        window.location.href = '/builder';
                    } else {
                        if (typeof StepperComponent !== 'undefined') {
                            StepperComponent.goToStep(0, true);
                        }
                        if (typeof showToast === 'function') {
                            showToast(`Loaded "${sample.name}" sample resume!`, 'success');
                        }
                    }
                }
                return;
            }

            // Switch to clicked profile
            const item = e.target.closest('.profile-list-item');
            if (item) {
                const id = item.dataset.id;
                if (id !== ResumeStore.getActiveProfileId()) {
                    ResumeStore.switchProfile(id);
                }
                closeProfilesModal();
                updateHeaderRoleBadge();
                if (isLandingPage) {
                    window.location.href = '/builder';
                } else {
                    if (typeof StepperComponent !== 'undefined') {
                        StepperComponent.goToStep(0);
                    }
                    if (typeof showToast === 'function') {
                        showToast('Switched to resume variant: ' + ResumeStore.getProfiles().find(p=>p.id===id).name, 'success');
                    }
                }
            }
        });
    }

    // Handle create
    if (btnCreateProfile && inputNewProfile) {
        btnCreateProfile.addEventListener('click', () => {
            const name = inputNewProfile.value.trim() || 'New Resume';
            ResumeStore.createProfile(name, name);
            closeProfilesModal();
            updateHeaderRoleBadge();
            if (isLandingPage) {
                window.location.href = '/builder';
            } else {
                if (typeof StepperComponent !== 'undefined') {
                    StepperComponent.goToStep(0);
                }
                if (typeof showToast === 'function') {
                    showToast('Created new resume variant: ' + name, 'success');
                }
            }
        });
    }

    // Initialize header badge
    setTimeout(updateHeaderRoleBadge, 200);
});
