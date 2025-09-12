// --- DOM Elements ---
const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');
const registerForm = document.getElementById('register-form');
const loginForm = document.getElementById('login-form');
const messageArea = document.getElementById('message-area');

// --- Form Toggle Logic ---
registerBtn.addEventListener('click', () => {
    container.classList.add('active');
    clearMessages();
});

loginBtn.addEventListener('click', () => {
    container.classList.remove('active');
    clearMessages();
});

// --- API Interaction Functions ---

function showMessage(message, isSuccess = true) {
    messageArea.textContent = message;
    messageArea.style.backgroundColor = isSuccess ? '#4CAF50' : '#f44336';
    messageArea.style.display = 'block';
}

function clearMessages() {
    messageArea.textContent = '';
    messageArea.style.display = 'none';
}

// --- Registration Form Submission ---
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault(); // Prevent default form submission
    clearMessages();

    const username = document.getElementById('reg-username').value;
    const email = document.getElementById('reg-email').value;
    const phone = document.getElementById('reg-phone').value;
    const password = document.getElementById('reg-password').value;

    const data = { username, email, phone, password };

    try {
        const response = await fetch('http://127.0.0.1:5000/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            showMessage(result.message, true);
            setTimeout(() => {
                container.classList.remove('active');
                clearMessages();
            }, 2000);
        } else {
            showMessage(result.message, false);
        }
    } catch (error) {
        console.error('Error during registration:', error);
        showMessage('An unexpected error occurred. Please try again later.', false);
    }
});

// --- Login Form Submission ---
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault(); // Prevent default form submission
    clearMessages();

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    const data = { email, password };

    try {
        const response = await fetch('http://127.0.0.1:5000/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            showMessage(result.message, true);
            // In a real application, you would handle the user's session here
            // For now, we'll just show a success message
        } else {
            showMessage(result.message, false);
        }
    } catch (error) {
        console.error('Error during login:', error);
        showMessage('An unexpected error occurred. Please try again later.', false);
    }
});
