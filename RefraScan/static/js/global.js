document.addEventListener('DOMContentLoaded', () => {
    const deleteForm = document.getElementById("delete-popup-form");
    const hiddenIdInput = document.getElementById("delete-item-id");

    const importForm = document.querySelector("#import-csv-popup form");
    const conflictPopup = document.getElementById("import-conflict-popup");
    const importPopup = document.getElementById("import-csv-popup");
    
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

    // ==========================================
    // EXCEL IMPORT & CONFLICT RESOLUTION LOGIC
    // ==========================================
    if (importForm && conflictPopup) {
            let conflictsList = [];
            let currentConflictIndex = 0;
            let tempFilename = "";
            let resolutionsMap = {};

            // Helper to send cleanup signal to backend
            const cleanupTempFile = () => {
                if (tempFilename) {
                    navigator.sendBeacon(
                        "/api/cancel-import",
                        JSON.stringify({ temp_file: tempFilename })
                    );
                    tempFilename = "";
                }
            };

            // Listen for modal close triggers (&times; buttons, Cancel buttons, background overlays)
            document.querySelectorAll(
                "#import-csv-popup .popup-close, #import-csv-popup .popup-cancel, " +
                "#import-conflict-popup .popup-close, #import-conflict-popup .popup-cancel"
            ).forEach(btn => {
                btn.addEventListener("click", () => {
                    cleanupTempFile();
                });
            });

            // Cleanup if user reloads or navigates away while modal is active
            window.addEventListener("beforeunload", () => {
                cleanupTempFile();
            });

            // 1. Intercept file upload
            importForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const formData = new FormData(importForm);
                const submitBtn = importForm.querySelector('button[type="submit"]');
                
                submitBtn.textContent = "Validating File...";
                submitBtn.disabled = true;

                try {
                    const res = await fetch("/api/validate-import", { method: "POST", body: formData });
                    const data = await res.json();

                    if (data.error) {
                        alert(data.error);
                        submitBtn.textContent = "Import Data";
                        submitBtn.disabled = false;
                        return;
                    }

                    tempFilename = data.temp_file;

                    if (data.has_conflicts && data.conflicts.length > 0) {
                        conflictsList = data.conflicts;
                        currentConflictIndex = 0;
                        resolutionsMap = {};
                        
                        importPopup.classList.remove("active");
                        showConflictData(0);
                        conflictPopup.classList.add("active");
                    } else {
                        executeFinalImport(tempFilename, {}, null);
                    }
                } catch (err) {
                    console.error("Validation Error:", err);
                    alert("A validation error occurred: " + err.message);
                    cleanupTempFile();
                } finally {
                    submitBtn.textContent = "Import Data";
                    submitBtn.disabled = false;
                }
            });

            // 2. Render current conflict into the UI
            function showConflictData(index) {
                const conflict = conflictsList[index];
                if (!conflict) return;

                const codeEl = document.getElementById("conflict-patient-code");
                if (codeEl) codeEl.textContent = conflict.patient_code || '';
                
                const dbName = document.getElementById("db-name");
                const dbPhone = document.getElementById("db-phone");
                const dbAge = document.getElementById("db-age");
                const dbDate = document.getElementById("db-date");

                if (dbName) dbName.textContent = conflict.db_data.name || '—';
                if (dbPhone) dbPhone.textContent = conflict.db_data.phone || '—';
                if (dbAge) dbAge.textContent = conflict.db_data.age || '—';
                if (dbDate) dbDate.textContent = conflict.db_data.date || '—';

                const exName = document.getElementById("ex-name");
                const exPhone = document.getElementById("ex-phone");
                const exAge = document.getElementById("ex-age");
                const exDate = document.getElementById("ex-date");

                if (exName) exName.textContent = conflict.excel_data.name || '—';
                if (exPhone) exPhone.textContent = conflict.excel_data.phone || '—';
                if (exAge) exAge.textContent = conflict.excel_data.age || '—';
                if (exDate) exDate.textContent = conflict.excel_data.date || '—';
            }

            // 3. Handle Individual Decisions
            function resolveCurrent(actionType) {
                const code = conflictsList[currentConflictIndex].patient_code;
                resolutionsMap[code] = actionType;
                currentConflictIndex++;
                
                if (currentConflictIndex >= conflictsList.length) {
                    executeFinalImport(tempFilename, resolutionsMap, null);
                } else {
                    showConflictData(currentConflictIndex);
                }
            }

            document.getElementById("btn-keep-current")?.addEventListener("click", () => resolveCurrent('keep'));
            document.getElementById("btn-update")?.addEventListener("click", () => resolveCurrent('update'));
            
            // 4. Handle Global Decisions
            document.getElementById("btn-keep-all")?.addEventListener("click", () => executeFinalImport(tempFilename, {}, 'keep_all'));
            document.getElementById("btn-update-all")?.addEventListener("click", () => executeFinalImport(tempFilename, {}, 'update_all'));

            // 5. Execute Final Command
            async function executeFinalImport(filename, resolutions, globalAction) {
                conflictPopup.classList.remove("active");
                importPopup.classList.remove("active");
                
                const activeTempFile = tempFilename;
                tempFilename = ""; // Reset variable so double cleanup isn't fired

                try {
                    const response = await fetch("/api/execute-import", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            temp_file: activeTempFile,
                            resolutions: resolutions,
                            global_action: globalAction
                        })
                    });
                    
                    if (response.redirected) {
                        window.location.href = response.url;
                    } else {
                        const result = await response.json();
                        alert(result.error || "Failed to finalize import.");
                    }
                } catch (err) {
                    console.error("Execution Error:", err);
                    alert("Execution failed to complete.");
                }
            }
        }
});