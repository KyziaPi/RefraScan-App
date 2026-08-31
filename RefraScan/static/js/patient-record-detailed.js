document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements for Follow Up
    const fuForm = document.getElementById('follow-up-form');
    const fuIdInput = document.getElementById('fu-id');
    const fuEncounterIdInput = document.getElementById('fu-encounter-id');
    const fuDateInput = document.getElementById('fu-date');
    const fuDetailsInput = document.getElementById('fu-details');
    const fuTitle = document.getElementById('fu-popup-title');

    // Helper to format date string to YYYY-MM-DD for <input type="date">
    function formatDateForInput(dateStr) {
        if (!dateStr || dateStr === '—') {
            const today = new Date();
            return today.toISOString().split('T')[0];
        }
        const d = new Date(dateStr);
        if (!isNaN(d.getTime())) {
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
        return dateStr;
    }

    // 1. Handle "New Follow Up" Header / Add Button click
    document.querySelectorAll('.btn-add-fu').forEach(btn => {
        btn.addEventListener('click', () => {
            if (fuIdInput) fuIdInput.value = ''; // Empty ID means INSERT new
            if (fuEncounterIdInput) fuEncounterIdInput.value = btn.dataset.encounterId;
            if (fuDateInput) fuDateInput.value = formatDateForInput(null); // Defaults to today
            if (fuDetailsInput) fuDetailsInput.value = '';
            if (fuTitle) fuTitle.textContent = 'Add New Follow Up';
        });
    });

    // 2. Handle "Edit" Row Button click
    document.querySelectorAll('.edit-fu-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (fuIdInput) fuIdInput.value = btn.dataset.fuId;
            if (fuEncounterIdInput) fuEncounterIdInput.value = btn.dataset.encounterId;
            if (fuDateInput) fuDateInput.value = formatDateForInput(btn.dataset.fuDate);
            if (fuDetailsInput) fuDetailsInput.value = btn.dataset.fuDetails;
            if (fuTitle) fuTitle.textContent = `Edit Follow Up #${btn.dataset.fuNumber}`;
        });
    });

    // 3. Handle Form Submission (Save Follow Up)
    if (fuForm) {
        fuForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const payload = {
                fu_id: fuIdInput.value,
                encounter_id: fuEncounterIdInput.value,
                follow_up_date: fuDateInput.value,
                details: fuDetailsInput.value
            };

            try {
                const response = await fetch('/api/save-follow-up', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (response.ok) {
                    window.location.reload(); 
                } else {
                    const result = await response.json();
                    alert(result.error || "Failed to save follow-up.");
                }
            } catch (error) {
                console.error("Error saving follow up:", error);
                alert("Network error occurred.");
            }
        });
    }
});