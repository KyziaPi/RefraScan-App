document.addEventListener("DOMContentLoaded", () => {
    // --- DOM ELEMENTS ---
    const allRows = Array.from(document.querySelectorAll(".root-table-body .table-row:not(.empty-row)"));
    const emptyRow = document.querySelector(".root-table-body .empty-row");

    // Pagination Controls
    const prevBtn = document.getElementById("prev-page");
    const nextBtn = document.getElementById("next-page");
    const pageInfo = document.getElementById("page-info");

    // Optional Search & Filter Inputs
    const searchInput = document.getElementById("search-input");
    const filterSelect = document.getElementById("filter-class");

    // Modal Elements (Populated by global.js)
    const deleteForm = document.getElementById("delete-popup-form");
    const hiddenIdInput = document.getElementById("delete-item-id");
    const deletePopup = document.getElementById("delete-confirmation-popup");
    const successPopup = document.getElementById("record-deleted-popup");

    // State Variables
    const itemsPerPage = 10;
    let currentPage = 1;
    let visibleRows = [...allRows];

    // --- 1. PAGINATION SYSTEM ---

    function updatePagination() {
        const totalItems = visibleRows.length;
        const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;

        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;

        allRows.forEach(row => (row.style.display = "none"));

        if (totalItems === 0) {
            if (emptyRow) emptyRow.style.display = "flex"; emptyRow.style.justifyContent = "center";
        } else {
            if (emptyRow) emptyRow.style.display = "none";

            const start = (currentPage - 1) * itemsPerPage;
            const end = start + itemsPerPage;
            const pageBatch = visibleRows.slice(start, end);

            pageBatch.forEach(row => (row.style.display = "grid"));
        }

        if (pageInfo) pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        if (prevBtn) prevBtn.disabled = currentPage === 1;
        if (nextBtn) nextBtn.disabled = currentPage === totalPages || totalPages === 0;
    }

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

    // --- 2. SEARCH & FILTERING ---

    function filterTable() {
        const query = searchInput?.value.toLowerCase().trim() || "";
        const selectedClass = filterSelect?.value.toLowerCase() || "all";

        visibleRows = allRows.filter(row => {
            const columns = row.querySelectorAll(".table-row-text");
            if (columns.length < 6) return false;

            const inferenceId = columns[0].textContent.toLowerCase();
            const name = columns[1].textContent.toLowerCase();
            const prediction = columns[5].textContent.toLowerCase();

            const matchesSearch = inferenceId.includes(query) || name.includes(query);
            const matchesFilter = selectedClass === "all" || prediction.includes(selectedClass);

            return matchesSearch && matchesFilter;
        });

        currentPage = 1;
        updatePagination();
    }

    searchInput?.addEventListener("input", filterTable);
    filterSelect?.addEventListener("change", filterTable);

    // --- 3. AJAX DELETE SUBMISSION ---

    deleteForm?.addEventListener("submit", async (e) => {
        e.preventDefault();

        // Values pre-populated by global.js
        const itemId = hiddenIdInput?.value;
        const deleteUrl = deleteForm.action;

        try {
            const response = await fetch(deleteUrl, { method: "DELETE" });
            const result = await response.json();

            if (response.ok) {
                // Remove deleted row from DOM & arrays
                const targetRow = allRows.find(row => {
                    const idText = row.querySelector(".table-row-text")?.textContent.trim();
                    return idText === itemId;
                });

                if (targetRow) {
                    const rowIdx = allRows.indexOf(targetRow);
                    if (rowIdx > -1) allRows.splice(rowIdx, 1);

                    const visibleIdx = visibleRows.indexOf(targetRow);
                    if (visibleIdx > -1) visibleRows.splice(visibleIdx, 1);

                    targetRow.remove();
                }

                updatePagination();

                // Toggle Modals
                deletePopup?.classList.remove("active");
                successPopup?.classList.add("active");
            } else {
                alert(result.message || "Failed to delete record.");
            }
        } catch (error) {
            console.error("Error deleting inference record:", error);
            alert("An error occurred while connecting to the server.");
        }
    });

    // Initialize Pagination
    updatePagination();
});