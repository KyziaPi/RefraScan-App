// Expose updatePagination globally so global.js can trigger re-pagination upon row deletion
let updatePagination = () => {};

document.addEventListener('DOMContentLoaded', () => {
    const editRoleForm = document.getElementById('edit-role-form');

    // --- 1. SUBMIT EDIT ROLE FORM VIA AJAX ---
    if (editRoleForm) {
        editRoleForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(editRoleForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch('/api/update-user-role', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                if (response.ok) {
                    window.location.reload();
                } else {
                    alert(result.error || "Failed to update role.");
                }
            } catch (err) {
                console.error("Error updating role:", err);
                alert("Network error occurred.");
            }
        });
    }

    // --- 2. PAGINATION SYSTEM ---
    const allRows = Array.from(
        document.querySelectorAll(".root-table-body .table-row:not(.empty-row)")
    );
    const emptyRow = document.querySelector(".root-table-body .empty-row");

    const prevBtn = document.getElementById("prev-page");
    const nextBtn = document.getElementById("next-page");
    const pageInfo = document.getElementById("page-info");

    const itemsPerPage = 10;
    let currentPage = 1;
    let visibleRows = [...allRows];

    updatePagination = function() {
        const totalItems = visibleRows.length;
        const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;

        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;

        // Hide all rows initially
        allRows.forEach((row) => (row.style.display = "none"));

        if (totalItems === 0) {
            if (emptyRow) {
                emptyRow.style.display = "grid";
            }
        } else {
            if (emptyRow) emptyRow.style.display = "none";

            const start = (currentPage - 1) * itemsPerPage;
            const end = start + itemsPerPage;
            const pageBatch = visibleRows.slice(start, end);

            pageBatch.forEach((row) => (row.style.display = "grid"));
        }

        if (pageInfo) pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        if (prevBtn) prevBtn.disabled = currentPage === 1;
        if (nextBtn) nextBtn.disabled = currentPage === totalPages || totalPages === 0;
    };

    prevBtn?.addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            updatePagination();
        }
    });

    nextBtn?.addEventListener("click", () => {
        const totalPages = Math.ceil(visibleRows.length / itemsPerPage);
        if (currentPage < totalPages) {
            currentPage++;
            updatePagination();
        }
    });

    // Initialize Pagination
    updatePagination();
});