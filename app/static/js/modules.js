// Global variables
let toastQueue = [];
let isShowingToast = false;

// ==========================================================
// Notification System
// ==========================================================
const showToast = (message, type = 'success', duration = 5000) => {
    toastQueue.push({ message, type, duration });
    if (!isShowingToast) {
        processToastQueue();
    }
};

const processToastQueue = () => {
    if (toastQueue.length === 0) {
        isShowingToast = false;
        return;
    }

    isShowingToast = true;
    const { message, type, duration } = toastQueue.shift();
    
    const toast = document.getElementById('notificationToast');
    const toastTitle = document.getElementById('toastTitle');
    const toastMessage = document.getElementById('toastMessage');
    const toastIcon = document.getElementById('toastIcon');
    
    const icons = {
        success: 'fa-check-circle text-success',
        danger: 'fa-exclamation-circle text-danger',
        warning: 'fa-exclamation-triangle text-warning',
        info: 'fa-info-circle text-info'
    };
    
    toastIcon.className = `fas ${icons[type] || icons.info}`;
    toastTitle.textContent = type.charAt(0).toUpperCase() + type.slice(1);
    toastMessage.textContent = message;
    
    const bsToast = new bootstrap.Toast(toast, { delay: duration });
    toast.classList.remove('bg-success', 'bg-danger', 'bg-warning', 'bg-info');
    toast.classList.add(`bg-${type}-subtle`);
    
    bsToast.show();

    setTimeout(() => {
        processToastQueue();
    }, duration + 500);
};

// ==========================================================
// Loading Overlay Management
// ==========================================================
const showLoading = (show = true, message = 'Processing...', progress = null) => {
    const elements = {
        spinner: document.getElementById('globalSpinner'),
        message: document.getElementById('loadingMessage'),
        progress: document.getElementById('uploadProgress')
    };
    
    elements.spinner.classList.toggle('d-none', !show);
    elements.message.textContent = message;
    
    if (progress !== null) {
        elements.progress.style.width = `${progress}%`;
        elements.progress.textContent = `${progress}%`;
        elements.progress.classList.remove('d-none');
    } else {
        elements.progress.classList.add('d-none');
    }
};

// ==========================================================
// Upload Summary Modal Management
// ==========================================================
const showUploadSummary = (data) => {
    const summaryModal = new bootstrap.Modal(document.getElementById('uploadSummaryModal'));
    
    // Update statistics with animation
    ['totalProcessed', 'modulesAdded', 'usersAdded'].forEach(id => {
        animateValue(id, data.stats[id.charAt(0).toLowerCase() + id.slice(1)] || 0);
    });
    
    updateWarningsAndErrors(data);
    summaryModal.show();
};

const animateValue = (elementId, value) => {
    const element = document.getElementById(elementId);
    element.textContent = '0';
    let current = 0;
    const target = parseInt(value) || 0;
    const increment = Math.ceil(target / 30);
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        element.textContent = current;
    }, 30);
};

const updateWarningsAndErrors = (data) => {
    // Handle warnings
    const warningSummary = document.getElementById('warningSummary');
    const warningsList = document.getElementById('warningsList');
    const warningsCount = document.getElementById('warningsCount');
    warningsList.innerHTML = '';
    
    if (data.warnings?.length) {
        warningSummary.classList.remove('d-none');
        warningsCount.textContent = data.warnings.length;
        groupAndDisplayItems(data.warnings, warningsList, 'warning');
    } else {
        warningSummary.classList.add('d-none');
    }
    
    // Handle errors
    const errorSummary = document.getElementById('errorSummary');
    const errorsList = document.getElementById('errorsList');
    const errorsCount = document.getElementById('errorsCount');
    errorsList.innerHTML = '';
    
    if (data.errors?.length) {
        errorSummary.classList.remove('d-none');
        errorsCount.textContent = data.errors.length;
        groupAndDisplayItems(data.errors, errorsList, 'danger');
    } else {
        errorSummary.classList.add('d-none');
    }
};

