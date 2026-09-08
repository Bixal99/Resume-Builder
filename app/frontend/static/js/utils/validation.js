// =============================================================================
// Client-Side Validation
// =============================================================================

const Validators = {
    email(v) { return !v || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v); },
    phone(v) { return !v || /^\+?[\d\s\-().]{7,20}$/.test(v); },
    url(v) { return !v || /^https?:\/\/.+/i.test(v) || /^[\w.-]+\.[a-z]{2,}/i.test(v); },
    required(v) { return v !== null && v !== undefined && String(v).trim() !== ''; },
    maxLength(v, max) { return !v || v.length <= max; },
    minLength(v, min) { return !v || v.length >= min; },
};

function validateField(el) {
    const val = el.value;
    const rules = el.dataset.validate ? el.dataset.validate.split(',') : [];
    let error = '';
    for (const rule of rules) {
        const [name, param] = rule.split(':');
        if (name === 'required' && !Validators.required(val)) error = 'This field is required';
        else if (name === 'email' && !Validators.email(val)) error = 'Invalid email address';
        else if (name === 'phone' && !Validators.phone(val)) error = 'Invalid phone number';
        else if (name === 'url' && !Validators.url(val)) error = 'Invalid URL';
        else if (name === 'maxLength' && !Validators.maxLength(val, parseInt(param))) error = `Max ${param} characters`;
        if (error) break;
    }
    const errEl = el.parentElement?.querySelector('.form-error');
    if (error) { el.classList.add('error'); if (errEl) errEl.textContent = error; }
    else { el.classList.remove('error'); if (errEl) errEl.textContent = ''; }
    return !error;
}

function validateForm(container) {
    const fields = container.querySelectorAll('[data-validate]');
    let valid = true;
    fields.forEach(f => { if (!validateField(f)) valid = false; });
    return valid;
}
