// ===== File input: enable/disable submit button =====
document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.querySelector('input[type="file"]');
    const uploadBtn = document.querySelector('#upload-btn');

    // ===== Secret: Vitruvian Man head click =====
    (function () {
        const logo = document.querySelector('.logo-container img');
        if (!logo) return;
        let headClicks = 0;
        logo.addEventListener('click', function (e) {
            const rect = logo.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width;
            const y = (e.clientY - rect.top) / rect.height;
            // Head area: top 35% of image, horizontally 30%-70%
            if (y < 0.35 && x > 0.30 && x < 0.70) {
                headClicks++;
                fetch('/logo_click', { method: 'POST' }).then(function () {
                    if (headClicks >= 5) {
                        window.location.href = '/credits';
                    }
                });
            }
        });
    })();

    if (fileInput && uploadBtn) {
        fileInput.addEventListener('change', function () {
            uploadBtn.disabled = !this.value;
        });
    }

    // ===== Calls page: collect checked IDs on submit =====
    const dynamicForm = document.getElementById('dynamicForm');
    const idsInput = document.getElementById('selected-ids');
    const submitBtn = document.getElementById('submit-btn');

    if (dynamicForm && idsInput) {
        const rowCheckboxes = document.querySelectorAll('tbody input[name="selected_ids"]');

        function updateSubmitState() {
            if (submitBtn) {
                const anyChecked = Array.from(rowCheckboxes).some(cb => cb.checked);
                submitBtn.disabled = !anyChecked;
            }
        }

        // Listen for any checkbox change
        rowCheckboxes.forEach(cb => {
            cb.addEventListener('change', updateSubmitState);
        });

        // On form submit, populate the hidden ids field
        dynamicForm.addEventListener('submit', function (e) {
            const checked = Array.from(rowCheckboxes).filter(cb => cb.checked);
            if (checked.length === 0) {
                e.preventDefault();
                return;
            }
            if (!confirm('Mark ' + checked.length + ' call(s) as returned?')) {
                e.preventDefault();
                return;
            }
            idsInput.value = checked.map(cb => cb.value).join(',');
        });

        // Initial state
        updateSubmitState();
    }
});