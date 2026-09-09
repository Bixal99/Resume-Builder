// =============================================================================
// Centralized State Store with Reactive Updates
// =============================================================================

const ResumeStore = (() => {
    const PROFILES_KEY = 'rb_profiles';
    const ACTIVE_PROFILE_KEY = 'rb_active_profile_id';
    const LEGACY_STORAGE_KEY = 'rb_resume_data';
    const listeners = [];
    let autoSaveTimer = null;

    const defaultState = () => ({
        id: null,
        session_id: getSessionId(),
        title: 'Untitled Resume',
        template_id: 'modern',
        page_size: 'A4',
        photo: null,
        first_name: '', last_name: '', professional_title: '',
        email: '', phone: '', address: '',
        linkedin: '', github: '', portfolio: '', website: '', nationality: '',
        summary: '',
        education: [],
        experience: [],
        projects: [],
        skills: [],
        languages: [],
        certifications: [],
        awards: [],
        volunteer: [],
        references: [],
        section_order: ['summary', 'experience', 'education', 'projects', 'skills', 'certifications', 'languages', 'awards', 'volunteer', 'references'],
        hidden_sections: [],
    });

    let state = defaultState();
    let profiles = [];
    let activeProfileId = null;

    function generateId(prefix = '') {
        const id = Date.now().toString(36) + Math.random().toString(36).substring(2, 9);
        return prefix ? `${prefix}_${id}` : id;
    }

    const ARRAY_SECTIONS = [
        'education', 'experience', 'projects', 'skills',
        'languages', 'certifications', 'awards', 'volunteer', 'references'
    ];

    function normalizeSkillCategory(cat) {
        if (!cat) return 'Technical Skills';
        let c = String(cat).trim().replace(/[:]+$/, '').toLowerCase();
        c = c.replace(/&amp;/g, '&').replace(/\s+/g, ' ');
        if (c.includes('framework') || c.includes('framwork') || c.includes('librar')) {
            return 'Frameworks & Libraries';
        }
        if (c.includes('tool') || c.includes('platform') || c.includes('devops')) {
            return 'Tools & Platforms';
        }
        if (c.includes('soft') || c.includes('interpersonal') || c.includes('management')) {
            return 'Soft Skills';
        }
        if (c.includes('tech') || c.includes('language') || c.includes('coding') || c.includes('program') || c.includes('competenc')) {
            return 'Technical Skills';
        }
        return String(cat).trim().replace(/[:]+$/, '');
    }

    function splitDegreeAndField(degree, fieldOfStudy) {
        let d = (degree || '').trim();
        let f = (fieldOfStudy || '').trim();
        if (!d) return { degree: d, field_of_study: f };
        if (f) {
            d = d.replace(new RegExp('\\s+(?:in|–|-|—)\\s+' + f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[.\\s]*$', 'i'), '').trim();
            return { degree: d, field_of_study: f };
        }
        const mIn = d.match(/^(.*?)\s+in\s+(.+)$/i);
        if (mIn) return { degree: mIn[1].trim().replace(/[,.;]+$/, ''), field_of_study: mIn[2].trim().replace(/[,.;]+$/, '') };
        const mDash = d.match(/^(.*?)\s+[-–—]\s+(.+)$/);
        if (mDash) return { degree: mDash[1].trim().replace(/[,.;]+$/, ''), field_of_study: mDash[2].trim().replace(/[,.;]+$/, '') };
        const mParen = d.match(/^(.*?)\s*\(([^)]+)\)\s*$/);
        if (mParen) return { degree: mParen[1].trim(), field_of_study: mParen[2].trim() };
        return { degree: d, field_of_study: f };
    }

    function ensureItemIds(targetState) {
        if (!targetState || typeof targetState !== 'object') return;
        ARRAY_SECTIONS.forEach(section => {
            if (Array.isArray(targetState[section])) {
                targetState[section].forEach((item, idx) => {
                    if (item && typeof item === 'object' && !item.id) {
                        item.id = generateId(section.substring(0, 4));
                    }
                });
            }
        });

        // Clean & separate education degree and field_of_study
        if (Array.isArray(targetState.education)) {
            targetState.education.forEach(item => {
                if (item && typeof item === 'object' && item.degree && (!item.field_of_study || !item.field_of_study.trim())) {
                    const split = splitDegreeAndField(item.degree, item.field_of_study);
                    if (split.field_of_study) {
                        item.degree = split.degree;
                        item.field_of_study = split.field_of_study;
                    }
                }
            });
        }

        // Clean & deduplicate skills and normalize categories
        if (Array.isArray(targetState.skills)) {
            const seen = new Set();
            const deduplicated = [];
            targetState.skills.forEach(skill => {
                if (skill && typeof skill === 'object' && skill.name) {
                    const sName = String(skill.name).trim();
                    const sLower = sName.toLowerCase();
                    if (sName && !seen.has(sLower)) {
                        seen.add(sLower);
                        skill.name = sName;
                        skill.category = normalizeSkillCategory(skill.category);
                        deduplicated.push(skill);
                    }
                }
            });
            targetState.skills = deduplicated;
        }
    }

    function initProfiles() {
        try {
            const savedProfiles = localStorage.getItem(PROFILES_KEY);
            if (savedProfiles) {
                profiles = JSON.parse(savedProfiles);
            }
            
            const legacyData = localStorage.getItem(LEGACY_STORAGE_KEY);
            
            if (profiles.length === 0) {
                // Migration or fresh start
                const defaultProfileId = generateId('prof');
                profiles = [{
                    id: defaultProfileId,
                    name: legacyData ? 'Hasan Ahmad' : 'My Resume',
                    updated_at: new Date().toISOString()
                }];
                localStorage.setItem(PROFILES_KEY, JSON.stringify(profiles));
                
                if (legacyData) {
                    localStorage.setItem(`rb_resume_data_${defaultProfileId}`, legacyData);
                    localStorage.removeItem(LEGACY_STORAGE_KEY);
                }
                activeProfileId = defaultProfileId;
                localStorage.setItem(ACTIVE_PROFILE_KEY, activeProfileId);
            } else {
                activeProfileId = localStorage.getItem(ACTIVE_PROFILE_KEY);
                if (!activeProfileId || !profiles.find(p => p.id === activeProfileId)) {
                    activeProfileId = profiles[0].id;
                    localStorage.setItem(ACTIVE_PROFILE_KEY, activeProfileId);
                }
            }
        } catch (e) {
            console.error('Profile initialization failed', e);
        }
    }

    function getProfiles() {
        return profiles;
    }

    function getActiveProfileId() {
        return activeProfileId;
    }

    function createProfile(name, targetRole = '') {
        save(); // Save current state before switching
        const id = generateId('prof');
        profiles.push({
            id,
            name: name || 'New Resume',
            target_role: targetRole || '',
            updated_at: new Date().toISOString()
        });
        localStorage.setItem(PROFILES_KEY, JSON.stringify(profiles));
        switchProfile(id);
    }

    function cloneProfile(sourceId, newName, targetRole = '') {
        save();
        const srcId = sourceId || activeProfileId;
        const sourceData = localStorage.getItem(`rb_resume_data_${srcId}`);
        const id = generateId('prof');
        const srcProfile = profiles.find(p => p.id === srcId);
        const name = newName || (srcProfile ? `${srcProfile.name} (Role Variant)` : 'New Variant');
        
        profiles.push({
            id,
            name,
            target_role: targetRole || (srcProfile ? srcProfile.target_role || '' : ''),
            updated_at: new Date().toISOString()
        });
        localStorage.setItem(PROFILES_KEY, JSON.stringify(profiles));

        if (sourceData) {
            try {
                const parsed = JSON.parse(sourceData);
                parsed.title = name;
                localStorage.setItem(`rb_resume_data_${id}`, JSON.stringify(parsed));
            } catch (e) {
                console.error('Failed to copy profile data:', e);
            }
        }

        switchProfile(id);
        return id;
    }

    function getActiveProfile() {
        return profiles.find(p => p.id === activeProfileId) || null;
    }

    function updateProfileInfo(id, meta = {}) {
        const p = profiles.find(p => p.id === id);
        if (p) {
            if (meta.name) p.name = meta.name;
            if (meta.target_role !== undefined) p.target_role = meta.target_role;
            p.updated_at = new Date().toISOString();
            localStorage.setItem(PROFILES_KEY, JSON.stringify(profiles));
            notify();
        }
    }

    function switchProfile(id) {
        if (!profiles.find(p => p.id === id)) return;
        save();
        activeProfileId = id;
        localStorage.setItem(ACTIVE_PROFILE_KEY, activeProfileId);
        load();
    }

    function deleteProfile(id) {
        profiles = profiles.filter(p => p.id !== id);
        localStorage.removeItem(`rb_resume_data_${id}`);
        if (profiles.length === 0) {
            createProfile('My Resume');
        } else if (activeProfileId === id) {
            switchProfile(profiles[0].id);
        } else {
            localStorage.setItem(PROFILES_KEY, JSON.stringify(profiles));
        }
    }

    function updateProfileTimestamp() {
        const p = profiles.find(p => p.id === activeProfileId);
        if (p) {
            p.updated_at = new Date().toISOString();
            localStorage.setItem(PROFILES_KEY, JSON.stringify(profiles));
        }
    }

    function load() {
        if (!activeProfileId) initProfiles();
        try {
            const saved = localStorage.getItem(`rb_resume_data_${activeProfileId}`);
            if (saved) {
                const parsed = JSON.parse(saved);
                state = { ...defaultState(), ...parsed, session_id: getSessionId() };
            } else {
                state = defaultState();
            }
        } catch (e) { console.warn('Failed to load saved state', e); state = defaultState(); }
        ensureItemIds(state);
        notify();
    }

    function save() {
        if (!activeProfileId) return;
        try { 
            ensureItemIds(state);
            localStorage.setItem(`rb_resume_data_${activeProfileId}`, JSON.stringify(state)); 
            updateProfileTimestamp();
            updateSaveStatus('saved');
        } catch (e) {
            console.error('Save failed:', e);
            if (e.name === 'QuotaExceededError' || e.code === 22) {
                // Emergency fallback: If photo was too large, save text contents so user work is never lost
                if (state.photo) {
                    try {
                        const stateWithoutPhoto = { ...state, photo: null };
                        localStorage.setItem(`rb_resume_data_${activeProfileId}`, JSON.stringify(stateWithoutPhoto));
                        console.warn('Storage quota reached. Saved resume text data safely without photo.');
                        updateSaveStatus('saved');
                        return;
                    } catch (fallbackErr) {
                        console.error('Fallback save failed:', fallbackErr);
                    }
                }
            }
            updateSaveStatus('error');
        }
    }

    function triggerAutoSave() {
        updateSaveStatus('saving');
        if (autoSaveTimer) clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(() => {
            save();
        }, 500);
    }

    // Immediately flush pending auto-save before closing or reloading the window
    if (typeof window !== 'undefined') {
        window.addEventListener('beforeunload', () => {
            if (autoSaveTimer) {
                clearTimeout(autoSaveTimer);
                save();
            }
        });
    }

    function get(key) { return key ? state[key] : { ...state }; }

    function set(key, value) {
        if (typeof key === 'object') { 
            Object.assign(state, key); 
        } else { 
            state[key] = value; 
        }
        ensureItemIds(state);
        triggerAutoSave();
        notify();
    }

    function reset() { state = defaultState(); save(); notify(); }

    function subscribe(fn) { listeners.push(fn); return () => { const i = listeners.indexOf(fn); if (i > -1) listeners.splice(i, 1); }; }

    function notify() { listeners.forEach(fn => { try { fn(state); } catch (e) { console.error(e); } }); }

    function revert() {
        load(); // Reload state from localStorage
    }

    function updateSaveStatus(status) {
        const el = document.getElementById('save-status');
        if (!el) return;
        const textEl = el.querySelector('.save-text');
        el.classList.remove('saving', 'error');
        if (status === 'saving') { 
            el.classList.add('saving'); 
            if (textEl) textEl.textContent = 'Saving...'; 
        } else if (status === 'saved') { 
            if (textEl) textEl.textContent = 'Auto-saved'; 
        } else if (status === 'error') { 
            el.classList.add('error'); 
            if (textEl) textEl.textContent = 'Save failed'; 
        }
    }

    function getResumeData() {
        ensureItemIds(state);
        const d = { ...state };
        delete d.id;
        delete d.session_id;
        return d;
    }

    return { 
        load, save, get, set, reset, subscribe, getResumeData, defaultState,
        getProfiles, getActiveProfileId, getActiveProfile, createProfile, cloneProfile,
        updateProfileInfo, switchProfile, deleteProfile,
        revert, updateSaveStatus, generateId
    };
})();
