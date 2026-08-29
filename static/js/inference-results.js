document.addEventListener("DOMContentLoaded", () => {
    // --- 1. Probability Bar Calculation ---
    const classNames = ["myopia", "hyperopia", "emmetropia"];

    classNames.forEach(cls => {
        const probElement = document.getElementById(`${cls}-probability`);
        const barBgElement = document.querySelector(`.container-${cls}-bar-bg`) || document.querySelector(`.${cls} .container-${cls}-bar-bg`);

        if (probElement && barBgElement) {
            let probValue = parseFloat(probElement.textContent.trim()) || 0;

            if (probValue <= 1.0) {
                probValue *= 100;
            }

            const paddingRight = Math.max(0, 100 - probValue);
            barBgElement.style.paddingRight = `${paddingRight}%`;
        }
    });

    // --- 2. Dynamic Patient Record Button Logic ---
    const patientIdInput = document.querySelector('input[name="patient_id"]');
    const patientRecordBtn = document.getElementById('patientRecordBtn');

    if (patientIdInput && patientRecordBtn) {
        const patientId = patientIdInput.value ? patientIdInput.value.trim() : "";

        // Check if patient_id exists and is valid
        if (patientId && patientId !== "None" && patientId !== "null") {
            // EXISTING PATIENT: Route to detailed record with query param
            patientRecordBtn.classList.remove('add-patient-record-btn');
            patientRecordBtn.classList.add('view-patient-record-btn');
            patientRecordBtn.textContent = 'View Patient Record';
            patientRecordBtn.setAttribute('formaction', '/patient-record-detailed');
        } else {
            // NEW PATIENT: Route to add patient form
            patientRecordBtn.classList.remove('view-patient-record-btn');
            patientRecordBtn.classList.add('add-patient-record-btn');
            patientRecordBtn.textContent = 'Add Patient Record';
            patientRecordBtn.setAttribute('formaction', '/add-patient');
        }
    }
});