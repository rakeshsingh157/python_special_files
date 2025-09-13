document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    const loaderOverlay = document.getElementById('loader-overlay');
    const inviteBtn = document.getElementById('invite-btn');
    const requestsBtn = document.getElementById('requests-btn');
    const showMoreBtn = document.getElementById('show-more-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const inviteModal = document.getElementById('invite-modal');
    const requestsModal = document.getElementById('requests-modal');
    const assignTaskModal = document.getElementById('assign-task-modal');
    const requestsList = document.getElementById('requests-modal-list');
    const collaboratorsList = document.getElementById('collaborators-list');
    const projectList = document.getElementById('project-list');
    const myTasksBtn = document.getElementById('my-tasks-btn');
    const assignedTasksBtn = document.getElementById('assigned-tasks-btn');
    const calendarGrid = document.getElementById('calendar-grid');

    // --- Global state ---
    let allCollaborators = [];
    let isShowingAll = false;
    let calendarDate = new Date();

    // --- Loader Functions ---
    const showLoader = () => loaderOverlay.classList.remove('hidden');
    const hideLoader = () => loaderOverlay.classList.add('hidden');

    // --- Main Data Loading & API Fetch ---
    async function fetchAllData() {
        showLoader();
        try {
            await Promise.all([
                fetchRequests(),
                fetchCollaborators(),
                fetchAndRenderPersonalTasks()
            ]);
            renderCalendar();
        } catch (error) {
            console.error("An error occurred during initial data fetch:", error);
            alert("Could not load collaboration data. Please try refreshing the page.");
        } finally {
            hideLoader();
        }
    }

    const apiFetch = async (url, options = {}) => {
        const response = await fetch(url, options);
        if (response.status === 401) {
            window.location.href = '/';
            return null;
        }
        return response;
    };

    async function fetchRequests() {
        try {
            const response = await apiFetch('/api/collaboration/requests');
            if (!response) return;
            const requests = await response.json();
            renderRequests(requests);
        } catch (error) { console.error("Failed to fetch requests:", error); }
    }

    async function fetchCollaborators() {
        try {
            const response = await apiFetch('/api/collaborators');
            if (!response) return;
            allCollaborators = await response.json();
            renderCollaborators();
        } catch (error) { console.error("Failed to fetch collaborators:", error); }
    }

    async function fetchAndRenderPersonalTasks() {
        try {
            const response = await apiFetch('/api/tasks/personal');
            if (!response) return;
            const tasks = await response.json();
            renderTasks(tasks, 'personal');
        } catch (error) { console.error("Failed to fetch personal tasks:", error); }
    }

    async function fetchAndRenderAssignedTasks() {
        try {
            const response = await apiFetch('/api/tasks/assigned-by-me');
            if (!response) return;
            const tasks = await response.json();
            renderTasks(tasks, 'assigned');
        } catch (error) { console.error("Failed to fetch assigned tasks:", error); }
    }

    // --- Rendering Functions ---
    function renderRequests(requests) {
        requestsList.innerHTML = '';
        if (requests.length === 0) {
            requestsList.innerHTML = '<p style="text-align: center; color: var(--grey-text);">No pending requests.</p>';
        } else {
            requests.forEach(req => {
                const card = document.createElement('div');
                card.className = 'collaborator-card';
                card.innerHTML = `
                    <div class="collaborator-avatar-container"><img src="${req.photo_url || 'https://placehold.co/44x44/e7d6fb/a084e8?text=U'}" alt="Avatar" class="collaborator-avatar"></div>
                    <div class="collaborator-info"><div class="collaborator-name">${req.username}</div></div>
                    <div class="collaborator-card-actions">
                        <button class="action-btn accept" data-id="${req.id}">Accept</button>
                        <button class="action-btn decline" data-id="${req.id}">Decline</button>
                    </div>`;
                requestsList.appendChild(card);
            });
        }
    }

    function renderCollaborators() {
        collaboratorsList.innerHTML = '';
        const collaboratorsToShow = isShowingAll ? allCollaborators : allCollaborators.slice(0, 4);
        if (allCollaborators.length === 0) {
            collaboratorsList.innerHTML = '<p style="color: var(--grey-text);">You have no collaborators yet.</p>';
        } else {
            collaboratorsToShow.forEach(collab => {
                const card = document.createElement('div');
                card.className = 'collaborator-card';
                card.innerHTML = `
                    <div class="collaborator-avatar-container"><img src="${collab.photo_url || 'https://placehold.co/44x44/e7d6fb/a084e8?text=U'}" alt="Avatar" class="collaborator-avatar"></div>
                    <div class="collaborator-info">
                        <div class="collaborator-name">${collab.username}</div>
                        <div class="collaborator-role">${collab.profile_bio || 'Collaborator'}</div>
                    </div>
                    <div class="collaborator-card-actions">
                        <button class="assign-task-btn" data-id="${collab.user_id}" data-name="${collab.username}" title="Assign Task"><svg class="icon" viewBox="0 0 24 24"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg></button>
                        <button class="remove-collaborator-btn" data-id="${collab.user_id}" title="Remove Collaborator"><svg class="icon" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg></button>
                    </div>`;
                collaboratorsList.appendChild(card);
            });
        }
        if (allCollaborators.length > 4) {
            showMoreBtn.style.display = 'block';
            showMoreBtn.textContent = isShowingAll ? 'Show Less' : 'Show More';
        } else {
            showMoreBtn.style.display = 'none';
        }
    }
    
    function renderTasks(tasks, type) {
        projectList.innerHTML = '';
        if (tasks.length === 0) {
            projectList.innerHTML = `<p style="color: var(--grey-text);">No tasks to show.</p>`;
            return;
        }
        tasks.forEach(task => {
            const card = document.createElement('div');
            card.className = `project-card ${task.done ? 'done' : ''}`;
            card.dataset.taskId = task.id;
            const assignedInfo = type === 'assigned' ? `<span class="assigned-to">To: ${task.assignee_name}</span>` : '';
            const assignerInfo = (type === 'personal' && task.assigner_email) ? `<span class="task-assigner-info">From: ${task.assigner_email}</span>` : '';
            let actionButtons = '';
            if (type === 'personal') {
                actionButtons = `
                    <div class="task-actions">
                        <button class="task-action-btn toggle-done-btn" data-id="${task.id}" title="Toggle Done"><svg class="icon" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg></button>
                        <button class="task-action-btn delete-task-btn" data-id="${task.id}" title="Delete Task"><svg class="icon" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg></button>
                    </div>`;
            } else if (type === 'assigned') {
                 actionButtons = `
                    <div class="task-actions">
                        <button class="task-action-btn delete-task-btn" data-id="${task.id}" title="Delete Task"><svg class="icon" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg></button>
                    </div>`;
            }
            card.innerHTML = `
                ${actionButtons}
                <div class="project-header"><h3 class="project-title">${task.title}</h3></div>
                <p class="project-description">${task.description || 'No description.'}</p>
                <div class="project-meta">
                    <span class="task-date-info">Due: ${task.date} at ${task.time}</span>
                    ${assignedInfo}
                    ${assignerInfo}
                </div>`;
            projectList.appendChild(card);
        });
    }

    // --- Event Handlers & API Calls ---
    function setupEventListeners() {
        inviteBtn.addEventListener('click', () => inviteModal.style.display = 'flex');
        document.getElementById('cancel-invite').addEventListener('click', () => inviteModal.style.display = 'none');
        document.getElementById('send-invite').addEventListener('click', sendInvite);
        requestsBtn.addEventListener('click', () => requestsModal.style.display = 'flex');
        document.getElementById('close-requests-modal').addEventListener('click', () => requestsModal.style.display = 'none');
        document.getElementById('cancel-assign-task').addEventListener('click', () => assignTaskModal.style.display = 'none');
        document.getElementById('confirm-assign-task').addEventListener('click', confirmAssignTask);
        showMoreBtn.addEventListener('click', () => {
            isShowingAll = !isShowingAll;
            renderCollaborators();
        });

        document.body.addEventListener('click', async (e) => {
            const acceptBtn = e.target.closest('.action-btn.accept');
            if (acceptBtn) await respondToRequest(acceptBtn.dataset.id, 'accept');
            const declineBtn = e.target.closest('.action-btn.decline');
            if (declineBtn) await respondToRequest(declineBtn.dataset.id, 'decline');
            const assignBtn = e.target.closest('.assign-task-btn');
            if (assignBtn) openAssignTaskModal(assignBtn.dataset.id, assignBtn.dataset.name);
            const removeBtn = e.target.closest('.remove-collaborator-btn');
            if (removeBtn && confirm('Are you sure you want to remove this collaborator?')) await removeCollaborator(removeBtn.dataset.id);
            const toggleDoneBtn = e.target.closest('.toggle-done-btn');
            if (toggleDoneBtn) await toggleTaskDone(toggleDoneBtn.dataset.id);
            const deleteBtn = e.target.closest('.delete-task-btn');
            if (deleteBtn && confirm('Delete this task permanently?')) await deleteTask(deleteBtn.dataset.id);
        });
        
        myTasksBtn.addEventListener('click', () => {
            assignedTasksBtn.classList.remove('active');
            myTasksBtn.classList.add('active');
            fetchAndRenderPersonalTasks();
        });
        assignedTasksBtn.addEventListener('click', () => {
            myTasksBtn.classList.remove('active');
            assignedTasksBtn.classList.add('active');
            fetchAndRenderAssignedTasks();
        });
        logoutBtn.addEventListener('click', async () => {
            await fetch('/logout', { method: 'POST' });
            window.location.href = '/';
        });

        document.getElementById('prev-month').addEventListener('click', () => {
            calendarDate.setMonth(calendarDate.getMonth() - 1);
            renderCalendar();
        });
        document.getElementById('next-month').addEventListener('click', () => {
            calendarDate.setMonth(calendarDate.getMonth() + 1);
            renderCalendar();
        });
        document.getElementById('today-btn').addEventListener('click', () => {
            calendarDate = new Date();
            renderCalendar();
        });
    }

    async function sendInvite() {
        const email = document.getElementById('invite-email').value;
        const messageEl = document.getElementById('invite-modal-message');
        if (!email) {
            messageEl.textContent = 'Email is required.';
            messageEl.style.color = 'red';
            return;
        }
        messageEl.textContent = '';
        try {
            const response = await apiFetch('/api/collaboration/invite', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            messageEl.textContent = 'Invitation sent successfully!';
            messageEl.style.color = 'green';
            setTimeout(() => {
                inviteModal.style.display = 'none';
                messageEl.textContent = '';
                document.getElementById('invite-email').value = '';
            }, 2000);
        } catch (error) {
            messageEl.textContent = error.message;
            messageEl.style.color = 'red';
        }
    }

    async function respondToRequest(requestId, action) {
        try {
            const response = await apiFetch(`/api/collaboration/requests/${requestId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action })
            });
            if (!response.ok) throw new Error('Failed to respond');
            await fetchAllData();
        } catch (error) {
            console.error(error);
            alert('Could not respond to request.');
        }
    }

    async function removeCollaborator(collaboratorId) {
        try {
            const response = await apiFetch('/api/collaborator/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ collaborator_id: collaboratorId })
            });
            if (!response.ok) throw new Error('Failed to remove collaborator');
            await fetchCollaborators();
        } catch (error) {
            console.error(error);
            alert('Could not remove collaborator.');
        }
    }

    function openAssignTaskModal(assigneeId, assigneeName) {
        document.getElementById('assignee-name').textContent = assigneeName;
        assignTaskModal.dataset.assigneeId = assigneeId;
        document.getElementById('assign-task-form').reset();
        document.getElementById('assign-task-modal-message').textContent = '';
        assignTaskModal.style.display = 'flex';
    }

    // CORRECTED and FILLED IN this function
    async function confirmAssignTask() {
        const messageEl = document.getElementById('assign-task-modal-message');
        messageEl.textContent = '';
       
        const assigneeId = assignTaskModal.dataset.assigneeId;
        const title = document.getElementById('assign-task-title').value;
        const description = document.getElementById('assign-task-description').value;
        const category = document.getElementById('assign-task-category').value;
        const date = document.getElementById('assign-task-date').value;
        const time = document.getElementById('assign-task-time').value;

        if (!title || !category || !date || !time) {
            messageEl.textContent = 'Please fill in all required fields.';
            messageEl.style.color = 'red';
            return;
        }

        const taskData = {
            assignee_id: assigneeId,
            title,
            description,
            category,
            date,
            time
        };

        try {
            const response = await apiFetch('/api/task/create_and_assign', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(taskData)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'An unknown error occurred.');
            
            messageEl.textContent = 'Task Assigned Successfully!';
            messageEl.style.color = 'green';

            if (assignedTasksBtn.classList.contains('active')) {
                fetchAndRenderAssignedTasks();
            }

            setTimeout(() => {
                assignTaskModal.style.display = 'none';
            }, 2000);

        } catch (error) {
            messageEl.textContent = error.message;
            messageEl.style.color = 'red';
        }
    }

    async function toggleTaskDone(taskId) {
        try {
            const response = await apiFetch(`/api/task/${taskId}/toggle_done`, { method: 'POST' });
            if (!response.ok) throw new Error('Failed to update task');
            const card = document.querySelector(`.project-card[data-task-id='${taskId}']`);
            if (card) card.classList.toggle('done');
        } catch (error) {
            alert('Could not update task status.');
        }
    }

    async function deleteTask(taskId) {
        try {
            const response = await apiFetch(`/api/task/${taskId}`, { method: 'DELETE' });
            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || 'Failed to delete task');
            }
            const card = document.querySelector(`.project-card[data-task-id='${taskId}']`);
            if (card) card.remove();
        } catch (error) {
            alert(`Could not delete task: ${error.message}`);
        }
    }
    
    // --- Calendar Logic ---
    async function renderCalendar() {
        const year = calendarDate.getFullYear();
        const month = calendarDate.getMonth();
        const today = new Date();
        const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

        document.getElementById('current-month').textContent = `${monthNames[month]} ${year}`;
        document.getElementById('calendar-date-display').innerHTML = `<span class="month">${monthNames[today.getMonth()]}</span><span class="day-number">${today.getDate()}</span>`;

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
            const isToday = year === today.getFullYear() && month === today.getMonth() && day === today.getDate();
            calendarGrid.innerHTML += `<span class="day-cell ${isToday ? 'today' : ''}" data-day="${day}">${day}</span>`;
        }
        
        await fetchAndHighlightDays(year, month);
    }

    const fetchAndHighlightDays = async (year, month) => {
        console.log(`Collaboration: Fetching calendar data for ${year}-${month + 1}`);
        const response = await apiFetch(`/api/collaboration/events/month_view?year=${year}&month=${month + 1}`);
        let highlightData = null;
        if (response && response.ok) {
            highlightData = await response.json();
        }
        console.log('Collaboration API Response for calendar:', highlightData); // Debugging line
        if (!highlightData) {
            console.log('Collaboration: No highlight data received');
            return;
        }

        const dayCells = calendarGrid.querySelectorAll('.day-cell');
        console.log('Collaboration highlightData:', highlightData);
        console.log(`Collaboration: Found ${dayCells.length} day cells`);
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
    
    // --- Initial Load ---
    setupEventListeners();
    fetchAllData();
});