// =============================================================================
// Download Component
// =============================================================================

const DownloadComponent = (() => {
    function render(container) {
        const pageSize = ResumeStore.get('page_size') || 'A4';
        container.innerHTML = `
            <div class="download-section">
                <div class="download-icon">📥</div>
                <h2 class="form-section-title" style="text-align:center;">Download Your Resume</h2>
                <p class="form-section-subtitle" style="text-align:center;">Choose your page size and download as PDF.</p>

                <div class="download-options">
                    <div class="page-size-option ${pageSize === 'A4' ? 'selected' : ''}" data-size="A4">
                        <span class="page-size-label">A4</span>
                        <span class="page-size-desc">210 × 297 mm<br>International</span>
                    </div>
                    <div class="page-size-option ${pageSize === 'Letter' ? 'selected' : ''}" data-size="Letter">
                        <span class="page-size-label">Letter</span>
                        <span class="page-size-desc">8.5 × 11 in<br>US / Canada</span>
                    </div>
                </div>

                <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-top: var(--space-4);">
                    <button class="btn btn-primary btn-lg" id="download-btn">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        Download PDF
                    </button>
                    <button class="btn btn-secondary btn-lg" id="download-json-btn" title="Download Standard JSON Schema Backup">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        Download JSON (Backup)
                    </button>
                </div>
                <p id="download-status" style="margin-top: var(--space-4); font-size: var(--text-sm); color: var(--text-secondary);"></p>
            </div>
        `;

        // Page size selection
        container.querySelectorAll('.page-size-option').forEach(opt => {
            opt.addEventListener('click', () => {
                container.querySelectorAll('.page-size-option').forEach(o => o.classList.remove('selected'));
                opt.classList.add('selected');
                ResumeStore.set('page_size', opt.dataset.size);
            });
        });

        // Download JSON Backup
        container.querySelector('#download-json-btn')?.addEventListener('click', () => {
            try {
                if (typeof JsonResumeConverter !== 'undefined') {
                    JsonResumeConverter.exportFile();
                    showToast('JSON Resume downloaded successfully!', 'success');
                } else {
                    throw new Error('JsonResumeConverter not loaded.');
                }
            } catch (err) {
                console.error('JSON export error:', err);
                showToast('Failed to export JSON: ' + err.message, 'error');
            }
        });

        // Download PDF
        container.querySelector('#download-btn').addEventListener('click', async () => {
            const btn = container.querySelector('#download-btn');
            const status = container.querySelector('#download-status');
            btn.disabled = true;
            btn.innerHTML = '<span class="animate-spin" style="display:inline-block">⏳</span> Generating PDF...';
            status.textContent = '';

            try {
                const data = ResumeStore.getResumeData();
                const blob = await API.downloadPDF(data);
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                const name = `${data.first_name || 'resume'}_${data.last_name || ''}_resume.pdf`.replace(/\s+/g, '_');
                a.href = url;
                a.download = name;
                a.click();
                URL.revokeObjectURL(url);
                status.innerHTML = '<span style="color: var(--color-success);">✅ PDF downloaded successfully!</span>';
                showToast('PDF downloaded!', 'success');
            } catch (e) {
                console.error('PDF download failed:', e);
                status.innerHTML = `<span style="color: var(--color-danger);">❌ ${e.message || 'PDF generation failed. Make sure the server is running.'}</span>`;
                showToast('PDF download failed', 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Download PDF';
            }
        });
    }

    return { render };
})();
