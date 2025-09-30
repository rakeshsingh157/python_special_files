document.addEventListener('DOMContentLoaded', () => {
    // --- ELEMENT SELECTORS ---
    const daySelector = document.getElementById('day-selector');
    const taskList = document.getElementById('task-list');
    const taskListTitle = document.getElementById('task-list-title');
    const completedToggle = document.getElementById('completed-toggle');
    const completedTaskList = document.getElementById('completed-task-list');
    const logoutBtn = document.getElementById('logout-btn');
    const calendarGrid = document.getElementById('calendar-grid');
    const currentMonthEl = document.getElementById('current-month');
    const calendarDateDisplay = document.getElementById('calendar-date-display');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const todayBtn = document.getElementById('today-btn');
    const stickySentinel = document.getElementById('sticky-sentinel');

    // --- GLOBAL STATE ---
    let allTasks = [];
    
    // --- IST TIMEZONE UTILITIES ---
    const getISTDate = () => {
        const now = new Date();
        // Convert to IST (+5:30)
        const istOffset = 5.5 * 60 * 60 * 1000; // 5.5 hours in milliseconds
        const utc = now.getTime() + (now.getTimezoneOffset() * 60000); // UTC time
        return new Date(utc + istOffset);
    };
    
    let selectedDate = getISTDate();
    let calendarDate = getISTDate();
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const icons = { 'work': '💼', 'home': '🏠', 'sports': '⚽', 'fun': '🎉', 'health': '🩺', 'fitness': '💪', 'personal': '👤', 'learning': '📚', 'finance': '💰', 'errands': '🛒', 'cleaning': '🧹', 'gardening': '🌱', 'cooking': '🍳', 'pets': '🐾', 'meeting': '🤝', 'commute': '🚗', 'networking': '🔗', 'admin': '📝', 'social': '🥳', 'entertainment': '🍿', 'travel': '✈️', 'hobby': '🎨', 'volunteering': '❤️', 'important': '❗️', 'to-do': '✅', 'later': '⏳', 'family': '👨‍👩‍👧‍👦' };

    // --- API HELPER ---
    const apiFetch = async (url, options = {}) => {
        try {
            const response = await fetch(url, options);
            if (response.status === 401) { window.location.href = '/'; return null; }
            if (!response.ok) { console.error("API error:", response.status); return null; }
            return response.json();
        } catch (error) { console.error("Network error:", error); return null; }
    };

    // --- DATE & TIME HELPERS ---
    const formatDate = (date) => {
        // Ensure we're working with IST date
        const istDate = date instanceof Date ? date : getISTDate();
        const year = istDate.getFullYear();
        const month = String(istDate.getMonth() + 1).padStart(2, '0');
        const day = String(istDate.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };
    const getDayName = (date, length = 'short') => {
        const istDate = date instanceof Date ? date : getISTDate();
        return istDate.toLocaleDateString('en-IN', { weekday: length, timeZone: 'Asia/Kolkata' });
    };

    // --- MAIN RENDER FUNCTION ---
    const renderPageContent = () => {
        renderDaySelector();
        renderTasksForSelectedDate();
        renderCompletedTasks();
        renderCalendar();
    };

    const renderDaySelector = () => {
        daySelector.innerHTML = '';
        const navPrev = document.createElement('span');
        navPrev.className = 'day-nav';
        navPrev.innerHTML = '←';
        navPrev.id = 'prev-week';
        daySelector.appendChild(navPrev);
        for (let i = -3; i <= 3; i++) {
            const date = new Date(selectedDate);
            date.setDate(date.getDate() + i);
            const dayItem = document.createElement('div');
            dayItem.className = 'day-item';
            dayItem.dataset.date = formatDate(date);
            dayItem.innerHTML = `<div class="day">${getDayName(date, 'short')}</div><div class="date">${date.getDate()}</div>`;
            if (i === 0) dayItem.classList.add('active');
            daySelector.appendChild(dayItem);
        }
        const navNext = document.createElement('span');
        navNext.className = 'day-nav';
        navNext.innerHTML = '→';
        navNext.id = 'next-week';
        daySelector.appendChild(navNext);
    };

    const renderTasksForSelectedDate = () => {
        const selectedDateStr = formatDate(selectedDate);
        const todayStr = formatDate(getISTDate());
        const pendingTasks = allTasks.filter(task => !task.done);

        if (selectedDateStr === todayStr) {
            taskListTitle.textContent = "Today's Tasks";
        } else {
            taskListTitle.textContent = `Tasks for ${getDayName(selectedDate, 'long')}, ${selectedDate.getDate()}`;
        }

        const selectedDayTasks = pendingTasks.filter(task => task.date === selectedDateStr);
        const otherTasks = pendingTasks.filter(task => task.date !== selectedDateStr);
        taskList.innerHTML = '';

        if (selectedDayTasks.length > 0) {
            taskListTitle.style.display = 'block';
            selectedDayTasks.forEach(task => taskList.appendChild(createTaskCard(task)));
        } else {
            taskListTitle.style.display = 'none';
        }

        if (otherTasks.length > 0) {
            if (selectedDayTasks.length > 0 || taskList.innerHTML === '') {
                const separator = document.createElement('h3');
                separator.className = 'section-title';
                separator.style.marginTop = '40px';
                separator.style.fontSize = '1.2rem';
                separator.textContent = 'Upcoming';
                taskList.appendChild(separator);
            }
            otherTasks.forEach(task => taskList.appendChild(createTaskCard(task)));
        }

        if (pendingTasks.length === 0) {
            taskList.innerHTML = '<p style="color: var(--grey-text); text-align: center;">You have no pending tasks. Great job!</p>';
        }

        taskList.appendChild(createAddTaskCard());
    };

    const renderCompletedTasks = () => {
        const completedTasks = allTasks.filter(task => task.done);
        completedTaskList.innerHTML = '';

        if (completedTasks.length === 0) {
            completedToggle.style.display = 'none';
        } else {
            completedToggle.style.display = 'flex';
            completedTasks.forEach(task => {
                completedTaskList.appendChild(createTaskCard(task));
            });
        }
    };

    const createTaskCard = (task) => {
        const card = document.createElement('div');
        card.className = `task-card ${task.done ? 'is-done' : ''}`;
        card.dataset.id = task.id;

        const doneButtonIcon = task.done
            ? `<svg class="icon" style="stroke: var(--purple-main); width:18px; height:18px; margin:0;" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>` // Undo Icon
            : `<svg class="icon" style="stroke: var(--success-green); width:18px; height:18px; margin:0;" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        const doneButtonTitle = task.done ? "Mark as Pending" : "Mark as Done";

        card.innerHTML = `
            <div class="task-content">
                <div class="task-icon-bg"><span class="task-icon">${icons[task.category.toLowerCase()] || '📌'}</span></div>
                <div class="task-details">
                    <h3 class="task-title">${task.title}</h3>
                    <p class="task-description">${task.description || ''}</p>
                </div>
            </div>
            <div class="task-footer">
                <div class="task-meta-details">
                    <div class="task-meta-item">
                        <svg class="icon" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                        <span>${task.date} at ${task.time}</span>
                    </div>
                </div>
                <div class="task-actions">
                     <button class="task-action-btn toggle-done-btn" title="${doneButtonTitle}">
                        ${doneButtonIcon}
                    </button>
                    <button class="task-action-btn delete-task-btn" title="Delete Task">
                        <svg class="icon" style="stroke: var(--danger-red);" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            </div>`;
        return card;
    };

    const createAddTaskCard = () => {
        const card = document.createElement('div');
        card.className = 'task-card add-task-sticky'; // We will style this class
        card.id = 'add-task-sticky-card';
        card.innerHTML = `<div class="task-content"><div class="task-icon-bg"><span class="task-icon">➕</span></div><div class="task-details"><h3 class="task-title">Add a New Task</h3><p class="task-description">Organize your schedule and stay productive.</p></div></div>`;
        card.onclick = () => window.location.href = '/add_event';
        return card;
    };

    // --- CALENDAR LOGIC ---
    const renderCalendar = async () => {
        const year = calendarDate.getFullYear();
        const month = calendarDate.getMonth();
        const today = getISTDate();
        currentMonthEl.textContent = `${monthNames[month]} ${year}`;
        calendarDateDisplay.innerHTML = `<span class="month">${monthNames[today.getMonth()]}</span><span class="day-number">${today.getDate()}</span>`;
        const firstDayOfMonth = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        calendarGrid.innerHTML = '';
        ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].forEach(label => calendarGrid.innerHTML += `<span class="day-label">${label}</span>`);
        for (let i = 0; i < firstDayOfMonth; i++) calendarGrid.innerHTML += `<span class="filler"></span>`;
        for (let day = 1; day <= daysInMonth; day++) {
            const isToday = (day === today.getDate() && month === today.getMonth() && year === today.getFullYear());
            calendarGrid.innerHTML += `<span class="day-cell ${isToday ? 'today' : ''}" data-day="${day}">${day}</span>`;
        }
        await fetchAndHighlightDays(year, month);
    };

    const fetchAndHighlightDays = async (year, month) => {
        const highlightData = await apiFetch(`/api/schedule/events/month_view?year=${year}&month=${month + 1}`);
        if (!highlightData) return;
        console.log('Schedule highlightData:', highlightData);
        const dayCells = calendarGrid.querySelectorAll('.day-cell');
        dayCells.forEach(cell => {
            const day = parseInt(cell.dataset.day, 10);
            cell.classList.remove('has-both', 'has-pending', 'has-completed');
            let isPending = false, isCompleted = false;
            if (highlightData && typeof highlightData === 'object' && !Array.isArray(highlightData)) {
                if (highlightData[day]) {
                    isPending = !!highlightData[day].hasPending;
                    isCompleted = !!highlightData[day].hasCompleted;
                }
            } else if (highlightData.pending && highlightData.completed) {
                isPending = highlightData.pending.includes(day);
                isCompleted = highlightData.completed.includes(day);
            } else if (Array.isArray(highlightData)) {
                isPending = highlightData.includes(day);
            }
            if (isPending && isCompleted) {
                cell.classList.add('has-both');
                console.log(`Day ${day}: has-both`);
            } else if (isPending) {
                cell.classList.add('has-pending');
                console.log(`Day ${day}: has-pending`);
            } else if (isCompleted) {
                cell.classList.add('has-completed');
                console.log(`Day ${day}: has-completed`);
            }
        });
    };

    // --- EVENT HANDLERS & ACTIONS ---
    daySelector.addEventListener('click', (e) => {
        const dayItem = e.target.closest('.day-item');
        if (dayItem) {
            selectedDate = new Date(dayItem.dataset.date + 'T00:00:00');
            renderDaySelector();
            renderTasksForSelectedDate();
        }
        if (e.target.id === 'prev-week') {
            selectedDate.setDate(selectedDate.getDate() - 7);
            renderDaySelector();
            renderTasksForSelectedDate();
        }
        if (e.target.id === 'next-week') {
            selectedDate.setDate(selectedDate.getDate() + 7);
            renderDaySelector();
            renderTasksForSelectedDate();
        }
    });

    const handleTaskAction = async (e) => {
        const taskId = e.target.closest('.task-card')?.dataset.id;
        if (!taskId) return;
        if (e.target.closest('.toggle-done-btn')) await toggleTaskDone(taskId);
        if (e.target.closest('.delete-task-btn')) {
            if (confirm('Are you sure you want to delete this task permanently?')) await deleteTask(taskId);
        }
    };
    taskList.addEventListener('click', handleTaskAction);
    completedTaskList.addEventListener('click', handleTaskAction);

    completedToggle.addEventListener('click', () => {
        completedToggle.classList.toggle('expanded');
        completedTaskList.classList.toggle('hidden');
    });

    const toggleTaskDone = async (taskId) => {
        const response = await apiFetch(`/api/task/${taskId}/toggle_done`, { method: 'POST' });
        if (response) await initializePage();
    };

    const deleteTask = async (taskId) => {
        const response = await apiFetch(`/api/task/${taskId}`, { method: 'DELETE' });
        if (response) {
            allTasks = allTasks.filter(task => task.id != taskId);
            renderPageContent();
        }
    };

    prevMonthBtn.addEventListener('click', () => { calendarDate.setMonth(calendarDate.getMonth() - 1); renderCalendar(); });
    nextMonthBtn.addEventListener('click', () => { calendarDate.setMonth(calendarDate.getMonth() + 1); renderCalendar(); });
    todayBtn.addEventListener('click', () => { calendarDate = getISTDate(); renderCalendar(); });
    if(logoutBtn) logoutBtn.addEventListener('click', async () => { await fetch('/logout', { method: 'POST' }); window.location.href = '/'; });

    // --- NEW SCROLL LOGIC FOR THE "ADD TASK" BUTTON ---
    window.addEventListener('scroll', () => {
        const addCard = document.getElementById('add-task-sticky-card');
        const isScrolledToTop = window.scrollY < 10; // Trigger when close to the top
        if (addCard) {
            if (isScrolledToTop) {
                addCard.classList.remove('is-sticky');
            } else {
                addCard.classList.add('is-sticky');
            }
        }
    });

    // --- INITIAL LOAD ---
    const initializePage = async () => {
        allTasks = await apiFetch('/api/tasks/all') || [];
        renderPageContent();
        // Immediately add the sticky class on load
        const addCard = document.getElementById('add-task-sticky-card');
        if (addCard) {
            addCard.classList.add('is-sticky');
        }
    };

    initializePage();
});