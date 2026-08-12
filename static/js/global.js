document.addEventListener('DOMContentLoaded', () => {
    // Popup functionality
    document.querySelectorAll("[data-popup]").forEach(button => {
        button.addEventListener("click", () => {
            const popupId = button.dataset.popup;
            const popup = document.getElementById(popupId);

            if (popup) {
                popup.classList.add("active");
            }
        });
    });

    document.querySelectorAll(".popup-close, .popup-cancel, .popup-close-action")
        .forEach(button => {
            button.addEventListener("click", () => {
                button.closest(".popup-overlay").classList.remove("active");
            });
        });
    

    const exportPopup = document.getElementById('export-csv-popup');
    if (!exportPopup) return;

    // Global Select All / Deselect All
    document.getElementById('select-all-fields')?.addEventListener('click', () => {
        exportPopup.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = true);
    });

    document.getElementById('deselect-all-fields')?.addEventListener('click', () => {
        exportPopup.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    });

    // Section Header Toggle Checkboxes
    exportPopup.querySelectorAll('.section-toggle').forEach(toggle => {
        toggle.addEventListener('change', (e) => {
            const group = e.target.closest('.export-group');
            const checkboxes = group.querySelectorAll('.export-checkbox-grid input[type="checkbox"]');
            checkboxes.forEach(cb => cb.checked = e.target.checked);
        });
    });
    
});