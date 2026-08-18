document.addEventListener('DOMContentLoaded', () => {
    /* Image Upload Functionality */
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const preview = document.getElementById('preview');
    const placeholder = document.querySelector('.placeholder');
    const fileName = document.getElementById('fileName');
    const fileNameWrapper = document.getElementById('fileNameWrapper');

    // Trigger file input when the main button is clicked
    dropZone.addEventListener('click', (e) => {
        // Prevent infinite loop if clicking the input itself
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });

    // Handle file selection
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            // Update only the span content and show the wrapper label
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
            // Clear span text and hide label if selection is cleared
            if (fileName) fileName.textContent = '';
            if (fileNameWrapper) fileNameWrapper.style.display = 'none';
        }
    });

    // Optional: Drag and drop support
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


    /* Input Group Functionality */

    // Mock database for existing patient search
    const mockPatients = [
        { id: 'PAT-1001', firstName: 'John', lastName: 'Doe', phone: '09171234567', age: 45, email: 'john@example.com' },
        { id: 'PAT-1002', firstName: 'Jane', lastName: 'Smith', phone: '09189876543', age: 32, email: 'jane@example.com' },
        { id: 'PAT-1003', firstName: 'Robert', lastName: 'Johnson', phone: '09191112223', age: 58, email: 'robert@example.com' }
    ];

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
                document.getElementById('submission-type').value = 'existing';
            }
        });
    });

    // Patient Search Implementation
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        searchResults.innerHTML = '';

        if (query.length < 2) {
            searchResults.classList.add('hidden');
            return;
        }

        const filtered = mockPatients.filter(p => 
            p.firstName.toLowerCase().includes(query) ||
            p.lastName.toLowerCase().includes(query) ||
            p.id.toLowerCase().includes(query) ||
            p.phone.includes(query)
        );

        if (filtered.length === 0) {
            searchResults.innerHTML = `<div class="search-item">No patients found</div>`;
        } else {
            filtered.forEach(patient => {
                const item = document.createElement('div');
                item.className = 'search-item';
                item.innerHTML = `
                    <div>
                        <strong>${patient.lastName}, ${patient.firstName}</strong>
                        <div class="search-item-info"><span>ID: ${patient.id} | Phone: ${patient.phone}</span></div>
                    </div>
                `;
                item.addEventListener('click', () => selectPatient(patient));
                searchResults.appendChild(item);
            });
        }

        searchResults.classList.remove('hidden');
    });

    // Select Patient Logic
    function selectPatient(patient) {
        patientIdInput.value = patient.id;
        document.getElementById('summary-name').textContent = `${patient.lastName}, ${patient.firstName}`;
        document.getElementById('summary-id').textContent = patient.id;
        document.getElementById('summary-phone').textContent = patient.phone;
        
        // Auto-fill shared age field
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
    });
});