// Expose updatePagination globally so global.js can call it upon deletion if needed
let updatePagination = () => {};

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const searchInput = document.getElementById("search-input");
    const filterActionSelect = document.getElementById("filter-action-type");
    const filterUserSelect = document.getElementById("filter-user-type");

    const allRows = Array.from(
        document.querySelectorAll(".root-table-body .table-row:not(.empty-row)")
    );
    const emptyRow = document.querySelector(".root-table-body .empty-row");

    // Pagination Controls
    const prevBtn = document.getElementById("prev-page");
    const nextBtn = document.getElementById("next-page");
    const pageInfo = document.getElementById("page-info");

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

    // --- 2. SEARCH & FILTERING ---
    function filterLogs() {
        const query = searchInput?.value.toLowerCase().trim() || "";
        const selectedAction = filterActionSelect?.value.toLowerCase().trim() || "";
        const selectedUserType = filterUserSelect?.value.toLowerCase().trim() || "";

        visibleRows = allRows.filter((row) => {
            const columns = row.querySelectorAll(".table-row-text");
            if (columns.length < 6) return false;

            const username = columns[1].textContent.toLowerCase();
            const role = columns[2].textContent.toLowerCase().replace(/\s+/g, "");
            const action = columns[3].textContent.toLowerCase().trim();
            const description = columns[4].textContent.toLowerCase();
            const ipAddress = columns[5].textContent.toLowerCase();

            const matchesSearch =
                query === "" ||
                username.includes(query) ||
                description.includes(query) ||
                ipAddress.includes(query);

            const matchesAction =
                selectedAction === "" || action.includes(selectedAction);

            const matchesUserType =
                selectedUserType === "" || role.toLowerCase() === selectedUserType.replace(/\s+/g, "").toLowerCase()

            return matchesSearch && matchesAction && matchesUserType;
        });

        currentPage = 1;
        updatePagination();
    }

    // Event Listeners
    searchInput?.addEventListener("input", filterLogs);
    filterActionSelect?.addEventListener("change", filterLogs);
    filterUserSelect?.addEventListener("change", filterLogs);

    // Initialize Pagination
    updatePagination();
});