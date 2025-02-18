document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const alertMessage = document.getElementById('alertMessage');

    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                email: document.getElementById('email').value,
                password: document.getElementById('password').value
            };

            try {
                const response = await fetch('/auth/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData),
                    credentials: 'same-origin'
                });

                const data = await response.json();
                
                if (data.success) {
                    alertMessage.className = 'alert alert-success mt-3';
                    alertMessage.textContent = 'Login successful. Redirecting...';
                    alertMessage.style.display = 'block';
                    
                    window.location.href = data.redirect_url;
                } else {
                    alertMessage.className = 'alert alert-danger mt-3';
                    alertMessage.textContent = data.message;
                    alertMessage.style.display = 'block';
                }
            } catch (error) {
                console.error('Login error:', error);
                alertMessage.className = 'alert alert-danger mt-3';
                alertMessage.textContent = 'An error occurred during login. Please try again.';
                alertMessage.style.display = 'block';
            }
        });
    }

    // User creation AJAX handler
    const userCreateForm = document.getElementById('userCreateForm');
    if (userCreateForm) {
        userCreateForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                username: document.getElementById('username').value,
                email: document.getElementById('email').value,
                password: document.getElementById('password').value,
                role: document.getElementById('role').value
            };

            fetch('/auth/api/users', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData),
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                alertMessage.className = 'alert alert-success mt-3';
                alertMessage.textContent = data.message;
                alertMessage.style.display = 'block';
                if (data.message === 'User created successfully') {
                    userCreateForm.reset();
                }
            })
            .catch(error => {
                alertMessage.className = 'alert alert-danger mt-3';
                alertMessage.textContent = 'An error occurred. Please try again.';
                alertMessage.style.display = 'block';
            });
        });
    }
});
