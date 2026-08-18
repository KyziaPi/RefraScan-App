document.addEventListener('DOMContentLoaded', () => {
    // Form input autocomplete off for all input fields
    document.querySelectorAll('input').forEach(input => {
        input.setAttribute('autocomplete', 'off');
    });
    
    // Popup functionality
    document.querySelectorAll("[data-popup]").forEach(button => {
        button.addEventListener("click", () => {
            const popupId = button.dataset.popup;
            const popup = document.getElementById(popupId);

            if (popup) {
                // Check if opening the dynamic delete confirmation modal
                if (popupId === "delete-confirmation-popup") {
                    const itemType = button.dataset.itemType || "Record";
                    const itemName = button.dataset.itemName;
                    const itemId = button.dataset.itemId || "";
                    const deleteUrl = button.dataset.deleteUrl || "/delete-patient";
                    const redirectUrl = button.dataset.redirectUrl || "/patient-records";

                    // 1. Update confirmation message text
                    const confirmMsgEl = popup.querySelector("#delete-confirmation-message");
                    if (confirmMsgEl) {
                        confirmMsgEl.innerHTML = itemName
                            ? `Do you really want to delete <strong>${itemName}</strong>?`
                            : `Do you really want to delete this <strong>${itemType}</strong>?`;
                    }

                    // 2. Update form action URL and hidden input value
                    const deleteForm = popup.querySelector("#delete-popup-form");
                    if (deleteForm) deleteForm.action = deleteUrl;

                    const itemIdInput = popup.querySelector("#delete-item-id");
                    if (itemIdInput) itemIdInput.value = itemId;

                    // 3. Pre-configure success modal message and redirect path
                    const successPopup = document.getElementById("record-deleted-popup");
                    if (successPopup) {
                        const deletedMsgEl = successPopup.querySelector("#record-deleted-message");
                        if (deletedMsgEl) {
                            deletedMsgEl.textContent = `${itemType} has been deleted.`;
                        }
                        successPopup.action = redirectUrl;
                    }
                }
                
                popup.classList.add("active");
            }
        });
    });

    document.querySelectorAll(".popup-close, .popup-cancel, .popup-close-action")
        .forEach(button => {
            button.addEventListener("click", () => {
                button.closest(".popup-overlay")?.classList.remove("active");
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