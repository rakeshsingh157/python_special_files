// Global variables
let currentUser = {
    id: "705345137f6c"
};

let suggestedTasks = [];

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize user session
    initializeUserSession();
    
    // Initialize event listeners
    document.getElementById('ai-prompt-form').addEventListener('submit', handleGenerateTasks);
});

// Initialize user session
async function initializeUserSession() {
    try {
        const response = await fetch('http://localhost:5000/user_id', {
            credentials: 'include' // Include cookies for session
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentUser.id = data.user_id;
            document.getElementById('user-id-display').textContent = currentUser.id;
            console.log('User ID:', currentUser.id);
            loadUserTasks();
        } else {
            console.error('Error getting user ID:', data.error);
            // Fallback: generate a local user ID
            currentUser.id = 'user_' + Math.random().toString(36).substr(2, 9);
            document.getElementById('user-id-display').textContent = currentUser.id;
        }
    } catch (error) {
        console.error('Error initializing user session:', error);
        // Fallback: generate a local user ID
        currentUser.id = 'user_' + Math.random().toString(36).substr(2, 9);
        document.getElementById('user-id-display').textContent = currentUser.id;
    }
}

// Handle task generation form submission
async function handleGenerateTasks(e) {
    e.preventDefault();
    
    const promptInput = document.getElementById('ai-prompt');
    const userInput = promptInput.value.trim();
    
    if (!userInput) {
        alert('Please describe your goal or task');
        return;
    }
    
    // Show loading state
    const generateBtn = document.querySelector('.ai-generate-btn');
    const originalText = generateBtn.textContent;
    generateBtn.textContent = 'Generating...';
    generateBtn.disabled = true;
    
    try {
        const response = await fetch('http://localhost:5000/generate_tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_input: userInput
            }),
            credentials: 'include' // Include cookies for session
        });
        
        const data = await response.json();
        
        if (response.ok) {
            suggestedTasks = data.tasks;
            displaySuggestedTasks(suggestedTasks);
        } else {
            console.error('Error generating tasks:', data.error);
            alert('Failed to generate tasks. Please try again.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to connect to the server. Please try again.');
    } finally {
        // Restore button state
        generateBtn.textContent = originalText;
        generateBtn.disabled = false;
    }
}

// Display suggested tasks in the UI
function displaySuggestedTasks(tasks) {
    const taskListContainer = document.getElementById('ai-task-list');
    taskListContainer.innerHTML = '';
    
    if (tasks.length === 0) {
        taskListContainer.innerHTML = '<p>No tasks generated. Try a different description.</p>';
        return;
    }
    
    tasks.forEach((task, index) => {
        const taskCard = document.createElement('div');
        taskCard.className = 'task-card ai-task-card';
        taskCard.innerHTML = `
            <div class="task-content">
                <div class="task-icon-bg"><span class="task-icon">${getEmojiForCategory(task.category)}</span></div>
                <div class="task-details">
                    <h3 class="task-title">${task.title}</h3>
                    <p class="task-description">${task.description}</p>
                    <div class="task-meta-info">
                        <span class="task-date">${formatDate(task.date)}</span>
                        <span class="task-time">${task.time}</span>
                        <span class="task-category">${task.category}</span>
                        <span class="task-reminder">${task.reminder || '15 minutes'} before</span>
                    </div>
                </div>
            </div>
            <div class="task-meta">
                <select class="reminder-select" id="reminder-${index}">
                    <option value="15 minutes" ${(task.reminder === '15 minutes') ? 'selected' : ''}>15 min before</option>
                    <option value="30 minutes" ${(task.reminder === '30 minutes') ? 'selected' : ''}>30 min before</option>
                    <option value="1 hour" ${(task.reminder === '1 hour') ? 'selected' : ''}>1 hour before</option>
                    <option value="2 hours" ${(task.reminder === '2 hours') ? 'selected' : ''}>2 hours before</option>
                    <option value="1 day" ${(task.reminder === '1 day') ? 'selected' : ''}>1 day before</option>
                </select>
                <button class="add-to-schedule-btn" onclick="addTaskToSchedule(${index})">Add to Schedule</button>
            </div>
        `;
        
        taskListContainer.appendChild(taskCard);
    });
}

// Add task to schedule (database)
async function addTaskToSchedule(taskIndex) {
    const task = suggestedTasks[taskIndex];
    const reminderSelect = document.getElementById(`reminder-${taskIndex}`);
    const reminderSetting = reminderSelect.value;
    
    try {
        const response = await fetch('http://localhost:5000/add_task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: task.title,
                description: task.description,
                category: task.category,
                date: task.date,
                time: task.time,
                reminder_setting: reminderSetting
            }),
            credentials: 'include' // Include cookies for session
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Task added to your schedule successfully!');
            loadUserTasks(); // Refresh the task list
        } else {
            console.error('Error adding task:', data.error);
            alert('Failed to add task. Please try again.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to connect to the server. Please try again.');
    }
}

// Load user's tasks from the server
async function loadUserTasks() {
    try {
        const response = await fetch(`http://localhost:5000/get_tasks`, {
            credentials: 'include' // Include cookies for session
        });
        const data = await response.json();
        
        if (response.ok) {
            console.log('User tasks loaded:', data.tasks);
            // You could display these tasks in a separate section if needed
        } else {
            console.error('Error loading tasks:', data.error);
        }
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

function getEmojiForCategory(category) {
    const emojis = {
        'work': '💼', 'home': '🏠', 'sports': '⚽', 'fun': '🎉',
        'health': '🩺', 'fitness': '💪', 'personal': '👤', 'learning': '📚',
        'finance': '💰', 'errands': '🛒', 'cleaning': '🧹', 'gardening': '🌱',
        'cooking': '🍳', 'pets': '🐾', 'meeting': '🤝', 'commute': '🚗',
        'networking': '🔗', 'admin': '📝', 'social': '🥳', 'entertainment': '🍿',
        'travel': '✈', 'hobby': '🎨', 'volunteering': '❤', 'important': '❗',
        'to-do': '✅', 'later': '⏳', 'family': '👨‍👩‍👧‍👦'
    };
    
    return emojis[category.toLowerCase()] || '✅';
}

function formatDate(dateString) {
    // Use IST timezone formatting
    const options = { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'Asia/Kolkata' };
    return new Date(dateString).toLocaleDateString('en-IN', options);
}