// Remove debug logs
document.addEventListener('DOMContentLoaded', function() {
    showLoading(true);
    
    if (moduleData) {
        try {
            updatePageContent(moduleData, reviewData);
            showLoading(false);
        } catch (error) {
            showError('Error displaying module data');
        }
    } else {
        showError('No module data available');
    }
});

async function loadModuleData(moduleId) {
    try {
        const [moduleResponse, reviewResponse] = await Promise.all([
            fetch(`/module-lead/modules/${moduleId}`),
            fetch(`/module-lead/modules/${moduleId}/review`)
        ]);

        const [moduleData, reviewData] = await Promise.all([
            moduleResponse.json(),
            reviewResponse.json()
        ]);

        if (!moduleResponse.ok || !moduleData.success) {
            throw new Error(moduleData.message || 'Failed to load module data');
        }

        // Update the page content
        updatePageContent(moduleData.data, reviewData.data);

        // Show the content
        showLoading(false);

    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Error loading module details');
    }
}

// Combine update functions
function updatePageContent(module, review) {
    if (!module) return;
    
    // Update page metadata
    document.title = `View Module - ${module.module_code}`;
    
    // Update all module details at once
    const details = {
        'module-code': module.module_code,
        'module-name': module.module_name,
        'module-lead': module.module_lead,
        'module-level': module.level ? `Level ${module.level}` : 'N/A'
    };

    Object.entries(details).forEach(([id, value]) => {
        const elements = document.querySelectorAll(`[data-field="${id}"]`);
        elements.forEach(el => el.textContent = value || 'N/A');
    });

    // Update status badge
    updateStatusBadge(module.in_use);

    // Update review information if available
    if (review) {
        updateReviewInfo(review);
    }
}

function updateStatusBadge(inUse) {
    const statusBadge = document.querySelector('.module-status');
    if (statusBadge) {
        statusBadge.className = `badge ${inUse ? 'bg-success' : 'bg-secondary'} module-status`;
        statusBadge.textContent = inUse ? 'Active' : 'Inactive';
    }
}

function updateReviewInfo(review) {
    if (!review) return;

    // Update review details
    const reviewElements = {
        'enhancement-plan': review.enhancement_plan_update,
        'student-attainment': review.student_attainment,
        'student-feedback': review.student_feedback,
        'risks': review.risks,
        'engagement-rating': review.engagement_rating,
        'learning-environment-rating': review.learning_environment_rating,
        'timetabling-rating': review.timetabling_rating
    };

    Object.entries(reviewElements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value || 'Not provided';
        }
    });

    // Update review date
    if (review.review_date) {
        const date = new Date(review.review_date.$date);
        document.querySelector('.review-date').textContent = 
            date.toLocaleDateString('en-GB', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
    }

    // Update enhancement plans
    if (review.enhancement_plans?.length > 0) {
        const plansContainer = document.querySelector('.enhancement-plans');
        if (plansContainer) {
            plansContainer.innerHTML = review.enhancement_plans.map(plan => `
                <div class="col-md-6 mb-3">
                    <div class="card enhancement-plan-card h-100">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h6 class="mb-0 text-primary">${plan.plan}</h6>
                            <span class="badge bg-primary">${plan.category || 'General'}</span>
                        </div>
                        <div class="card-body">
                            <div class="enhancement-details">
                                <h6 class="text-muted small">Implementation Details:</h6>
                                <p class="card-text">${plan.details || 'No details provided'}</p>
                            </div>
                            ${plan.added_date ? `
                                <div class="mt-3 pt-2 border-top">
                                    <small class="text-muted">
                                        <i class="fas fa-calendar-alt me-1"></i>
                                        Added: ${new Date(plan.added_date.$date).toLocaleDateString()}
                                    </small>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `).join('');
        }
    }
}

async function loadReviewerName(reviewerId) {
    try {
        const response = await fetch(`/module-lead/api/users/${reviewerId}`, {
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        const data = await response.json();
        if (data.success && data.data) {
            document.querySelector('.reviewer-name').textContent = data.data.username;
        }
    } catch (error) {
        console.error('Error loading reviewer name:', error);
    }
}

function showLoading(show) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const content = document.getElementById('moduleContent');
    
    if (loadingIndicator && content) {
        loadingIndicator.style.display = show ? 'block' : 'none';
        content.style.display = show ? 'none' : 'block';
    }
}

function showError(message) {
    const content = document.getElementById('moduleContent');
    if (content) {
        content.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-circle me-2"></i>
                ${message}
            </div>
        `;
    }
    showLoading(false);
}

// Add global toast function if not exists
window.showToast = window.showToast || function(message, type) {
    console.log(`${type.toUpperCase()}: ${message}`);
    // You can implement a proper toast notification here
};
