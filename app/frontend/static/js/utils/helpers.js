// =============================================================================
// Utility Helpers
// =============================================================================

function debounce(fn, ms = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}

function throttle(fn, ms = 100) {
    let last = 0;
    return (...args) => {
        const now = Date.now();
        if (now - last >= ms) { last = now; fn(...args); }
    };
}

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    return dateStr;
}

function sanitizeHTML(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function escapeAttr(str) {
    if (!str) return '';
    return str.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function showToast(message, type = 'success', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${sanitizeHTML(message)}</span>`;
    container.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateX(20px)'; setTimeout(() => toast.remove(), 300); }, duration);
}

function getSessionId() {
    let sid = localStorage.getItem('rb_session_id');
    if (!sid) { sid = generateUUID(); localStorage.setItem('rb_session_id', sid); }
    return sid;
}

// =============================================================================
// Modern In-UI Dialogs (Replaces browser-native confirm() and prompt())
// =============================================================================

function _getOrCreateDialogContainer() {
    let overlay = document.getElementById('ui-dialog-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'ui-dialog-overlay';
        overlay.className = 'ui-dialog-overlay';
        overlay.innerHTML = `
            <div class="ui-dialog-card" id="ui-dialog-card">
                <div class="ui-dialog-header">
                    <div class="ui-dialog-icon-badge" id="ui-dialog-icon-badge">
                        <span id="ui-dialog-icon">⚠️</span>
                    </div>
                    <div class="ui-dialog-header-text">
                        <h3 class="ui-dialog-title" id="ui-dialog-title">Confirmation</h3>
                        <p class="ui-dialog-message" id="ui-dialog-message"></p>
                    </div>
                </div>
                <div class="ui-dialog-body" id="ui-dialog-body" style="display: none;">
                    <input type="text" class="ui-dialog-input" id="ui-dialog-input" autocomplete="off" spellcheck="false" />
                </div>
                <div class="ui-dialog-actions">
                    <button type="button" class="btn btn-secondary ui-dialog-btn-cancel" id="ui-dialog-btn-cancel">Cancel</button>
                    <button type="button" class="btn btn-primary ui-dialog-btn-confirm" id="ui-dialog-btn-confirm">Confirm</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
    }
    return overlay;
}

function showConfirmDialog({
    title = 'Confirm Action',
    message = 'Are you sure you want to proceed?',
    icon = '⚠️',
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    isDanger = false
} = {}) {
    return new Promise((resolve) => {
        const overlay = _getOrCreateDialogContainer();
        const card = overlay.querySelector('#ui-dialog-card');
        const iconEl = overlay.querySelector('#ui-dialog-icon');
        const iconBadge = overlay.querySelector('#ui-dialog-icon-badge');
        const titleEl = overlay.querySelector('#ui-dialog-title');
        const messageEl = overlay.querySelector('#ui-dialog-message');
        const bodyEl = overlay.querySelector('#ui-dialog-body');
        const btnCancel = overlay.querySelector('#ui-dialog-btn-cancel');
        const btnConfirm = overlay.querySelector('#ui-dialog-btn-confirm');

        iconEl.textContent = icon;
        titleEl.textContent = title;
        messageEl.textContent = message;
        bodyEl.style.display = 'none';

        btnCancel.textContent = cancelText;
        btnConfirm.textContent = confirmText;

        if (isDanger) {
            btnConfirm.className = 'btn btn-danger ui-dialog-btn-confirm';
            iconBadge.className = 'ui-dialog-icon-badge danger';
        } else {
            btnConfirm.className = 'btn btn-primary ui-dialog-btn-confirm';
            iconBadge.className = 'ui-dialog-icon-badge';
        }

        const cleanup = () => {
            overlay.classList.remove('active');
            window.removeEventListener('keydown', handleKeydown);
            btnCancel.onclick = null;
            btnConfirm.onclick = null;
            overlay.onclick = null;
        };

        const handleKeydown = (e) => {
            if (e.key === 'Escape') {
                cleanup();
                resolve(false);
            } else if (e.key === 'Enter') {
                cleanup();
                resolve(true);
            }
        };

        btnCancel.onclick = (e) => {
            e.stopPropagation();
            cleanup();
            resolve(false);
        };

        btnConfirm.onclick = (e) => {
            e.stopPropagation();
            cleanup();
            resolve(true);
        };

        overlay.onclick = (e) => {
            if (e.target === overlay) {
                cleanup();
                resolve(false);
            }
        };

        window.addEventListener('keydown', handleKeydown);
        overlay.classList.add('active');
        btnConfirm.focus();
    });
}

function showPromptDialog({
    title = 'Input Required',
    message = 'Please enter a value:',
    icon = '✍️',
    defaultValue = '',
    placeholder = '',
    confirmText = 'Submit',
    cancelText = 'Cancel'
} = {}) {
    return new Promise((resolve) => {
        const overlay = _getOrCreateDialogContainer();
        const card = overlay.querySelector('#ui-dialog-card');
        const iconEl = overlay.querySelector('#ui-dialog-icon');
        const iconBadge = overlay.querySelector('#ui-dialog-icon-badge');
        const titleEl = overlay.querySelector('#ui-dialog-title');
        const messageEl = overlay.querySelector('#ui-dialog-message');
        const bodyEl = overlay.querySelector('#ui-dialog-body');
        const inputEl = overlay.querySelector('#ui-dialog-input');
        const btnCancel = overlay.querySelector('#ui-dialog-btn-cancel');
        const btnConfirm = overlay.querySelector('#ui-dialog-btn-confirm');

        iconEl.textContent = icon;
        titleEl.textContent = title;
        messageEl.textContent = message;
        bodyEl.style.display = 'block';

        inputEl.value = defaultValue;
        inputEl.placeholder = placeholder;

        btnCancel.textContent = cancelText;
        btnConfirm.textContent = confirmText;
        btnConfirm.className = 'btn btn-primary ui-dialog-btn-confirm';
        iconBadge.className = 'ui-dialog-icon-badge info';

        const cleanup = () => {
            overlay.classList.remove('active');
            window.removeEventListener('keydown', handleKeydown);
            btnCancel.onclick = null;
            btnConfirm.onclick = null;
            overlay.onclick = null;
        };

        const handleKeydown = (e) => {
            if (e.key === 'Escape') {
                cleanup();
                resolve(null);
            } else if (e.key === 'Enter') {
                cleanup();
                resolve(inputEl.value.trim());
            }
        };

        btnCancel.onclick = (e) => {
            e.stopPropagation();
            cleanup();
            resolve(null);
        };

        btnConfirm.onclick = (e) => {
            e.stopPropagation();
            const val = inputEl.value.trim();
            cleanup();
            resolve(val);
        };

        overlay.onclick = (e) => {
            if (e.target === overlay) {
                cleanup();
                resolve(null);
            }
        };

        window.addEventListener('keydown', handleKeydown);
        overlay.classList.add('active');
        setTimeout(() => {
            inputEl.focus();
            inputEl.select();
        }, 50);
    });
}
