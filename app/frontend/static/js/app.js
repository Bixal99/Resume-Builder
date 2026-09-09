// =============================================================================
// Main Application Entry Point
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Load saved state from localStorage
    ResumeStore.load();

    // Initialize stepper
    const stepperNav = document.getElementById('stepper-nav');
    StepperComponent.render(stepperNav);
    StepperComponent.goToStep(0);

    // Initialize live preview
    PreviewManager.init();

    // --- Navigation Buttons ---
    document.getElementById('btn-prev-step')?.addEventListener('click', () => StepperComponent.prev());
    document.getElementById('btn-next-step')?.addEventListener('click', () => StepperComponent.next());

    // --- Profiles & Samples Buttons ---
    document.getElementById('btn-quick-samples')?.addEventListener('click', () => {
        document.getElementById('btn-profiles')?.click();
    });

    // --- JSON Resume Export & Import ---
    const btnExportJson = document.getElementById('btn-export-json');
    if (btnExportJson) {
        btnExportJson.addEventListener('click', () => {
            try {
                JsonResumeConverter.exportFile();
                if (typeof showToast === 'function') {
                    showToast('Exported JSON Resume successfully!', 'success');
                }
            } catch (err) {
                console.error('Export failed:', err);
                if (typeof showToast === 'function') {
                    showToast('Failed to export JSON: ' + err.message, 'error');
                }
            }
        });
    }

    const btnImportJson = document.getElementById('btn-import-json');
    const jsonImportInput = document.getElementById('json-import-input');
    if (btnImportJson && jsonImportInput) {
        btnImportJson.addEventListener('click', () => {
            jsonImportInput.click();
        });

        jsonImportInput.addEventListener('change', (e) => {
            const file = e.target.files?.[0];
            if (!file) return;

            JsonResumeConverter.importFile(
                file,
                (importedData) => {
                    StepperComponent.goToStep(0, true);
                    if (typeof showToast === 'function') {
                        showToast('JSON Resume imported successfully!', 'success');
                    }
                    jsonImportInput.value = '';
                },
                (err) => {
                    if (typeof showToast === 'function') {
                        showToast('JSON Import Error: ' + err.message, 'error');
                    }
                    jsonImportInput.value = '';
                }
            );
        });
    }

    // --- Auto-fill from PDF (Real-Time In-Screen AI Extraction) ---
    const btnAiImport = document.getElementById('btn-ai-import');
    const aiImportInput = document.getElementById('ai-import-input');
    const liveBanner = document.getElementById('live-extraction-banner');
    const bannerStatusTitle = document.getElementById('extraction-status-title');
    const bannerDetailText = document.getElementById('extraction-detail-text');
    const bannerPctBadge = document.getElementById('extraction-pct-badge');
    const bannerProgressBarFill = document.getElementById('extraction-progress-bar-fill');
    const bannerChipsContainer = document.getElementById('extraction-fields-chips');
    const bannerCloseBtn = document.getElementById('extraction-banner-close');

    if (bannerCloseBtn && liveBanner) {
        bannerCloseBtn.addEventListener('click', () => {
            liveBanner.style.opacity = '0';
            setTimeout(() => {
                liveBanner.style.display = 'none';
                liveBanner.style.opacity = '1';
            }, 250);
        });
    }

    function updateExtractionBanner(pct, title, detail) {
        if (pct !== undefined && pct !== null) {
            let targetPct;
            if (pct === 0) {
                targetPct = 0;
            } else {
                const curWidth = bannerProgressBarFill ? (parseFloat(bannerProgressBarFill.style.width) || 0) : 0;
                targetPct = Math.max(curWidth, Math.min(100, Math.round(pct)));
            }
            if (bannerPctBadge) bannerPctBadge.textContent = `${targetPct}%`;
            if (bannerProgressBarFill) bannerProgressBarFill.style.width = `${targetPct}%`;
        }
        if (bannerStatusTitle && title) bannerStatusTitle.textContent = title;
        if (bannerDetailText && detail) bannerDetailText.textContent = detail;
    }

    function addPlacedFieldChip(label, value) {
        if (!bannerChipsContainer) return;
        const chip = document.createElement('div');
        chip.className = 'extraction-chip';
        const displayVal = typeof value === 'string'
            ? (value.length > 26 ? value.substring(0, 26) + '...' : value)
            : `${value} items`;
        chip.innerHTML = `✓ ${sanitizeHTML(label)}: <strong>${sanitizeHTML(displayVal)}</strong>`;
        bannerChipsContainer.appendChild(chip);
        chip.scrollIntoView({ behavior: 'smooth', inline: 'nearest', block: 'nearest' });
    }

    function populateAndHighlightField(fieldKey, value) {
        const inputEl = document.getElementById(fieldKey);
        if (inputEl) {
            inputEl.value = value || '';
            inputEl.classList.remove('field-live-populating');
            void inputEl.offsetWidth; // Force CSS animation restart
            inputEl.classList.add('field-live-populating');
            setTimeout(() => {
                if (inputEl) inputEl.classList.remove('field-live-populating');
            }, 2200);
        }
    }

    if (btnAiImport && aiImportInput) {
        btnAiImport.addEventListener('click', () => {
            aiImportInput.click();
        });

        aiImportInput.addEventListener('change', async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;

            const originalHtml = btnAiImport.innerHTML;
            btnAiImport.disabled = true;
            btnAiImport.innerHTML = '⚡ Placing Fields...';

            // Navigate to step 0 (Personal) so user immediately sees fields filling into the form on screen
            if (typeof StepperComponent !== 'undefined') {
                StepperComponent.goToStep(0);
            }

            // Reveal and initialize in-screen extraction banner
            if (liveBanner) {
                liveBanner.classList.remove('completed');
                liveBanner.style.display = 'block';
                liveBanner.style.opacity = '1';
                if (bannerCloseBtn) bannerCloseBtn.style.display = 'none';
                if (bannerChipsContainer) bannerChipsContainer.innerHTML = '';
                if (bannerProgressBarFill) bannerProgressBarFill.style.width = '0%';
                if (bannerPctBadge) bannerPctBadge.textContent = '0%';
                updateExtractionBanner(5, '⚡ AI Extracting Resume Text...', `Reading "${file.name}" (${(file.size / 1024).toFixed(1)} KB)`);
            }

            // Prepare live RHS preview with visual placeholder slots ready for streaming
            if (typeof PreviewManager !== 'undefined' && PreviewManager.prepareForLiveExtraction) {
                PreviewManager.prepareForLiveExtraction();
            }

            const placedSet = new Set();

            try {
                const parsedData = await API.parseResumeStream(file, (progress) => {
                    if (progress.event === 'status') {
                        updateExtractionBanner(
                            progress.pct,
                            `⚡ ${progress.label}`,
                            progress.detail || 'Extracting structured data from resume...'
                        );
                    } else if (progress.event === 'token') {
                        if (progress.chars && bannerDetailText) {
                            bannerDetailText.textContent = `Streaming neural tokens (${progress.chars} characters processed)...`;
                        }
                        if (progress.pct !== undefined) {
                            updateExtractionBanner(progress.pct);
                        }
                    } else if (progress.event === 'field_update') {
                        const field = progress.field === 'location' ? 'address' : progress.field;
                        const val = progress.value;

                        if (!placedSet.has(field)) {
                            placedSet.add(field);

                            // 1. Immediately store into central state
                            ResumeStore.set(field, val);

                            // 2. Direct real-time visual injection into RHS preview DOM (instantaneous!)
                            if (typeof PreviewManager !== 'undefined' && PreviewManager.updateFieldDirectly) {
                                PreviewManager.updateFieldDirectly(field, val);
                            }

                            // 3. Real-time form input population with glow animation on screen
                            populateAndHighlightField(field, val);

                            // 4. Update banner ticker and status
                            const fieldLabel = field.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
                            addPlacedFieldChip(fieldLabel, val);
                            updateExtractionBanner(
                                progress.pct,
                                `⚡ Placed ${fieldLabel} into template...`,
                                `✓ Field "${fieldLabel}" placed into template spot`
                            );
                        }
                    } else if (progress.event === 'skill_item') {
                        const skill = progress.skill;
                        if (skill && skill.name) {
                            const sName = skill.name.trim();

                            // 1. Central store update (avoid duplicates)
                            const currentSkills = ResumeStore.get('skills') || [];
                            if (!currentSkills.some(s => (s.name || '').trim().toLowerCase() === sName.toLowerCase())) {
                                currentSkills.push(skill);
                                ResumeStore.set('skills', currentSkills);
                            }

                            // 2. Direct real-time visual injection into RHS preview DOM (one-by-one live!)
                            if (typeof PreviewManager !== 'undefined' && PreviewManager.addSkillDirectly) {
                                PreviewManager.addSkillDirectly(skill);
                            }

                            // 3. Update placed chips and banner ticker
                            addPlacedFieldChip(`SKILL: ${sName}`, sName);
                            updateExtractionBanner(
                                progress.pct,
                                `⚡ Placed Skill: ${sName}...`,
                                `✓ Placed skill "${sName}" into template`
                            );

                            // 4. If current form step is on skills, refresh the form step
                            if (typeof StepperComponent !== 'undefined') {
                                const cur = StepperComponent.getCurrentStep();
                                if (cur && cur.id === 'skills') {
                                    StepperComponent.renderFormStep();
                                }
                            }
                        }
                    } else if (progress.event === 'section_item') {
                        const section = progress.section;
                        const item = progress.item;
                        if (section && item) {
                            // 1. Central store update (avoid duplicates by key fields)
                            const currentList = ResumeStore.get(section) || [];
                            let isDuplicate = false;
                            if (section === 'projects') {
                                isDuplicate = currentList.some(p => p.title && item.title && p.title.trim().toLowerCase() === item.title.trim().toLowerCase());
                            } else if (section === 'experience') {
                                isDuplicate = currentList.some(e => e.company && item.company && e.company.trim().toLowerCase() === item.company.trim().toLowerCase() && e.position === item.position);
                            } else if (section === 'education') {
                                isDuplicate = currentList.some(e => e.institution && item.institution && e.institution.trim().toLowerCase() === item.institution.trim().toLowerCase());
                            } else if (section === 'certifications') {
                                isDuplicate = currentList.some(c => c.name && item.name && c.name.trim().toLowerCase() === item.name.trim().toLowerCase());
                            } else if (section === 'languages') {
                                isDuplicate = currentList.some(l => l.name && item.name && l.name.trim().toLowerCase() === item.name.trim().toLowerCase());
                            }

                            if (!isDuplicate) {
                                currentList.push(item);
                                ResumeStore.set(section, currentList);
                            }

                            // 2. Direct real-time visual injection into RHS preview DOM (one-by-one live!)
                            if (typeof PreviewManager !== 'undefined' && PreviewManager.addSectionItemDirectly) {
                                PreviewManager.addSectionItemDirectly(section, item);
                            }

                            // 3. Update placed chips and banner ticker
                            const itemTitle = item.title || item.position || item.degree || item.name || `${section} entry`;
                            const singularLabel = section.endsWith('s') ? section.slice(0, -1).toUpperCase() : section.toUpperCase();
                            addPlacedFieldChip(`${singularLabel}: ${itemTitle}`, itemTitle);
                            updateExtractionBanner(
                                progress.pct,
                                `⚡ Placed ${singularLabel}: ${itemTitle}...`,
                                `✓ Placed ${singularLabel.toLowerCase()} "${itemTitle}" into template`
                            );

                            // 4. If current form step is on this section, re-render form step
                            if (typeof StepperComponent !== 'undefined') {
                                const cur = StepperComponent.getCurrentStep();
                                if (cur && cur.id === section) {
                                    StepperComponent.renderFormStep();
                                }
                            }
                        }
                    } else if (progress.event === 'section_update') {
                        const section = progress.section;
                        const data = progress.data;

                        // Skills are streamed one-by-one live; avoid bulk overwrite during stream
                        if (section === 'skills') {
                            ResumeStore.set('skills', data);
                            return;
                        }

                        if (!placedSet.has(section)) {
                            placedSet.add(section);

                            // 1. Immediately store array section into central state
                            ResumeStore.set(section, data);

                            // 2. Direct real-time visual injection into RHS preview DOM (instantaneous!)
                            if (typeof PreviewManager !== 'undefined' && PreviewManager.updateSectionDirectly) {
                                PreviewManager.updateSectionDirectly(section, data);
                            }

                            // 3. If current step is on this section, re-render form step
                            if (typeof StepperComponent !== 'undefined') {
                                const cur = StepperComponent.getCurrentStep();
                                if (cur && cur.id === section) {
                                    StepperComponent.renderFormStep();
                                }
                            }

                            // 4. Update banner ticker and status
                            const secLabel = section.replace('_', ' ').toUpperCase();
                            addPlacedFieldChip(secLabel, data.length);
                            updateExtractionBanner(
                                progress.pct,
                                `⚡ Placed ${data.length} ${secLabel} entries...`,
                                `✓ Section "${section}" placed into template spot`
                            );
                        }
                    } else if (progress.event === 'complete') {
                        updateExtractionBanner(100, '✓ All Fields Placed into Template!', 'Validation complete. Applying full resume...');
                    }
                });

                if (parsedData && typeof parsedData === 'object') {
                    // Update full validated resume dataset
                    ResumeStore.set(parsedData);
                    ResumeStore.save();

                    // Pixel-perfect refresh of preview from Jinja2 engine
                    if (typeof PreviewManager !== 'undefined' && PreviewManager.refresh) {
                        PreviewManager.refresh();
                    }

                    // Re-render personal step (step 0) so all inputs and fields reflect validated data
                    if (typeof StepperComponent !== 'undefined') {
                        StepperComponent.goToStep(0, true);
                    }

                    // Complete visual banner state
                    if (liveBanner) {
                        liveBanner.classList.add('completed');
                        updateExtractionBanner(100, '✓ Resume Placed into Template Successfully!', 'All fields and sections are loaded and active in the template.');
                        if (bannerCloseBtn) bannerCloseBtn.style.display = 'inline-block';

                        // Auto-hide banner after 6 seconds
                        setTimeout(() => {
                            if (liveBanner && liveBanner.classList.contains('completed')) {
                                liveBanner.style.opacity = '0';
                                setTimeout(() => {
                                    if (liveBanner.classList.contains('completed')) {
                                        liveBanner.style.display = 'none';
                                        liveBanner.style.opacity = '1';
                                    }
                                }, 350);
                            }
                        }, 6000);
                    }

                    if (typeof showToast === 'function') {
                        showToast('Resume imported! Fields placed into template.', 'success');
                    }
                } else {
                    throw new Error('No valid data received from neural parser.');
                }
            } catch (err) {
                console.error('Import error:', err);
                if (liveBanner) {
                    liveBanner.classList.remove('completed');
                    updateExtractionBanner(0, '⚠️ Extraction Notice', err.message || 'Could not complete resume extraction.');
                    if (bannerCloseBtn) bannerCloseBtn.style.display = 'inline-block';
                }
                if (typeof showToast === 'function') {
                    showToast(`Resume import error: ${err.message || 'Unknown error'}`, 'error');
                }
            } finally {
                btnAiImport.disabled = false;
                btnAiImport.innerHTML = originalHtml;
                aiImportInput.value = '';
            }
        });
    }

    // --- Header Download Button ---
    document.getElementById('btn-download-pdf')?.addEventListener('click', async () => {
        const btn = document.getElementById('btn-download-pdf');
        btn.disabled = true;
        btn.innerHTML = '⏳ Generating...';
        try {
            const data = ResumeStore.getResumeData();
            const blob = await API.downloadPDF(data);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${data.first_name || 'resume'}_resume.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('PDF downloaded!', 'success');
        } catch (e) {
            showToast('PDF generation failed. ' + (e.message || ''), 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Download PDF';
        }
    });

    // --- Preview Toggle (Mobile) ---
    document.getElementById('btn-toggle-preview')?.addEventListener('click', () => {
        const panel = document.getElementById('preview-panel');
        panel.classList.toggle('mobile-visible');
    });

    // --- Resizable Divider ---
    const divider = document.getElementById('builder-divider');
    const formPanel = document.getElementById('form-panel');
    if (divider && formPanel) {
        let isResizing = false;
        divider.addEventListener('mousedown', (e) => {
            isResizing = true;
            divider.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const containerWidth = document.getElementById('builder-main').offsetWidth;
            const newWidth = Math.max(360, Math.min(e.clientX, containerWidth - 300));
            formPanel.style.width = `${newWidth}px`;
        });
        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                divider.classList.remove('active');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    }

    console.log('🚀 Resume Builder initialized');
});
