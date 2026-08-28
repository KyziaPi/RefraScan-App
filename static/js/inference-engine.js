document.addEventListener('DOMContentLoaded', () => {
    /* ==========================================
       Image Upload Functionality
    ========================================== */
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const preview = document.getElementById('preview');
    const placeholder = document.querySelector('.placeholder');
    const fileName = document.getElementById('fileName');
    const fileNameWrapper = document.getElementById('fileNameWrapper');

    // Trigger file input when the main button is clicked
    dropZone.addEventListener('click', (e) => {
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });

    // Handle file selection
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            if (fileName) fileName.textContent = file.name;
            if (fileNameWrapper) fileNameWrapper.style.display = 'block';

            const reader = new FileReader();
            reader.onload = function(e) {
                preview.src = e.target.result;
                preview.style.display = 'block';
                if (placeholder) placeholder.style.display = 'none';
            };
            reader.readAsDataURL(file);
        } else {
            if (fileName) fileName.textContent = '';
            if (fileNameWrapper) fileNameWrapper.style.display = 'none';
        }
    });

    // Drag and drop support
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--color-primary, #007bff)';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--color-border)';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--color-border)';
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            fileInput.dispatchEvent(new Event('change'));
        }
    });


    /* ==========================================
       Input Group & Tab Functionality
    ========================================== */
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const submissionTypeInput = document.getElementById('submission-type');
    const patientIdInput = document.getElementById('patient-id');
    const searchInput = document.getElementById('patient-search');
    const searchResults = document.getElementById('search-results');
    const summaryCard = document.getElementById('patient-summary-card');
    const clearBtn = document.getElementById('clear-selected-patient');
    const ageInput = document.getElementById('age');

    // Tab Switching Logic
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`${targetTab}-tab`).classList.add('active');

            // Reset selection state when switching tabs
            if (targetTab === 'new-patient') {
                submissionTypeInput.value = 'new';
                patientIdInput.value = '';
            } else {
                submissionTypeInput.value = 'existing';
            }
        });
    });

    /* ==========================================
       Live Patient Search (Database Integration)
    ========================================== */
    let debounceTimer;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();
        searchResults.innerHTML = '';

        if (query.length < 2) {
            searchResults.classList.add('hidden');
            return;
        }

        // Wait 300ms after the user stops typing before hitting the database
        debounceTimer = setTimeout(async () => {
            try {
                const response = await fetch(`/api/search-patients?q=${encodeURIComponent(query)}`);
                if (!response.ok) throw new Error("Search failed");
                
                const patients = await response.json();

                if (!Array.isArray(patients) || patients.length === 0) {
                    searchResults.innerHTML = `<div class="search-item">No patients found</div>`;
                } else {
                    patients.forEach(patient => {
                        const item = document.createElement('div');
                        item.className = 'search-item';
                        // Matches db column names: last_name, first_name, patient_code
                        item.innerHTML = `
                            <div>
                                <strong>${patient.last_name}, ${patient.first_name}</strong>
                                <div class="search-item-info">
                                    <span>ID: ${patient.patient_code} | Phone: ${patient.phone || 'N/A'}</span>
                                </div>
                            </div>
                        `;
                        item.addEventListener('click', () => selectPatient(patient));
                        searchResults.appendChild(item);
                    });
                }

                searchResults.classList.remove('hidden');
            } catch (error) {
                console.error("Error fetching patients:", error);
                searchResults.innerHTML = `<div class="search-item">Error searching database</div>`;
                searchResults.classList.remove('hidden');
            }
        }, 300); 
    });

    // Select Patient Logic
    function selectPatient(patient) {
        // Use database serial 'id' for relationships, but display 'patient_code'
        patientIdInput.value = patient.id; 
        document.getElementById('summary-name').textContent = `${patient.last_name}, ${patient.first_name}`;
        document.getElementById('summary-id').textContent = patient.patient_code;
        document.getElementById('summary-phone').textContent = patient.phone || 'N/A';
        
        // Auto-fill shared age field based on DB value
        if (patient.age) {
            ageInput.value = patient.age;
        }

        searchInput.parentElement.classList.add('hidden');
        searchResults.classList.add('hidden');
        summaryCard.classList.remove('hidden');
    }

    // Reset Selected Patient
    clearBtn.addEventListener('click', () => {
        patientIdInput.value = '';
        searchInput.value = '';
        ageInput.value = '';
        summaryCard.classList.add('hidden');
        searchInput.parentElement.classList.remove('hidden');
        
        // Refocus search bar
        setTimeout(() => searchInput.focus(), 50);
    });
});