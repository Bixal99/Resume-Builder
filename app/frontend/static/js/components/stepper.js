// =============================================================================
// Step Wizard Component
// =============================================================================

const StepperComponent = (() => {
    function getSteps() {
        const order = ResumeStore.get('section_order') || [];
        const getOrderIndex = (stepId) => {
            if (stepId === 'additional') {
                const subSections = ['certifications', 'languages', 'awards', 'volunteer', 'references'];
                const indices = subSections.map(s => order.indexOf(s)).filter(idx => idx !== -1);
                return indices.length ? Math.min(...indices) : 99;
            }
            const idx = order.indexOf(stepId);
            return idx !== -1 ? idx : 99;
        };

        const contentSteps = [
            { id: 'summary', label: 'Summary', icon: '📝' },
            { id: 'experience', label: 'Experience', icon: '💼' },
            { id: 'education', label: 'Education', icon: '🎓' },
            { id: 'projects', label: 'Projects', icon: '🚀' },
            { id: 'skills', label: 'Skills', icon: '⚡' },
            { id: 'additional', label: 'More', icon: '➕' },
        ];

        contentSteps.sort((a, b) => getOrderIndex(a.id) - getOrderIndex(b.id));

        return [
            { id: 'personal', label: 'Personal', icon: '👤' },
            ...contentSteps,
            { id: 'reorder', label: 'Arrange', icon: '↕️' },
            { id: 'template', label: 'Template', icon: '🎨' },
            { id: 'review', label: 'Review', icon: '✅' },
            { id: 'download', label: 'Download', icon: '📥' },
        ];
    }

    let currentStepId = 'personal';

    function render(container) {
        if (!container) return;
        container.innerHTML = '';
        const steps = getSteps();
        const currentIndex = steps.findIndex(s => s.id === currentStepId);
        
        const completedSteps = ResumeStore.get('completed_steps') || [];
        
        const stepper = document.createElement('div');
        stepper.className = 'stepper';
        steps.forEach((step, i) => {
            // A step is only visually completed if it's explicitly in completed_steps array
            // The user explicitly clicks Save & Next to get it there.
            const isCompleted = completedSteps.includes(step.id);
            
            // Current active step shouldn't be marked with a checkmark visually if we want it to look active
            const isCompletedStyle = isCompleted && i !== currentIndex;
            
            if (i > 0) {
                const conn = document.createElement('div');
                const isConnActive = completedSteps.includes(steps[i-1].id) || i <= currentIndex;
                conn.className = `stepper-connector${isConnActive ? ' active' : ''}`;
                stepper.appendChild(conn);
            }
            const el = document.createElement('div');
            el.className = `stepper-step${i === currentIndex ? ' active' : ''}${isCompletedStyle ? ' completed' : ''}`;
            el.innerHTML = `<span class="stepper-number">${isCompletedStyle ? '✓' : i + 1}</span><span class="stepper-label">${step.label}</span>`;
            el.addEventListener('click', () => goToStep(i));
            stepper.appendChild(el);
        });
        container.appendChild(stepper);
    }

    function goToStep(index) {
        const steps = getSteps();
        if (index < 0 || index >= steps.length) return;
        
        ResumeStore.save();

        currentStepId = steps[index].id;
        render(document.getElementById('stepper-nav'));
        renderFormStep();
        updateNavButtons();
    }

    function next() {
        const steps = getSteps();
        
        // Mark current step as completed explicitly
        let completed = ResumeStore.get('completed_steps') || [];
        if (!completed.includes(currentStepId)) {
            completed.push(currentStepId);
            ResumeStore.set('completed_steps', completed);
        }
        
        const currentIndex = steps.findIndex(s => s.id === currentStepId);
        goToStep(currentIndex + 1);
    }
    
    function prev() {
        const steps = getSteps();
        const currentIndex = steps.findIndex(s => s.id === currentStepId);
        goToStep(currentIndex - 1);
    }
    
    function getCurrentStep() {
        const steps = getSteps();
        return steps.find(s => s.id === currentStepId) || steps[0];
    }
    
    function getCurrentIndex() {
        return getSteps().findIndex(s => s.id === currentStepId);
    }
    
    function getTotalSteps() {
        return getSteps().length;
    }

    function updateNavButtons() {
        const steps = getSteps();
        const currentIndex = steps.findIndex(s => s.id === currentStepId);
        const prevBtn = document.getElementById('btn-prev-step');
        const nextBtn = document.getElementById('btn-next-step');
        
        if (prevBtn) prevBtn.disabled = currentIndex === 0;
        if (nextBtn) {
            if (currentIndex === steps.length - 1) {
                nextBtn.style.display = 'none';
            } else {
                nextBtn.style.display = '';
                nextBtn.innerHTML = 'Save & Next <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>';
            }
        }
    }

    function renderFormStep() {
        const container = document.getElementById('form-content');
        if (!container) return;
        container.innerHTML = '';
        container.scrollTop = 0;
        switch (currentStepId) {
            case 'personal': PersonalInfoComponent.render(container); break;
            case 'summary': SummaryComponent.render(container); break;
            case 'experience': ExperienceComponent.render(container); break;
            case 'education': EducationComponent.render(container); break;
            case 'projects': ProjectsComponent.render(container); break;
            case 'skills': SkillsComponent.render(container); break;
            case 'additional': AdditionalComponent.render(container); break;
            case 'reorder': ArrangeComponent.render(container); break;
            case 'template': TemplateSelectorComponent.render(container); break;
            case 'review': ReviewComponent.render(container); break;
            case 'download': DownloadComponent.render(container); break;
        }
    }

    return {
        render,
        goToStep,
        next,
        prev,
        getCurrentStep,
        getCurrentIndex,
        getTotalSteps,
        updateNavButtons,
        get STEPS() { return getSteps(); }
    };
})();
