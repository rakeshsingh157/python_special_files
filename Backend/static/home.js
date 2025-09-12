document.addEventListener('DOMContentLoaded', () => {
    // --- ELEMENT SELECTORS ---
    const todayTaskList = document.getElementById('today-task-list');
    const calendarGrid = document.getElementById('calendar-grid');
    const currentMonthEl = document.getElementById('current-month');
    const calendarDateDisplay = document.getElementById('calendar-date-display');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const todayBtn = document.getElementById('today-btn');
    const logoutBtn = document.getElementById('logout-btn');

    // --- GLOBAL STATE ---
    let calendarDate = new Date();
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

    // --- API HELPER ---
    const apiFetch = async (url, options = {}) => {
        try {
            const response = await fetch(url, options);
            if (response.status === 401) {
                window.location.href = '/'; // Redirect to login on unauthorized
                return null;
            }
            return response;
        } catch (error) {
            console.error("Network error:", error);
            return null;
        }
    };

    // --- TASK RENDERING LOGIC ---
    const getTaskIcon = () => {
        const icons = ['🎨', '🏆', '🚀', '✨', '📚', '💼', '💡', '🎉', '📞', '💬'];
        return icons[Math.floor(Math.random() * icons.length)];
    };

    const fetchAndRenderTodayTasks = async () => {
        const response = await apiFetch('/api/tasks/today');
        if (!response || !response.ok) return;
        const tasks = await response.json();

        todayTaskList.innerHTML = ''; // Clear existing tasks

        if (tasks.length === 0) {
            todayTaskList.innerHTML = '<p style="color: var(--grey-text); text-align: center;">No tasks scheduled for today. Enjoy your day!</p>';
            return;
        }

        tasks.forEach(task => {
            const card = document.createElement('div');
            card.className = 'task-card';
            card.innerHTML = `
                <div class="task-content">
                    <div class="task-icon-bg"><span class="task-icon">${getTaskIcon()}</span></div>
                    <div class="task-details">
                        <h3 class="task-title">${task.title}</h3>
                        <p class="task-description">${task.description || 'No description provided.'}</p>
                    </div>
                </div>
                <div class="task-meta">
                    <span class="task-time">${task.time}</span>
                </div>
            `;
            todayTaskList.appendChild(card);
        });
    };

    // --- CALENDAR LOGIC ---
    const renderCalendar = async () => {
        const year = calendarDate.getFullYear();
        const month = calendarDate.getMonth(); // 0-indexed
        const today = new Date();

        // Update header and illustration
        currentMonthEl.textContent = `${monthNames[month]} ${year}`;
        calendarDateDisplay.innerHTML = `<span class="month">${monthNames[today.getMonth()]}</span><span class="day-number">${today.getDate()}</span>`;
        
        const firstDayOfMonth = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        calendarGrid.innerHTML = ''; // Clear previous grid
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
        // Fetch days with events for the current view (month is 1-indexed for API)
       
        const response = await apiFetch(`/api/events/month_view?year=${year}&month=${month + 1}`);
        let highlightData = null;
        if (response && response.ok) {
            highlightData = await response.json();
        }
        // Show debug output above the calendar
        let debugDiv = document.getElementById('calendar-debug');
        
        
       

        const dayCells = calendarGrid.querySelectorAll('.day-cell');
        console.log(`Home: Found ${dayCells.length} day cells`);
        dayCells.forEach(cell => {
            const day = parseInt(cell.dataset.day, 10);
            // Remove previous highlight classes
            cell.classList.remove('has-both', 'has-pending', 'has-completed');
            if (highlightData.pending && highlightData.completed) {
                // New API format with pending/completed arrays
                if (highlightData.pending.includes(day) && highlightData.completed.includes(day)) {
                    cell.classList.add('has-both'); // Both pending and completed
                } else if (highlightData.pending.includes(day)) {
                    cell.classList.add('has-pending'); // Not done: light color
                } else if (highlightData.completed.includes(day)) {
                    cell.classList.add('has-completed'); // Done: dark color
                }
            } else if (Array.isArray(highlightData)) {
                // Old API format with simple array
                if (highlightData.includes(day)) {
                    cell.classList.add('has-pending');
                }
            }
        });
    };

    // --- EVENT LISTENERS ---
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
    
    logoutBtn.addEventListener('click', async () => {
        await fetch('/logout', { method: 'POST' });
        window.location.href = '/';
    });

    // --- INITIAL LOAD ---
    const initializePage = () => {
        fetchAndRenderTodayTasks();
        renderCalendar();
    };

    initializePage();
});