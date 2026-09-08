// =============================================================================
// JSON Resume Schema Exporter & Importer (Standard JSON Resume compatibility)
// =============================================================================

const JsonResumeConverter = (() => {
    /**
     * Converts Resumate internal store data to standard JSON Resume format.
     */
    function toStandardJson(data) {
        const d = data || {};
        const fullName = [d.first_name, d.last_name].filter(Boolean).join(' ') || '';

        const profiles = [];
        if (d.linkedin) {
            profiles.push({ network: 'LinkedIn', url: d.linkedin, username: d.linkedin.split('/').filter(Boolean).pop() || '' });
        }
        if (d.github) {
            profiles.push({ network: 'GitHub', url: d.github, username: d.github.split('/').filter(Boolean).pop() || '' });
        }

        return {
            $schema: "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
            basics: {
                name: fullName,
                label: d.professional_title || '',
                image: d.photo_url || '',
                email: d.email || '',
                phone: d.phone || '',
                url: d.website || '',
                summary: d.summary || '',
                location: {
                    address: d.address || '',
                    city: '',
                    countryCode: '',
                    region: ''
                },
                profiles: profiles
            },
            work: (d.experience || []).map(exp => ({
                name: exp.company || '',
                position: exp.position || '',
                url: '',
                startDate: exp.start_date || '',
                endDate: exp.is_current ? 'Present' : (exp.end_date || ''),
                summary: exp.description || '',
                highlights: (exp.description || '').split('\n').map(l => l.replace(/^[•\-\*]\s*/, '').trim()).filter(Boolean)
            })),
            volunteer: (d.volunteer || []).map(v => ({
                organization: v.organization || '',
                position: v.role || '',
                url: '',
                startDate: v.start_date || '',
                endDate: v.is_current ? 'Present' : (v.end_date || ''),
                summary: v.description || '',
                highlights: []
            })),
            education: (d.education || []).map(edu => ({
                institution: edu.institution || '',
                url: '',
                area: edu.field_of_study || '',
                studyType: edu.degree || '',
                startDate: edu.start_date || '',
                endDate: edu.end_date || '',
                score: edu.gpa || '',
                courses: []
            })),
            awards: (d.awards || []).map(a => ({
                title: a.title || '',
                date: a.date || '',
                awarder: a.issuer || '',
                summary: a.description || ''
            })),
            certificates: (d.certifications || []).map(c => ({
                name: c.name || '',
                date: c.issue_date || '',
                issuer: c.issuer || '',
                url: c.url || ''
            })),
            skills: (d.skills || []).map(s => ({
                name: s.name || '',
                level: s.level ? String(s.level) : 'Intermediate',
                keywords: [s.category || 'General'].filter(Boolean)
            })),
            languages: (d.languages || []).map(l => ({
                language: l.name || '',
                fluency: l.fluency || 'Fluent'
            })),
            projects: (d.projects || []).map(p => ({
                name: p.title || '',
                description: p.description || '',
                highlights: [],
                keywords: Array.isArray(p.technologies) ? p.technologies : [],
                url: p.url || p.github_url || ''
            })),
            references: (d.references || []).map(r => ({
                name: r.name || '',
                reference: `${r.title || ''}${r.company ? ' at ' + r.company : ''}${r.email ? ' (' + r.email + ')' : ''}`
            })),
            meta: {
                canonical: "https://resumate.app",
                version: "v1.0.0",
                lastModified: new Date().toISOString(),
                resumate: {
                    first_name: d.first_name || '',
                    last_name: d.last_name || '',
                    section_order: d.section_order || [],
                    hidden_sections: d.hidden_sections || [],
                    theme_settings: d.theme_settings || {}
                }
            }
        };
    }

    /**
     * Converts standard JSON Resume or native Resumate export into Resumate internal store format.
     */
    function fromStandardJson(json) {
        if (!json || typeof json !== 'object') {
            throw new Error('Invalid JSON resume format.');
        }

        if (json.first_name !== undefined || json.last_name !== undefined) {
            return json;
        }

        const metaResumate = json.meta?.resumate || {};
        const basics = json.basics || {};
        let firstName = metaResumate.first_name || '';
        let lastName = metaResumate.last_name || '';

        if (!firstName && !lastName && basics.name) {
            const parts = basics.name.trim().split(/\s+/);
            firstName = parts[0] || '';
            lastName = parts.slice(1).join(' ') || '';
        }

        let linkedin = '';
        let github = '';
        if (Array.isArray(basics.profiles)) {
            basics.profiles.forEach(p => {
                const net = (p.network || '').toLowerCase();
                if (net.includes('linkedin') && p.url) linkedin = p.url;
                if (net.includes('github') && p.url) github = p.url;
            });
        }

        const experience = (json.work || []).map((w, idx) => ({
            id: `exp_${Date.now()}_${idx}`,
            company: w.name || '',
            position: w.position || '',
            location: w.location || '',
            start_date: w.startDate || '',
            end_date: (w.endDate === 'Present' ? '' : w.endDate) || '',
            is_current: (w.endDate === 'Present' || !w.endDate),
            description: w.summary || (Array.isArray(w.highlights) ? w.highlights.map(h => `• ${h}`).join('\n') : '')
        }));

        const education = (json.education || []).map((e, idx) => ({
            id: `edu_${Date.now()}_${idx}`,
            institution: e.institution || '',
            degree: e.studyType || '',
            field_of_study: e.area || '',
            location: '',
            start_date: e.startDate || '',
            end_date: e.endDate || '',
            gpa: e.score || '',
            description: Array.isArray(e.courses) && e.courses.length ? `Relevant Courses: ${e.courses.join(', ')}` : ''
        }));

        const skills = [];
        (json.skills || []).forEach((s, idx) => {
            if (Array.isArray(s.keywords) && s.keywords.length > 0) {
                s.keywords.forEach((kw, kwIdx) => {
                    skills.push({
                        id: `skill_${Date.now()}_${idx}_${kwIdx}`,
                        name: kw,
                        category: s.name || 'technical',
                        level: 3
                    });
                });
            } else if (s.name) {
                skills.push({
                    id: `skill_${Date.now()}_${idx}`,
                    name: s.name,
                    category: 'technical',
                    level: 3
                });
            }
        });

        const projects = (json.projects || []).map((p, idx) => ({
            id: `proj_${Date.now()}_${idx}`,
            title: p.name || '',
            description: p.description || (Array.isArray(p.highlights) ? p.highlights.join('\n') : ''),
            url: p.url || '',
            github_url: '',
            technologies: Array.isArray(p.keywords) ? p.keywords : []
        }));

        const languages = (json.languages || []).map((l, idx) => ({
            id: `lang_${Date.now()}_${idx}`,
            name: l.language || l.name || '',
            fluency: l.fluency || 'Fluent'
        }));

        const certifications = (json.certificates || []).map((c, idx) => ({
            id: `cert_${Date.now()}_${idx}`,
            name: c.name || '',
            issuer: c.issuer || '',
            issue_date: c.date || '',
            expiry_date: '',
            credential_id: '',
            url: c.url || ''
        }));

        const awards = (json.awards || []).map((a, idx) => ({
            id: `award_${Date.now()}_${idx}`,
            title: a.title || '',
            issuer: a.awarder || '',
            date: a.date || '',
            description: a.summary || ''
        }));

        const volunteer = (json.volunteer || []).map((v, idx) => ({
            id: `vol_${Date.now()}_${idx}`,
            organization: v.organization || '',
            role: v.position || '',
            location: '',
            start_date: v.startDate || '',
            end_date: v.endDate === 'Present' ? '' : (v.endDate || ''),
            is_current: (v.endDate === 'Present' || !v.endDate),
            description: v.summary || ''
        }));

        const references = (json.references || []).map((r, idx) => ({
            id: `ref_${Date.now()}_${idx}`,
            name: r.name || '',
            title: r.reference || '',
            company: '',
            email: '',
            phone: '',
            relationship_type: 'Professional'
        }));

        return {
            first_name: firstName,
            last_name: lastName,
            professional_title: basics.label || '',
            email: basics.email || '',
            phone: basics.phone || '',
            address: basics.location?.address || '',
            website: basics.url || '',
            linkedin: linkedin,
            github: github,
            photo_url: basics.image || '',
            summary: basics.summary || '',
            experience,
            education,
            skills,
            projects,
            languages,
            certifications,
            awards,
            volunteer,
            references,
            section_order: metaResumate.section_order || undefined,
            hidden_sections: metaResumate.hidden_sections || undefined,
            theme_settings: metaResumate.theme_settings || undefined
        };
    }

    /**
     * Triggers browser download of current resume state as standard JSON.
     */
    function exportFile() {
        const rawData = ResumeStore.getResumeData();
        const exportObj = toStandardJson(rawData);
        const jsonString = JSON.stringify(exportObj, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const filename = `${rawData.first_name || 'resume'}_${rawData.last_name || ''}_resume.json`.toLowerCase().replace(/\s+/g, '_');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Reads a user-uploaded .json file and updates ResumeStore.
     */
    function importFile(file, onSuccess, onError) {
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const parsed = JSON.parse(e.target.result);
                const internalState = fromStandardJson(parsed);
                ResumeStore.set(internalState);
                ResumeStore.save();
                if (typeof onSuccess === 'function') onSuccess(internalState);
            } catch (err) {
                console.error('JSON Resume import failed:', err);
                if (typeof onError === 'function') onError(err);
            }
        };
        reader.onerror = () => {
            if (typeof onError === 'function') onError(new Error('Failed to read file.'));
        };
        reader.readAsText(file);
    }

    return {
        toStandardJson,
        fromStandardJson,
        exportFile,
        importFile
    };
})();
