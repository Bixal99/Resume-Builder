// =============================================================================
// API Client
// =============================================================================

const API = (() => {
    const BASE = '/api';

    async function request(path, options = {}) {
        const url = `${BASE}${path}`;
        const config = {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        };
        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }
        const res = await fetch(url, config);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || 'Request failed');
        }
        const ct = res.headers.get('content-type') || '';
        if (ct.includes('application/json')) return res.json();
        if (ct.includes('text/html')) return res.text();
        return res;
    }

    return {
        // Resume CRUD
        createResume: (data) => request('/resumes', { method: 'POST', body: data }),
        getResume: (id) => request(`/resumes/${id}`),
        getResumeBySession: (sid) => request(`/resumes/session/${sid}`),
        updateResume: (id, data) => request(`/resumes/${id}`, { method: 'PUT', body: data }),
        deleteResume: (id) => request(`/resumes/${id}`, { method: 'DELETE' }),

        // Preview
        getPreview: (data) => request('/preview', { method: 'POST', body: data }),

        // PDF
        downloadPDF: async (data) => {
            const res = await fetch(`${BASE}/download/pdf`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || 'PDF generation failed');
            }
            return res.blob();
        },

        // Parse Resume from PDF (Standard)
        parseResume: async (file) => {
            const formData = new FormData();
            formData.append('file', file);
            const res = await fetch(`${BASE}/parse`, {
                method: 'POST',
                body: formData,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || 'Resume parsing failed');
            }
            return res.json();
        },

        // Parse Resume with Real-Time SSE Stream Progress
        parseResumeStream: async (file, onProgress) => {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch(`${BASE}/parse-stream`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(err.detail || 'Resume parsing stream failed');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';
            let parsedResult = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    const trimmed = line.trim();
                    if (trimmed.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(trimmed.substring(6));
                            if (typeof onProgress === 'function') {
                                onProgress(data);
                            }
                            if (data.event === 'complete' && data.data) {
                                parsedResult = data.data;
                            } else if (data.event === 'error') {
                                throw new Error(data.detail || 'AI parsing error');
                            }
                        } catch (parseErr) {
                            throw parseErr;
                        }
                    }
                }
            }

            if (!parsedResult) {
                return API.parseResume(file);
            }
            return parsedResult;
        },

        // AI STAR Bullet Point Optimizer
        optimizeBullet: (params) => request('/ai/optimize-bullet', {
            method: 'POST',
            body: params
        }),
        
        getPageCount: (data) => request('/page-count', { method: 'POST', body: data }),

        // Templates
        getTemplates: () => request('/templates'),
        getTemplate: (id) => request(`/templates/${id}`),

        // Health
        health: () => request('/health'),
    };
})();
