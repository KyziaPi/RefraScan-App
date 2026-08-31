// Expose updatePagination globally so global.js can call it upon row deletion
let updatePagination = () => {};

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const allRows = Array.from(document.querySelectorAll(".root-table-body .table-row:not(.empty-row)"));
    const emptyRow = document.querySelector(".root-table-body .empty-row");

    // Pagination Controls
    const prevBtn = document.getElementById("prev-page");
    const nextBtn = document.getElementById("next-page");
    const pageInfo = document.getElementById("page-info");

    // Search Input
    const searchInput = document.getElementById("search-input");

    // Pagination State
    const itemsPerPage = 10;
    let currentPage = 1;
    let visibleRows = [...allRows];

    // --- 1. PAGINATION SYSTEM ---
    updatePagination = function() {
        const totalItems = visibleRows.length;
        const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;

        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;

        allRows.forEach(row => (row.style.display = "none"));

        if (totalItems === 0) {
            if (emptyRow) {
                emptyRow.style.display = "flex";
                emptyRow.style.justifyContent = "center";
            }
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

    // --- 2. SEARCH FILTERING ---
    function filterTable() {
        const query = searchInput?.value.toLowerCase().trim() || "";

        visibleRows = allRows.filter(row => {
            const columns = row.querySelectorAll(".table-row-text");
            if (columns.length < 5) return false;

            const patientCode = columns[0].textContent.toLowerCase();
            const name = columns[2].textContent.toLowerCase();
            const referredFrom = columns[4].textContent.toLowerCase();

            return patientCode.includes(query) || name.includes(query) || referredFrom.includes(query);
        });

        currentPage = 1;
        updatePagination();
    }

    searchInput?.addEventListener("input", filterTable);

    // Initialize Pagination
    updatePagination();
});