const groupAndDisplayItems = (items, listElement, type) => {
    const groups = items.reduce((acc, item) => {
        const key = item.replace(/['"A-Z0-9]+/g, 'X');
        if (!acc[key]) {
            acc[key] = { template: item, count: 0, examples: [] };
        }
        acc[key].count++;
        if (acc[key].examples.length < 3) {
            acc[key].examples.push(item);
        }
        return acc;
    }, {});

    Object.values(groups).forEach(group => {
        const li = document.createElement('li');
        li.className = 'mb-2';
        
        if (group.count === 1) {
            li.textContent = group.template;
        } else {
            const template = group.template.replace(/['"][^'"]+['"]/, 'X');
            li.innerHTML = createGroupHTML(group, template, type);
        }
        listElement.appendChild(li);
    });
};

const createGroupHTML = (group, template, type) => `
    <div class="d-flex align-items-start">
        <span class="badge bg-${type} text-dark me-2">${group.count}×</span>
        <div>
            <div>${template}</div>
            <small class="text-muted">Examples: ${group.examples.map(e => {
                const match = e.match(/['"][^'"]+['"]/);
                return match ? `<span class="badge bg-light text-dark me-1">${match[0]}</span>` : '';
            }).join('')}</small>
        </div>
    </div>
`;

// ==========================================================
// File Upload Handling
// ==========================================================
const validateFile = (file) => {
    const submitBtn = document.getElementById('uploadButton');
    const maxSize = 10 * 1024 * 1024; // 10MB
    
    if (!file) return false;
    
    const validTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel'
    ];
    
    if (!validTypes.includes(file.type)) {
        showToast('Please select a valid Excel file (.xlsx or .xls)', 'danger');
        submitBtn.disabled = true;
        return false;
    }

    if (file.size > maxSize) {
        showToast('File size exceeds maximum limit of 10MB', 'danger');
        submitBtn.disabled = true;
        return false;
    }
    
    submitBtn.disabled = false;
    showToast(`File selected: ${file.name}`, 'info', 2000);
    return true;
};

const handleFileUpload = async (e) => {
    e.preventDefault();
    const form = e.target;
    const file = document.getElementById('file').files[0];

    if (!validateFile(file)) return;
    
    try {
        showLoading(true, 'Uploading...');
        const response = await uploadFile(form);
        const data = await response.json();
        await handleUploadResponse(data);
    } catch (error) {
        showToast('Error uploading file', 'danger');
        console.error('Upload error:', error);
    } finally {
        showLoading(false);
    }
};

const startProgressSimulation = () => {
    let progress = 0;
    return setInterval(() => {
        progress += 5;
        if (progress <= 90) {
            showLoading(true, 'Processing file...', progress);
        }
    }, 300);
};

const uploadFile = async (form) => {
    const formData = new FormData(form);
    
    return await fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    });
};

const handleUploadResponse = async (response, startTime) => {
    try {
        const data = await response.json();
        console.log('Upload response:', data); // Debug log
        
        const duration = ((Date.now() - startTime) / 1000).toFixed(1);
        const stats = data.data?.stats || {
            total_processed: 0,
            modules_added: 0,
            users_added: 0
        };
        
        // Update loading state before showing results
        if (data.success) {
            showLoading(true, `Completed in ${duration}s!`, 100);
            setTimeout(() => {
                showLoading(false);
                // Show the summary modal
                showUploadSummary({
                    stats: stats,
                    warnings: data.data?.warnings || [],
                    errors: data.errors || []
                });
                
                // Show success messages
                showToast(data.message || 'Upload successful', 'success');
                
                if (stats.modules_added > 0 || stats.users_added > 0) {
                    setTimeout(() => {
                        showToast(
                            `Added ${stats.modules_added} modules and ${stats.users_added} users`,
                            'info',
                            6000
                        );
                    }, 1000);
                }
            }, 500);
        } else {
            showLoading(false);
            showToast(data.message || 'Upload failed', 'danger');
            showUploadSummary({
                stats: stats,
                warnings: [],
                errors: data.errors || ['Upload failed']
            });
        }

        // Show warnings if any
        if (data.data?.warnings?.length > 0) {
            setTimeout(() => {
                data.data.warnings.forEach((warning, index) => {
                    setTimeout(() => {
                        showToast(warning, 'warning', 8000);
                    }, index * 300);
                });
            }, 1500);
        }
    } catch (error) {
        showLoading(false);
        console.error('Error parsing response:', error);
        showToast('Error processing server response', 'danger');
    }
};

