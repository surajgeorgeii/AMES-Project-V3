// Global variables for state management
let currentPage = 1;
let currentSort = 'module_code';
let currentDirection = 'asc';
let searchTimeout;

document.addEventListener('DOMContentLoaded', function() {
    // Initial setup
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            loadModules();
        });
    }

    // Search input handling with debounce
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                loadModules();
            }, 300);
        });
    }

    // Filter change handlers
    document.getElementById('code_prefix')?.addEventListener('change', () => loadModules());

    // Sort handlers
    document.querySelectorAll('[data-sort]').forEach(header => {
        header.addEventListener('click', function(e) {
            e.preventDefault();
            handleSort(this.dataset.sort);
        });
    });

    // Initial load with URL parameters
    loadModules(Object.fromEntries(new URLSearchParams(window.location.search)));
});

async function loadModules(params = {}) {
    try {
        showLoading(true);
        const queryParams = new URLSearchParams({
            search: params.search || document.getElementById('search')?.value || '',
            code_prefix: params.code_prefix || document.getElementById('code_prefix')?.value || '',
            sort: params.sort || document.getElementById('sort')?.value || '',
            direction: params.direction || document.getElementById('direction')?.value || '',
            page: params.page || '1'
        });

        const response = await fetch(`/module-lead/modules/your-modules?${queryParams}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        
        if (!response.ok) throw new Error('Network response was not ok');
        
        const html = await response.text();
        updateTableContent(html);
        updateURL(Object.fromEntries(queryParams));
        setupTableInteractions();
        
    } catch (error) {
        showError('Error loading modules');
        console.error('Loading error:', error);
    } finally {
        showLoading(false);
    }
}

function updateTableContent(html) {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    // Update table content
    const newTable = tempDiv.querySelector('.table-responsive');
    if (newTable) {
        document.querySelector('.table-responsive').replaceWith(newTable);
    }
    
    // Update pagination if exists
    const newPagination = tempDiv.querySelector('.pagination');
    const currentPagination = document.querySelector('.pagination');
    if (newPagination && currentPagination) {
        currentPagination.replaceWith(newPagination);
    }
    
    // Update total count
    const newCount = tempDiv.querySelector('#totalModules');
    const currentCount = document.querySelector('#totalModules');
    if (newCount && currentCount) {
        currentCount.textContent = newCount.textContent;
    }
}

function setupTableInteractions() {
    // Setup clickable rows
    document.querySelectorAll('.clickable-row').forEach(row => {
        row.addEventListener('click', function(e) {
            if (!e.target.closest('a')) {
                window.location = this.dataset.href || this.getAttribute('onclick').match(/'([^']+)'/)[1];
            }
        });
    });

    // Setup pagination
    document.querySelectorAll('.pagination .page-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const url = new URL(this.href);
            loadModules(Object.fromEntries(url.searchParams));
        });
    });
}

async function handleSort(field) {
    const currentSort = document.getElementById('sort').value;
    const currentDirection = document.getElementById('direction').value;
    
    let newDirection = 'asc';
    if (field === currentSort && currentDirection === 'asc') {
        newDirection = 'desc';
    }

    document.getElementById('sort').value = field;
    document.getElementById('direction').value = newDirection;
    await loadModules();
    updateSortIndicators(field, newDirection);
}

function updateSortIndicators(field, direction) {
    document.querySelectorAll('[data-sort]').forEach(element => {
        const icon = element.querySelector('i');
        if (element.dataset.sort === field) {
            icon.className = `fas fa-sort-${direction}`;
        } else {
            icon.className = 'fas fa-sort';
        }
    });
}

function showLoading(show) {
    const indicator = document.getElementById('tableLoadingIndicator');
    if (indicator) {
        indicator.classList.toggle('d-none', !show);
    }
}

function showError(message) {
    // Implement your error display logic here
    console.error(message);
    // You could use a toast notification or alert system
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
