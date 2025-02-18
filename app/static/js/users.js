document.addEventListener('DOMContentLoaded', function() {
    const createUserForm = document.getElementById('createUserForm');
    const createUserModal = document.getElementById('createUserModal');
    const modal = new bootstrap.Modal(createUserModal);

    if (createUserForm) {
        createUserForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            // Reset previous error states
            this.querySelectorAll('.is-invalid').forEach(el => {
                el.classList.remove('is-invalid');
                el.nextElementSibling.textContent = '';
            });
            const formError = document.getElementById('formError');
            formError.classList.add('d-none');
            formError.textContent = '';

            // Show loading state
            const submitBtn = this.querySelector('button[type="submit"]');
            const spinner = submitBtn.querySelector('.spinner-border');
            submitBtn.disabled = true;
            spinner.classList.remove('d-none');

            try {
                // Get form data
                const formData = {
                    username: this.querySelector('[name="username"]').value.trim(),
                    email: this.querySelector('[name="email"]').value.trim(),
                    password: this.querySelector('[name="password"]').value,
                    role: this.querySelector('[name="role"]').value
                };

                const response = await fetch(this.action, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });

                let result;
                try {
                    result = await response.json();
                    console.log('Server response:', result);  // Debug log
                } catch (jsonError) {
                    console.error('JSON parse error:', jsonError);
                    throw new Error('Invalid server response');
                }

                if (response.ok && result.success) {
                    // Use global showToast function from base.html
                    showToast(result.message || 'User created successfully', 'success');
                    modal.hide();
                    this.reset();
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    if (result.errors) {
                        Object.entries(result.errors).forEach(([field, errors]) => {
                            const input = this.querySelector(`[name="${field}"]`);
                            if (input) {
                                input.classList.add('is-invalid');
                                const feedback = input.nextElementSibling;
                                const errorMessage = Array.isArray(errors) ? errors[0] : errors;
                                feedback.textContent = errorMessage;
                            } else if (field === 'general') {
                                formError.textContent = Array.isArray(errors) ? errors[0] : errors;
                                formError.classList.remove('d-none');
                            }
                        });
                    }
                    // Show error notification using global showToast
                    showToast(result.message || 'Failed to create user', 'danger');
                }
            } catch (error) {
                console.error('Error:', error);
                formError.textContent = error.message || 'Server error. Please try again.';
                formError.classList.remove('d-none');
                showToast('Server error. Please try again.', 'danger');
            } finally {
                submitBtn.disabled = false;
                spinner.classList.add('d-none');
            }
        });
    }

    const editUserForm = document.getElementById('editUserForm');
    if (editUserForm) {
        editUserForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            // Reset previous error states
            this.querySelectorAll('.is-invalid').forEach(el => {
                el.classList.remove('is-invalid');
                el.nextElementSibling.textContent = '';
            });
            const formError = document.getElementById('editFormError');
            formError.classList.add('d-none');
            formError.textContent = '';

            // Show loading state
            const submitBtn = this.querySelector('button[type="submit"]');
            const spinner = submitBtn.querySelector('.spinner-border');
            submitBtn.disabled = true;
            spinner.classList.remove('d-none');

            try {
                const userId = document.getElementById('editUserId').value;
                const formData = {
                    username: document.getElementById('editUsername').value.trim(),
                    email: document.getElementById('editEmail').value.trim(),
                    role: document.getElementById('editRole').value
                };

                const response = await fetch(`/admin/api/users/${userId}`, {
                    method: 'PUT',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast(result.message || 'User updated successfully', 'success');
                    const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
                    modal.hide();
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    if (result.errors) {
                        Object.entries(result.errors).forEach(([field, errors]) => {
                            const input = this.querySelector(`[name="${field}"]`);
                            if (input) {
                                input.classList.add('is-invalid');
                                const feedback = input.nextElementSibling;
                                feedback.textContent = Array.isArray(errors) ? errors[0] : errors;
                            }
                        });
                    }
                    formError.textContent = result.message || 'Failed to update user';
                    formError.classList.remove('d-none');
                }
            } catch (error) {
                console.error('Error:', error);
                formError.textContent = 'Server error. Please try again.';
                formError.classList.remove('d-none');
            } finally {
                submitBtn.disabled = false;
                spinner.classList.add('d-none');
            }
        });
    }

    const emailUserForm = document.getElementById('emailUserForm');
    if (emailUserForm) {
        emailUserForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            // Reset previous error states
            this.querySelectorAll('.is-invalid').forEach(el => {
                el.classList.remove('is-invalid');
                el.nextElementSibling.textContent = '';
            });
            const formError = document.getElementById('emailFormError');
            formError.classList.add('d-none');
            formError.textContent = '';

            // Show loading state
            const submitBtn = this.querySelector('button[type="submit"]');
            const spinner = submitBtn.querySelector('.spinner-border');
            submitBtn.disabled = true;
            spinner.classList.remove('d-none');

            try {
                const userId = document.getElementById('emailUserId').value;
                const formData = {
                    subject: this.querySelector('[name="subject"]').value.trim(),
                    message: this.querySelector('[name="message"]').value.trim()
                };

                const response = await fetch(`/admin/users/${userId}/send-email`, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast(result.message || 'Email sent successfully', 'success');
                    const modal = bootstrap.Modal.getInstance(document.getElementById('emailUserModal'));
                    modal.hide();
                } else {
                    if (result.errors) {
                        Object.entries(result.errors).forEach(([field, errors]) => {
                            const input = this.querySelector(`[name="${field}"]`);
                            if (input) {
                                input.classList.add('is-invalid');
                                const feedback = input.nextElementSibling;
                                feedback.textContent = Array.isArray(errors) ? errors[0] : errors;
                            }
                        });
                    }
                    formError.textContent = result.message || 'Failed to send email';
                    formError.classList.remove('d-none');
                }
            } catch (error) {
                console.error('Error:', error);
                formError.textContent = 'Server error. Please try again.';
                formError.classList.remove('d-none');
            } finally {
                submitBtn.disabled = false;
                spinner.classList.add('d-none');
            }
        });
    }
});

function editUser(userId, username, email, role) {
    // Populate the edit form
    document.getElementById('editUserId').value = userId;
    document.getElementById('editUsername').value = username;
    document.getElementById('editEmail').value = email;
    document.getElementById('editRole').value = role;

    // Show the modal
    const editModal = new bootstrap.Modal(document.getElementById('editUserModal'));
    editModal.show();
}

function emailUser(userId, username, email) {
    // Reset form
    const form = document.getElementById('emailUserForm');
    form.reset();
    
    // Set user ID
    document.getElementById('emailUserId').value = userId;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('emailUserModal'));
    modal.show();
}