// ==========================================================
// Table Management
// ==========================================================
async function loadModulesTable(page = 1, search = '', status = 'all', sort = 'module_code', direction = 'asc') {
    try {
        showLoading(true, 'Loading modules...');
        const response = await fetch(
            `/admin/modules?page=${page}&search=${encodeURIComponent(search)}&status=${status}&sort=${sort}&direction=${direction}`
        );
        const html = await response.text();
        
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        // Update table content
        const newTable = tempDiv.querySelector('.table-responsive');
        document.querySelector('.table-responsive').replaceWith(newTable);
        
        // Update pagination
        updatePagination(tempDiv);
        
        // Update total count
        updateTotalCount(tempDiv);
        
        // Update URL
        updateURL({ page, search, status, sort, direction });
        
        // Reinitialize event listeners
        setupTableEventListeners();
        
    } catch (error) {
        showToast('Error loading modules', 'danger');
        console.error('Table loading error:', error);
    } finally {
        showLoading(false);
    }
}

function setupSearchAndFilters() {
    // Search handling with debounce
    const searchInput = document.querySelector('input[name="search"]');
    let searchTimeout;
    
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const status = document.querySelector('.btn-group .active').dataset.status;
                const sort = document.querySelector('[data-sort].active').dataset.sort;
                const direction = document.querySelector('[data-sort].active').dataset.direction;
                loadModulesTable(1, e.target.value, status, sort, direction);
            }, 500);
        });
    }

    // Status filter handling
    document.querySelectorAll('.btn-group .btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const status = e.target.dataset.status;
            const search = searchInput.value;
            const sort = document.querySelector('[data-sort].active').dataset.sort;
            const direction = document.querySelector('[data-sort].active').dataset.direction;
            loadModulesTable(1, search, status, sort, direction);
        });
    });

    // Sort handling
    document.querySelectorAll('[data-sort]').forEach(element => {
        element.addEventListener('click', (e) => {
            e.preventDefault();
            const sort = e.target.dataset.sort;
            const direction = e.target.dataset.direction === 'asc' ? 'desc' : 'asc';
            const status = document.querySelector('.btn-group .active').dataset.status;
            const search = searchInput.value;
            loadModulesTable(1, search, status, sort, direction);
        });
    });
}

