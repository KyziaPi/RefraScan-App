document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('add-patient-form');
    const successPopup = document.getElementById('record-success-popup');
    const diagnosisList = document.getElementById("diagnosis-list");
    const hiddenIdInput = document.getElementById('id');
    const patientId = hiddenIdInput ? hiddenIdInput.value : null;

    let newlyCreatedPatientId = null;

    // Helper function to format date strings strictly to YYYY-MM-DD for <input type="date">
    function formatDateForInput(dateStr) {
        if (!dateStr) return '';
        const str = String(dateStr).trim();
        
        // Extract YYYY-MM-DD directly if present
        const match = str.match(/^(\d{4}-\d{2}-\d{2})/);
        if (match) return match[1];

        // Otherwise parse using Date object
        const d = new Date(str);
        if (!isNaN(d.getTime())) {
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
        return str;
    }

    // Helper function to enable/disable remove buttons based on row count
    function updateRemoveButtons() {
        if (!diagnosisList) return;
        const rows = diagnosisList.querySelectorAll(".dynamic-input-row");
        const removeBtns = diagnosisList.querySelectorAll(".dynamic-remove-btn");

        removeBtns.forEach((btn) => {
            btn.disabled = rows.length <= 1;
        });
    }

    // Event Delegation for Add (+) and Remove (-) diagnosis buttons
    if (diagnosisList) {
        diagnosisList.addEventListener("click", (e) => {
            const addBtn = e.target.closest(".dynamic-add-btn");
            const removeBtn = e.target.closest(".dynamic-remove-btn");

            if (addBtn) {
                const currentRow = addBtn.closest(".dynamic-input-row");
                const newRow = document.createElement("div");
                newRow.className = "dynamic-input-row";
                newRow.innerHTML = `
                    <input type="text" name="diagnosis[]" placeholder="Enter diagnosis...">
                    <button type="button" class="dynamic-remove-btn" aria-label="Remove diagnosis">−</button>
                    <button type="button" class="dynamic-add-btn" aria-label="Add diagnosis">+</button>
                `;

                currentRow.after(newRow);
                updateRemoveButtons();
                newRow.querySelector("input").focus();
            }

            if (removeBtn) {
                const rows = diagnosisList.querySelectorAll(".dynamic-input-row");
                if (rows.length > 1) {
                    const rowToRemove = removeBtn.closest(".dynamic-input-row");
                    rowToRemove.remove();
                    updateRemoveButtons();
                }
            }
        });
    }

    updateRemoveButtons();

    // =========================================================
    // 1. AUTO-FILL LOGIC FOR EDIT MODE
    // =========================================================
    if (patientId) {
        try {
            const response = await fetch(`/api/get-patient/${patientId}`);
            if (response.ok) {
                const data = await response.json();

                for (const [key, value] of Object.entries(data)) {
                    if (value === null || value === undefined) continue;

                    const valStr = String(value).trim().toLowerCase();

                    // 1. Radio Buttons (Handles case-insensitivity & OD/OS/Boolean mappings)
                    const radios = document.querySelectorAll(`input[type="radio"][name="${key}"]`);
                    if (radios.length > 0) {
                        radios.forEach(radio => {
                            const rVal = radio.value.trim().toLowerCase();
                            const isMatch = (rVal === valStr) ||
                                (valStr === 'os' && rVal === 'left') ||
                                (valStr === 'left' && rVal === 'os') ||
                                (valStr === 'od' && rVal === 'right') ||
                                (valStr === 'right' && rVal === 'od') ||
                                (valStr === 'true' && rVal === 'yes') ||
                                (valStr === 'false' && rVal === 'no');

                            if (isMatch) {
                                radio.checked = true;
                            }
                        });
                        continue;
                    }

                    // 2. Checkbox Arrays (e.g. family_history[], past_history[])
                    if (Array.isArray(value) && key !== 'diagnosis') {
                        value.forEach(val => {
                            const checkbox = document.querySelector(`input[type="checkbox"][name="${key}[]"][value="${val}"]`) 
                                          || document.querySelector(`input[type="checkbox"][name="${key}"][value="${val}"]`);
                            if (checkbox) checkbox.checked = true;
                        });
                        continue;
                    }

                    // 3. Dynamic Diagnoses Array
                    if (key === 'diagnosis' && Array.isArray(value) && value.length > 0) {
                        if (diagnosisList) {
                            diagnosisList.innerHTML = ''; // Clear initial default row
                            value.forEach(diag => {
                                const newRow = document.createElement("div");
                                newRow.className = "dynamic-input-row";
                                newRow.innerHTML = `
                                    <input type="text" name="diagnosis[]" placeholder="Enter diagnosis..." value="${diag}">
                                    <button type="button" class="dynamic-remove-btn" aria-label="Remove diagnosis">−</button>
                                    <button type="button" class="dynamic-add-btn" aria-label="Add diagnosis">+</button>
                                `;
                                diagnosisList.appendChild(newRow);
                            });
                            updateRemoveButtons();
                        }
                        continue;
                    }

                    // 4. Standard Text, Number, Date, and Select Inputs
                    let standardInput = document.querySelector(`[name="${key}"]`) 
                                     || document.querySelector(`[name="${key}[]"]`);

                    // Fallback for exam_date vs date field name differences
                    if (!standardInput && key === 'date') {
                        standardInput = document.querySelector(`[name="exam_date"]`);
                    } else if (!standardInput && key === 'exam_date') {
                        standardInput = document.querySelector(`[name="date"]`);
                    }

                    if (standardInput && standardInput.type !== 'radio' && standardInput.type !== 'checkbox') {
                        if (standardInput.type === 'date') {
                            standardInput.value = formatDateForInput(value);
                        } else {
                            standardInput.value = value;
                        }
                    }
                }
            } else {
                console.error("Failed to load patient record details for edit mode.");
            }
        } catch (err) {
            console.error("Error fetching patient data for edit:", err);
        }
    }

    // =========================================================
    // 2. FORM SUBMISSION HANDLER
    // =========================================================
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const data = {};

            for (const key of formData.keys()) {
                const values = formData.getAll(key);
                if (key.endsWith('[]') || values.length > 1) {
                    data[key] = values.filter(val => val.trim() !== '');
                } else {
                    data[key] = values[0];
                }
            }

            try {
                const response = await fetch('/api/add-patient', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    const result = await response.json();
                    newlyCreatedPatientId = result.patient_id;
                    
                    const msgEl = successPopup?.querySelector('#record-success-message');
                    if (msgEl) msgEl.textContent = 'Patient record has been saved successfully.';
                    
                    if (successPopup) {
                        successPopup.classList.add('active');
                    }
                } else {
                    const error = await response.json();
                    alert("Error saving patient: " + (error.error || "Unknown error"));
                }
            } catch (err) {
                console.error("Submission failed:", err);
                alert("Network error occurred while saving.");
            }
        });
    }

    const handleRedirect = () => {
        if (newlyCreatedPatientId) {
            window.location.href = `/patient-record-detailed?id=${newlyCreatedPatientId}`;
        }
    };

    if (successPopup) {
        const closeTriggers = successPopup.querySelectorAll('.popup-close, .popup-close-action');
        closeTriggers.forEach(btn => btn.addEventListener('click', handleRedirect));
    }
});