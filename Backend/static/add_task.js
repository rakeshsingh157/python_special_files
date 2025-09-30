document.addEventListener('DOMContentLoaded', () => {
    // --- IST TIMEZONE UTILITIES ---
    const getISTDate = () => {
        const now = new Date();
        // Convert to IST (+5:30)
        const istOffset = 5.5 * 60 * 60 * 1000; // 5.5 hours in milliseconds
        const utc = now.getTime() + (now.getTimezoneOffset() * 60000); // UTC time
        return new Date(utc + istOffset);
    };

    // Set default date/time to current IST
    const istNow = getISTDate();
    const taskDateInput = document.getElementById('task-date');
    const taskTimeInput = document.getElementById('task-time');
    
    if (taskDateInput && !taskDateInput.value) {
        taskDateInput.value = istNow.toISOString().split('T')[0]; // YYYY-MM-DD
    }
    
    if (taskTimeInput && !taskTimeInput.value) {
        const hours = istNow.getHours().toString().padStart(2, '0');
        const minutes = istNow.getMinutes().toString().padStart(2, '0');
        taskTimeInput.value = `${hours}:${minutes}`;
    }

    const taskForm = document.getElementById('add-task-form');
    const messageEl = document.getElementById('form-message');

    if (taskForm) {
        taskForm.addEventListener('submit', async (event) => {
            event.preventDefault(); // Prevent the default browser page reload

            // Gather all form data
            const title = document.getElementById('task-title').value;
            const description = document.getElementById('task-description').value;
            const date = document.getElementById('task-date').value;
            const time = document.getElementById('task-time').value;
            const category = document.getElementById('task-category').value;
            const reminder_setting = document.getElementById('task-reminder').value;

            // Basic validation
            if (!title || !date || !time) {
                messageEl.textContent = 'Please fill out Title, Date, and Time.';
                messageEl.style.color = 'red';
                return;
            }

            // Create the data payload to send to the server
            const taskData = {
                title,
                description,
                date,
                time,
                category,
                reminder_setting
            };
            
            try {
                // Send the data to the backend API endpoint
                const response = await fetch('/api/tasks/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(taskData)
                });

                const result = await response.json();

                if (response.ok) {
                    messageEl.textContent = result.message;
                    messageEl.style.color = 'green';
                    
                    taskForm.reset();

                    // Redirect to the schedule page after a short delay
                    setTimeout(() => {
                        window.location.href = '/schedule';
                    }, 1500);

                } else {
                    throw new Error(result.error || 'An unknown error occurred.');
                }

            } catch (error) {
                messageEl.textContent = error.message;
                messageEl.style.color = 'red';
            }
        });
    }
});document.addEventListener('DOMContentLoaded', () => {
    // --- FORM Elements ---
    const taskForm = document.getElementById('add-task-form');
    const messageEl = document.getElementById('form-message');

    // --- CALENDAR Elements ---
    const calendarGrid = document.getElementById('calendar-grid');
    const currentMonthEl = document.getElementById('current-month');
    const calendarDateDisplay = document.getElementById('calendar-date-display');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const todayBtn = document.getElementById('today-btn');
    
    // --- GLOBAL STATE ---
    let calendarDate = new Date();
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

    // --- API HELPER ---
    const apiFetch = async (url) => {
        try {
            const response = await fetch(url);
            if (response.status === 401) {
                window.location.href = '/'; 
                return null;
            }
            if (!response.ok) {
                console.error("API request failed with status:", response.status, "for URL:", url);
                return null;
            }
            return response.json();
        } catch (error) {
            console.error("Network error during fetch:", error);
            return null;
        }
    };
    
    // --- FORM LOGIC ---
    const handleFormSubmit = async (event) => {
        event.preventDefault(); // Prevent the default browser page reload

        // Gather all form data
        const title = document.getElementById('task-title').value;
        const description = document.getElementById('task-description').value;
        const date = document.getElementById('task-date').value;
        const time = document.getElementById('task-time').value;
        const category = document.getElementById('task-category').value;
        const reminder_setting = document.getElementById('task-reminder').value;

        // Basic validation
        if (!title || !date || !time) {
            messageEl.textContent = 'Please fill out Title, Date, and Time.';
            messageEl.style.color = 'red';
            return;
        }

        const taskData = { title, description, date, time, category, reminder_setting };
        
        try {
            const response = await fetch('/api/tasks/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(taskData)
            });

            const result = await response.json();

            if (response.ok) {
                messageEl.textContent = result.message;
                messageEl.style.color = 'green';
                taskForm.reset();
                setTimeout(() => {
                    window.location.href = '/schedule'; // Redirect to schedule page after success
                }, 1500);

            } else {
                throw new Error(result.error || 'An unknown error occurred.');
            }

        } catch (error) {
            messageEl.textContent = error.message;
            messageEl.style.color = 'red';
        }
    };

    // --- CALENDAR LOGIC ---
    const renderCalendar = async () => {
        const year = calendarDate.getFullYear();
        const month = calendarDate.getMonth();
        const today = new Date();

        currentMonthEl.textContent = `${monthNames[month]} ${year}`;
        calendarDateDisplay.innerHTML = `<span class="month">${monthNames[today.getMonth()]}</span><span class="day-number">${today.getDate()}</span>`;
        
        const firstDayOfMonth = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        calendarGrid.innerHTML = '';
        ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].forEach(label => {
            calendarGrid.innerHTML += `<span class="day-label">${label}</span>`;
        });

        for (let i = 0; i < firstDayOfMonth; i++) {
            calendarGrid.innerHTML += `<span class="filler"></span>`;
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const isToday = (day === today.getDate() && month === today.getMonth() && year === today.getFullYear());
            calendarGrid.innerHTML += `<span class="day-cell ${isToday ? 'today' : ''}" data-day="${day}">${day}</span>`;
        }

        await fetchAndHighlightDays(year, month);
    };

    const fetchAndHighlightDays = async (year, month) => {
        const highlightData = await apiFetch(`/api/tasks/events/month_view?year=${year}&month=${month + 1}`);
        console.log('Add Task API Response for calendar:', highlightData); // Debugging line
        if (!highlightData) return;

        const dayCells = calendarGrid.querySelectorAll('.day-cell');
        dayCells.forEach(cell => {
            const day = parseInt(cell.dataset.day, 10);
            cell.classList.remove('has-both', 'has-pending', 'has-completed');
            if (highlightData.pending && highlightData.completed) {
                if (highlightData.pending.includes(day) && highlightData.completed.includes(day)) {
                    cell.classList.add('has-both');
                } else if (highlightData.pending.includes(day)) {
                    cell.classList.add('has-pending');
                } else if (highlightData.completed.includes(day)) {
                    cell.classList.add('has-completed');
                }
            } else if (Array.isArray(highlightData)) {
                if (highlightData.includes(day)) {
                    cell.classList.add('has-pending');
                }
            }
        });
    };

    // --- EVENT LISTENERS ---
    if (taskForm) {
        taskForm.addEventListener('submit', handleFormSubmit);
    }

    prevMonthBtn.addEventListener('click', () => {
        calendarDate.setMonth(calendarDate.getMonth() - 1);
        renderCalendar();
    });

    nextMonthBtn.addEventListener('click', () => {
        calendarDate.setMonth(calendarDate.getMonth() + 1);
        renderCalendar();
    });

    todayBtn.addEventListener('click', () => {
        calendarDate = new Date();
        renderCalendar();
    });

    // --- INITIAL LOAD ---
    renderCalendar();
});