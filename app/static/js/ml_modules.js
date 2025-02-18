document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Handle filter form submission
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            applyFilters();
        });

        // Add event listeners for filter changes
        ['search', 'status', 'code_prefix'].forEach(filterId => {
            const element = document.getElementById(filterId);
            if (element) {
                element.addEventListener('change', function() {
                    applyFilters();
                });
            }
        });
    }

    // Handle sort headers
    const sortHeaders = document.querySelectorAll('[data-sort]');
    sortHeaders.forEach(header => {
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

    // Add click handlers for sort headers
    document.querySelectorAll('th a[data-sort]').forEach(header => {
        header.addEventListener('click', function(e) {
            e.preventDefault();
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

function applyFilters() {
    const params = new URLSearchParams();
    
    // Add all filter values
    const search = document.getElementById('search').value;
    if (search) params.set('search', search);
    
    const status = document.getElementById('status').value;
    if (status && status !== 'all') params.set('review_status', status);
    
    const codePrefix = document.getElementById('code_prefix').value;
    if (codePrefix) params.set('code_prefix', codePrefix);
    
    const sort = document.getElementById('sort').value;
    if (sort) params.set('sort', sort);
    
    const direction = document.getElementById('direction').value;
    if (direction) params.set('direction', direction);
    
    // Add page and per_page parameters
    params.set('page', '1');
    params.set('per_page', '20');

    // Debug log
    console.log('Fetching with params:', params.toString());

    showLoading();  // Use global showLoading

    // Update API endpoint path to match registered routes
    fetch(`/module-lead/api/modules/list?${params.toString()}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
        }
    })
    .then(response => {
        console.log('Response status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('Received data:', data);
        if (data.success) {
            updateTable(data.data.items);
            if (data.data.total !== undefined) {
                document.querySelector('h3').textContent = `All Modules (${data.data.total})`;
            }
            updateURL(params);
        } else {
            showToast(data.message || 'Error loading modules', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error loading modules', 'danger');
    })
    .finally(() => {
        hideLoading();
    });
}

// Helper functions for UI updates
function updateTable(modules) {
    const tableBody = document.querySelector('.table tbody');
    if (!tableBody) return;

    if (!modules || !Array.isArray(modules) || modules.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4 text-muted">
                    <i class="fas fa-inbox fa-2x mb-2 d-block"></i>
                    <p class="mb-0">No modules found</p>
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = modules.map(module => {
        // Ensure module._id is properly handled
        let moduleId;
        if (typeof module._id === 'object' && module._id.$oid) {
            moduleId = module._id.$oid;
        } else if (typeof module._id === 'string') {
            moduleId = module._id;
        } else {
            moduleId = '';
        }

        return `
            <tr>
                <td class="px-3">
                    <div class="text-truncate" style="max-width: 200px" title="${module.module_code || ''}">
                        ${module.module_code || 'N/A'}
                    </div>
                </td>
                <td class="px-3">
                    <div class="text-truncate" style="max-width: 300px" title="${module.module_name || ''}">
                        ${module.module_name || 'N/A'}
                    </div>
                </td>
                <td class="px-3">
                    <div class="text-truncate" style="max-width: 100px" title="Level ${module.level || ''}">
                        Level ${module.level || 'N/A'}
                    </div>
                </td>
                <td class="px-3">
                    <span class="badge ${module.review_submitted ? 'bg-success' : 'bg-warning'}">
                        ${module.review_submitted ? 'Reviewed' : 'Pending'}
                    </span>
                </td>
                <td class="px-3">
                    <div class="text-truncate" style="max-width: 150px" title="${module.module_lead || ''}">
                        ${module.module_lead || 'N/A'}
                    </div>
                </td>
                <td class="px-3">
                    <div class="text-truncate" style="max-width: 150px" title="${reviewerName}">
                        ${reviewerName}
                    </div>
                </td>
                <td>
                    <button type="button" 
                            class="btn btn-sm btn-outline-primary edit-module-btn" 
                            data-module-id="${moduleId}"
                            title="Edit module">
                        <i class="fas fa-edit"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function updatePagination(pagination) {
    const paginationContainer = document.querySelector('.card-footer .pagination');
    if (!paginationContainer) return;

    // Implementation depends on your pagination structure
    // ...existing pagination update code...
}

function updateURL(params) {
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.pushState({}, '', newUrl);
}

// Toast notification system
function showToast(message, type = 'success', duration = 5000) {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: duration });
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1050';
    document.body.appendChild(container);
    return container;
}
