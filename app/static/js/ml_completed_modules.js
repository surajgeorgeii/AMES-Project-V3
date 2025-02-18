document.addEventListener('DOMContentLoaded', function() {
    const moduleTable = document.querySelector('#moduleTable tbody');
    const searchInput = document.querySelector('input[name="search"]');
    let currentRequest = null;

    async function loadModules(params = {}) {
        try {
            showLoading(true);
            const queryParams = new URLSearchParams({
                search: params.search || document.getElementById('search').value || '',
                code_prefix: params.code_prefix || document.getElementById('code_prefix').value || '',
                sort: params.sort || document.getElementById('sort').value || '',
                direction: params.direction || document.getElementById('direction').value || '',
                page: params.page || '1'
            });

            const response = await fetch(`/module-lead/modules/completed?${queryParams}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            
            if (data.success) {
                renderModules(data.data.modules);
                updateTotalCount(data.data.total);
                updateURL(Object.fromEntries(queryParams));
            } else {
                showError(data.message || 'Error loading modules');
            }
        } catch (error) {
            showError('Network error');
            console.error('Loading error:', error);
        } finally {
            showLoading(false);
        }
    }

    function formatDate(dateString) {
        if (!dateString) return 'No date recorded';
        const date = new Date(dateString);
        return date.toISOString().split('T')[0];
    }

    function renderModules(modules) {
        if (!modules || modules.length === 0) {
            moduleTable.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4">
                        <div class="text-muted">
                            <i class="fas fa-clipboard-check fa-2x mb-3"></i>
                            <p class="mb-0">No completed module reviews found</p>
                        </div>
                    </td>
                </tr>`;
            return;
        }

        moduleTable.innerHTML = modules.map(module => `
            <tr>
                <td>${module.module_code || 'N/A'}</td>
                <td>${module.module_name || 'N/A'}</td>
                <td>${module.module_lead || 'N/A'}</td>
                <td>${formatDate(module.review_date?.$date)}</td>
                <td>${module.reviewer_name || 'Unknown'}</td>
                <td>
                    <a href="/module-lead/modules/${module._id.$oid}/view" 
                       class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-eye"></i> View
                    </a>
                </td>
            </tr>
        `).join('');
    }

    function showError(message) {
        moduleTable.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4">
                    <div class="text-danger">${message}</div>
                </td>
            </tr>`;
    }

    function updateTotalCount(total) {
        const totalElement = document.getElementById('totalModules');
        if (totalElement) {
            totalElement.textContent = total;
        }
    }

    function applyFilters() {
        const params = {
            search: document.getElementById('search').value,
            code_prefix: document.getElementById('code_prefix').value,
            sort: document.getElementById('sort').value,
            direction: document.getElementById('direction').value
        };
        loadModules(params);
    }

    function updateURL(params) {
        const url = new URL(window.location);
        Object.entries(params).forEach(([key, value]) => {
            if (value) {
                url.searchParams.set(key, value);
            } else {
                url.searchParams.delete(key);
            }
        });
        window.history.pushState({}, '', url);
    }

    // Initial load with URL parameters
    loadModules(Object.fromEntries(new URLSearchParams(window.location.search)));

    // Search handling with debounce
    let searchTimeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            loadModules({ search: this.value });
        }, 300);
    });

    // Add form submit handler
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            loadModules();
        });
    }

    // Add change handlers for filters
    ['code_prefix'].forEach(filterId => {
        const element = document.getElementById(filterId);
        if (element) {
            element.addEventListener('change', () => loadModules());
        }
    });

    // Handle sort headers
    document.querySelectorAll('[data-sort]').forEach(header => {
        header.addEventListener('click', function() {
            const sortField = this.dataset.sort;
            const currentSort = document.getElementById('sort').value;
            const currentDirection = document.getElementById('direction').value;
            
            let newDirection = 'asc';
            if (sortField === currentSort && currentDirection === 'asc') {
                newDirection = 'desc';
            }

            document.getElementById('sort').value = sortField;
            document.getElementById('direction').value = newDirection;
            applyFilters();
        });
    });
});
