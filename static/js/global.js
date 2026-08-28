document.addEventListener('DOMContentLoaded', () => {
    const deleteForm = document.getElementById("delete-popup-form");
    const hiddenIdInput = document.getElementById("delete-item-id");
    
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

    // --- CENTRALIZED DELETE SUBMISSION ---
    deleteForm?.addEventListener("submit", async (e) => {
        e.preventDefault();

        const itemId = hiddenIdInput?.value;
        const deleteUrl = deleteForm.action;
        const deletePopup = document.getElementById("delete-confirmation-popup");
        const successPopup = document.getElementById("record-deleted-popup");

        try {
            const response = await fetch(deleteUrl, { method: "DELETE" });
            const result = await response.json();

            if (response.ok) {
                // 1. IF ON DETAILED PAGE: Redirect back to records list or reload page
                if (window.location.pathname.includes('patient-record-detailed')) {
                    // If deleting a specific follow-up sheet item, reload page. Otherwise redirect.
                    if (deleteUrl.includes('delete-follow-up')) {
                        window.location.reload();
                    } else {
                        window.location.href = '/patient-records';
                    }
                    return;
                }

                // 2. IF ON MAIN TABLE PAGE: Remove row directly from DOM
                const deleteBtn = document.querySelector(`button[data-item-id="${itemId}"]`);
                if (deleteBtn) {
                    const targetRow = deleteBtn.closest('.table-row');
                    if (targetRow) {
                        targetRow.remove();
                    }
                }

                // Call updatePagination if it exists globally (defined in patient-records.js)
                if (typeof updatePagination === 'function') {
                    updatePagination();
                }

                // Toggle Modals
                deletePopup?.classList.remove("active");
                successPopup?.classList.add("active");
            } else {
                alert(result.error || result.message || "Failed to delete record.");
            }
        } catch (error) {
            console.error("Error deleting record:", error);
            alert("An error occurred while communicating with the server.");
        }
    });

    // Export CSV Handling
    const exportPopup = document.getElementById('export-csv-popup');
    if (!exportPopup) return;

    document.getElementById('select-all-fields')?.addEventListener('click', () => {
        exportPopup.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = true);
    });

    document.getElementById('deselect-all-fields')?.addEventListener('click', () => {
        exportPopup.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    });

    exportPopup.querySelectorAll('.section-toggle').forEach(toggle => {
        toggle.addEventListener('change', (e) => {
            const group = e.target.closest('.export-group');
            const checkboxes = group.querySelectorAll('.export-checkbox-grid input[type="checkbox"]');
            checkboxes.forEach(cb => cb.checked = e.target.checked);
        });
    });
});