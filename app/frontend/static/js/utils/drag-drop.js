// =============================================================================
// Drag & Drop Reordering
// =============================================================================

function initDragDrop(container, onReorder) {
    let dragEl = null;
    const cards = () => Array.from(container.querySelectorAll('.entry-card'));

    container.addEventListener('dragstart', e => {
        const card = e.target.closest('.entry-card');
        if (!card) return;
        dragEl = card;
        card.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', '');
    });

    container.addEventListener('dragover', e => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        const afterEl = getDragAfterElement(container, e.clientY);
        if (afterEl) container.insertBefore(dragEl, afterEl);
        else container.appendChild(dragEl);
    });

    container.addEventListener('dragend', e => {
        if (dragEl) { dragEl.classList.remove('dragging'); dragEl = null; }
        const order = cards().map(c => c.dataset.id);
        if (onReorder) onReorder(order);
    });
}

function getDragAfterElement(container, y) {
    const els = Array.from(container.querySelectorAll('.entry-card:not(.dragging)'));
    return els.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) return { offset, element: child };
        return closest;
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}
