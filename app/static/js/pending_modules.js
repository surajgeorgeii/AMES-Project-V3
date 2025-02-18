// Global variables for state management
let currentPage = 1;
let currentSort = 'module_code';
let currentDirection = 'asc';
let searchTimeout;

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Initial table load
    loadModulesTable();

    // Search handling with debounce
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(e.target.value);
            }, 500);
        });
    }

    // Sort handling
    document.querySelectorAll('[data-sort]').forEach(element => {
        element.addEventListener('click', (e) => {
            e.preventDefault();
            const sortField = e.currentTarget.dataset.sort;
            handleSort(sortField);
        });
    });

    // Review button handling
    setupReviewButtons();
});

function setupReviewButtons() {
    document.querySelectorAll('.review-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const moduleId = e.currentTarget.dataset.moduleId;
            window.location.href = `/admin/modules/${moduleId}/review`;
        });
    });
}

async function performSearch(query) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        loadModulesTable(1, query, currentSort, currentDirection);
    }, 500);
}

async function handleSort(field) {
    const newDirection = field === currentSort && currentDirection === 'asc' ? 'desc' : 'asc';
    currentSort = field;
    currentDirection = newDirection;

    await loadModulesTable(1, document.querySelector('input[name="search"]').value, field, newDirection);
    updateSortIndicators(field, newDirection);
}

async function loadModulesTable(page = 1, search = '', sort = currentSort, direction = currentDirection) {
    try {
        showLoading(true, 'Loading modules...');
        const response = await fetch(`/admin/modules/pending?page=${page}&search=${encodeURIComponent(search)}&sort=${sort}&direction=${direction}`);
        const html = await response.text();
        
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        // Update table content
        const newTable = tempDiv.querySelector('.table-responsive');
        document.querySelector('.table-responsive').replaceWith(newTable);
        
        // Update pagination if it exists
        const newPagination = tempDiv.querySelector('.card-footer');
        const currentPagination = document.querySelector('.card-footer');
        if (newPagination && currentPagination) {
            currentPagination.replaceWith(newPagination);
        }
        
        // Update total count
        const newCount = tempDiv.querySelector('#totalModules');
        const currentCount = document.querySelector('#totalModules');
        if (newCount && currentCount) {
            currentCount.textContent = newCount.textContent;
        }
        
        // Update URL without reload
        const newUrl = new URL(window.location);
        newUrl.searchParams.set('page', page);
        newUrl.searchParams.set('search', search);
        newUrl.searchParams.set('sort', sort);
        newUrl.searchParams.set('direction', direction);
        window.history.pushState({}, '', newUrl);
        
        // Reinitialize event listeners
        setupReviewButtons();
        setupPagination();
        
    } catch (error) {
        showToast('Error loading modules', 'danger');
        console.error('Table loading error:', error);
    } finally {
        showLoading(false);
    }
}

function setupPagination() {
    document.querySelectorAll('.pagination .page-link').forEach(link => {
        link.addEventListener('click', async (e) => {
            e.preventDefault();
            const url = new URL(e.currentTarget.href);
            const page = url.searchParams.get('page') || 1;
            const search = url.searchParams.get('search') || '';
            const sort = url.searchParams.get('sort') || currentSort;
            const direction = url.searchParams.get('direction') || currentDirection;
            
            await loadModulesTable(page, search, sort, direction);
        });
    });
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

// Review form handling
document.addEventListener('DOMContentLoaded', () => {
    const reviewForm = document.querySelector('#moduleReviewForm');
    if (reviewForm) {
        reviewForm.addEventListener('submit', handleReviewSubmit);
    }
});

async function handleReviewSubmit(e) {
    e.preventDefault();
    
    try {
        showLoading(true, 'Submitting review...');
        
        const formData = new FormData(e.target);
        const response = await fetch(e.target.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Review submitted successfully', 'success');
            setTimeout(() => {
                window.location.href = '/admin/modules';
            }, 1500);
        } else {
            showToast(data.message || 'Error submitting review', 'danger');
        }
        
    } catch (error) {
        showToast('Error submitting review', 'danger');
        console.error('Review submission error:', error);
    } finally {
        showLoading(false);
    }
}

// Enhancement plan management
function addEnhancementPlan() {
    const container = document.getElementById('enhancementPlans');
    const planCount = container.children.length + 1;
    
    const template = `
        <div class="enhancement-item mb-3">
            <label class="form-label">Enhancement Plan ${planCount}:</label>
            <select class="form-select mb-2" name="enhancementPlan${planCount}" required>
                <option value="">Select Enhancement Plan</option>
                ${enhancementOptions.map(opt => 
                    `<option value="${opt.value}">${opt.label}</option>`
                ).join('')}
            </select>
            <div class="mb-2">
                <label class="form-label">Details:</label>
                <textarea class="form-control" name="enhancementDetailsText${planCount}" 
                          rows="3" required></textarea>
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', template);
}

function validateReviewForm() {
    const requiredFields = [
        'enhancementPlan',
        'studentAttainment',
        'studentFeedback',
        'risks',
        'engagement',
        'learningEnvironment',
        'timetabling'
    ];
    
    let isValid = true;
    requiredFields.forEach(field => {
        const element = document.querySelector(`[name="${field}"]`);
        if (!element.value.trim()) {
            element.classList.add('is-invalid');
            isValid = false;
        } else {
            element.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

document.addEventListener('DOMContentLoaded', function() {
    // ...existing code...

    // Update loadModules function to handle all filters
    async function loadModules(params = {}) {
        try {
            showLoading(true);
            const queryParams = new URLSearchParams({
                search: params.search || document.getElementById('search').value || '',
                academic_year: params.academic_year || document.getElementById('academic_year').value || '',
                code_prefix: params.code_prefix || document.getElementById('code_prefix').value || '',
                sort: params.sort || document.getElementById('sort').value || '',
                direction: params.direction || document.getElementById('direction').value || '',
                page: params.page || '1'
            });

            const response = await fetch(`/admin/modules/pending?${queryParams}`, {
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

    // Add form submit handler
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            loadModules();
        });
    }

    // Add change handlers for filters
    ['academic_year', 'code_prefix'].forEach(filterId => {
        const element = document.getElementById(filterId);
        if (element) {
            element.addEventListener('change', () => loadModules());
        }
    });

    // Update search handling
    let searchTimeout;
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                loadModules();
            }, 300);
        });
    }

    // Handle sort headers
    document.querySelectorAll('[data-sort]').forEach(header => {
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
            loadModules();
        });
    });

    // Initial load with URL parameters
    loadModules(Object.fromEntries(new URLSearchParams(window.location.search)));
});

// Helper functions
function showLoading(show) {
    const indicator = document.getElementById('tableLoadingIndicator');
    if (indicator) {
        indicator.classList.toggle('d-none', !show);
    }
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