// ==========================================================
// AJAX Operations
// ==========================================================
const moduleOperations = {
    delete: async (moduleId) => {
        try {
            const response = await fetch(`/admin/modules/${moduleId}/delete`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            const result = await response.json();
            if (result.success) {
                showToast('Module deleted successfully', 'success');
                await loadModulesTable(); // Refresh table
            } else {
                showToast(result.message || 'Failed to delete module', 'danger');
            }
        } catch (error) {
            console.error('Delete error:', error);
            showToast('Error deleting module', 'danger');
        }
    },

    toggleStatus: async (moduleId, currentStatus) => {
        try {
            const response = await fetch(`/admin/modules/${moduleId}/toggle_status`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            const result = await response.json();
            if (result.success) {
                const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
                showToast(`Module ${newStatus}`, 'success');
                await loadModulesTable(); // Refresh table
            } else {
                showToast(result.message || 'Failed to update status', 'danger');
            }
        } catch (error) {
            console.error('Status toggle error:', error);
            showToast('Error updating module status', 'danger');
        }
    }
};

// Update setupTableEventListeners to include new operation handlers
function setupTableEventListeners() {
    // Reinitialize pagination
    document.querySelectorAll('.pagination .page-link').forEach(link => {
        link.addEventListener('click', async (e) => {
            e.preventDefault();
            const url = new URL(e.currentTarget.href);
            const params = Object.fromEntries(url.searchParams);
            await loadModulesTable(
                params.page || 1,
                params.search || '',
                params.status || 'all',
                params.sort || 'module_code',
                params.direction || 'asc'
            );
        });
    });

    // Delete module handler
    document.querySelectorAll('.delete-module').forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to delete this module?')) {
                const moduleId = e.currentTarget.dataset.moduleId;
                await moduleOperations.delete(moduleId);
            }
        });
    });

    // Toggle status handler
    document.querySelectorAll('.toggle-status').forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            const moduleId = e.currentTarget.dataset.moduleId;
            const currentStatus = e.currentTarget.dataset.currentStatus;
            await moduleOperations.toggleStatus(moduleId, currentStatus);
        });
    });
}

// Consolidate upload form handlers
function setupUploadForm() {
    const form = document.getElementById('uploadForm');
    if (!form) return;

    // Remove duplicate event listener
    form.removeEventListener('submit', handleFileUpload);
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        const spinner = document.getElementById('uploadSpinner');
        const btnText = document.getElementById('uploadButtonText');
        const progressBar = document.getElementById('uploadProgress');
        const errorDiv = document.getElementById('uploadError');
        
        // Reset states
        errorDiv.classList.add('d-none');
        errorDiv.textContent = '';
        submitBtn.disabled = true;
        spinner.classList.remove('d-none');
        btnText.textContent = 'Uploading...';
        progressBar.classList.remove('d-none');
        progressBar.querySelector('.progress-bar').style.width = '0%';
        
        try {
            showLoading(true, 'Uploading...');
            const response = await uploadFile(form);
            const result = await response.json();
            
            if (result.success) {
                if (result.redirect) {
                    window.location.href = result.redirect;
                } else {
                    showToast('Upload successful', 'success');
                    await loadModulesTable(); // Reload table
                    bootstrap.Modal.getInstance(document.getElementById('uploadModal')).hide();
                }
            } else {
                errorDiv.textContent = result.message || 'Upload failed';
                errorDiv.classList.remove('d-none');
                showToast(result.message || 'Upload failed', 'danger');
            }
        } catch (error) {
            console.error('Upload error:', error);
            errorDiv.textContent = 'Server error. Please try again.';
            errorDiv.classList.remove('d-none');
            showToast('Error uploading file', 'danger');
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
            btnText.textContent = 'Upload';
            progressBar.classList.add('d-none');
            showLoading(false);
        }
    });
}

// ==========================================================
// Helper Functions
// ==========================================================
function updatePagination(tempDiv) {
    const newPagination = tempDiv.querySelector('.card-footer');
    const currentPagination = document.querySelector('.card-footer');
    if (newPagination && currentPagination) {
        currentPagination.replaceWith(newPagination);
    }
}

function updateTotalCount(tempDiv) {
    const newCount = tempDiv.querySelector('.total-modules');
    const currentCount = document.querySelector('.total-modules');
    if (newCount && currentCount) {
        currentCount.textContent = newCount.textContent;
    }
}

function updateURL(params) {
    const newUrl = new URL(window.location);
    Object.entries(params).forEach(([key, value]) => {
        if (value) {
            newUrl.searchParams.set(key, value);
        } else {
            newUrl.searchParams.delete(key);
        }
    });
    window.history.pushState({}, '', newUrl);
}

function setupTableEventListeners() {
    // Reinitialize pagination
    document.querySelectorAll('.pagination .page-link').forEach(link => {
        link.addEventListener('click', async (e) => {
            e.preventDefault();
            const url = new URL(e.currentTarget.href);
            const params = Object.fromEntries(url.searchParams);
            await loadModulesTable(
                params.page || 1,
                params.search || '',
                params.status || 'all',
                params.sort || 'module_code',
                params.direction || 'asc'
            );
        });
    });

    // Delete module handler
    document.querySelectorAll('.delete-module').forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to delete this module?')) {
                const moduleId = e.currentTarget.dataset.moduleId;
                await moduleOperations.delete(moduleId);
            }
        });
    });

    // Toggle status handler
    document.querySelectorAll('.toggle-status').forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            const moduleId = e.currentTarget.dataset.moduleId;
            const currentStatus = e.currentTarget.dataset.currentStatus;
            await moduleOperations.toggleStatus(moduleId, currentStatus);
        });
    });
};

function applyFilters() {
    const search = document.getElementById('search').value;
    const status = document.getElementById('status').value;
    const codePrefix = document.getElementById('code_prefix').value;
    const sort = document.getElementById('sort').value;
    const direction = document.getElementById('direction').value;
    
    const params = new URLSearchParams({
        search: search,
        status: status,
        code_prefix: codePrefix,
        sort: sort,
        direction: direction,
        page: 1 // Reset to first page when filters change
    });

    // Remove empty params
    for (const [key, value] of params.entries()) {
        if (!value) params.delete(key);
    }

    window.location.href = `${window.location.pathname}?${params.toString()}`;
}

// ==========================================================
// Event Listeners
// ==========================================================
document.addEventListener('DOMContentLoaded', () => {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // Initial table load
    loadModulesTable();

    // Setup forms and handlers
    setupUploadForm();
    setupSearchAndFilters();
    setupTableEventListeners();

    // File input handling
    const fileInput = document.getElementById('file');
    if (fileInput) {
        fileInput.addEventListener('change', validateFile);
    }

    // Upload form handling
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFileUpload);
    }
});

document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const form = this;
    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const spinner = document.getElementById('uploadSpinner');
    const btnText = document.getElementById('uploadButtonText');
    const progressBar = document.getElementById('uploadProgress');
    const errorDiv = document.getElementById('uploadError');
    
    // Reset states
    errorDiv.classList.add('d-none');
    errorDiv.textContent = '';
    submitBtn.disabled = true;
    spinner.classList.remove('d-none');
    btnText.textContent = 'Uploading...';
    progressBar.classList.remove('d-none');
    progressBar.querySelector('.progress-bar').style.width = '0%';
    
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });

        let result;
        try {
            result = await response.json();
            console.log('Server response:', result);  // Debug log
        } catch (err) {
            console.error('JSON parse error:', err);
            throw new Error('Invalid server response');
        }
        
        if (result.success && result.redirect) {
            window.location.href = result.redirect;
        } else {
            errorDiv.textContent = result.message || 'Upload failed';
            errorDiv.classList.remove('d-none');
            resetFormState();
        }
    } catch (error) {
        console.error('Upload error:', error);
        errorDiv.textContent = 'Server error. Please try again.';
        errorDiv.classList.remove('d-none');
        resetFormState();
    }

    function resetFormState() {
        submitBtn.disabled = false;
        spinner.classList.add('d-none');
        btnText.textContent = 'Upload';
        progressBar.classList.add('d-none');
    }
});

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
        ['search', 'status', 'academic_year', 'code_prefix'].forEach(filterId => {
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
});

// Add loading indicator functions
function showLoading() {
    const tableBody = document.querySelector('.table tbody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="100%" class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </td>
            </tr>
        `;
    }
}

function hideLoading() {
    const loadingRow = document.querySelector('.table tbody tr td .spinner-border');
    if (loadingRow) {
        loadingRow.parentElement.parentElement.remove();
    }
}
