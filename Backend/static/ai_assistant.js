document.addEventListener('DOMContentLoaded', () => {
    // --- CHAT Elements ---
    const chatWindow = document.getElementById('ai-chat-window');
    const inputTextArea = document.getElementById('ai-input-textarea');
    const sendButton = document.getElementById('ai-send-btn');
    const logoutBtn = document.getElementById('logout-btn');

    // --- CALENDAR Elements ---
    const calendarGrid = document.getElementById('calendar-grid');
    let calendarDate = new Date();

    // --- Chat Logic ---
    const sendMessage = async () => {
        const message = inputTextArea.value.trim();
        if (!message) return;

        inputTextArea.value = '';
        inputTextArea.disabled = true;
        sendButton.disabled = true;

        appendMessage(message, 'outgoing');

        const typingIndicator = appendMessage('...', 'incoming', true);

        try {
            const response = await fetch('/api/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message }),
            });

            typingIndicator.remove();

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'An error occurred.');
            }

            const data = await response.json();
            appendMessage(data.reply, 'incoming');

        } catch (error) {
            appendMessage(`Error: ${error.message}`, 'incoming', false, true);
        } finally {
            inputTextArea.disabled = false;
            sendButton.disabled = false;
            inputTextArea.focus();
        }
    };

    const appendMessage = (text, type, isTyping = false, isError = false) => {
        const messageBubble = document.createElement('div');
        messageBubble.classList.add(type === 'outgoing' ? 'user-message-bubble' : 'ai-message-bubble');
        messageBubble.classList.add(type);

        if (isTyping) {
            messageBubble.innerHTML = `<div class="typing-indicator"><span></span><span></span><span></span></div>`;
        } else {
            // Convert markdown to HTML for better formatting
            const htmlContent = convertMarkdownToHtml(text);
            messageBubble.innerHTML = htmlContent;
        }

        if (isError) {
            messageBubble.style.backgroundColor = '#ffdddd';
            messageBubble.style.color = '#d8000c';
        }

        chatWindow.appendChild(messageBubble);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        return messageBubble;
    };

    // Function to convert basic markdown to HTML
    const convertMarkdownToHtml = (text) => {
        let html = text;
        
        // Convert **bold** to <strong>
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert *italic* to <em>
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Convert `code` to <code>
        html = html.replace(/`(.*?)`/g, '<code>$1</code>');
        
        // Convert line breaks
        html = html.replace(/\\n\\n/g, '<br><br>');
        html = html.replace(/\\n/g, '<br>');
        html = html.replace(/\n\n/g, '<br><br>');
        html = html.replace(/\n/g, '<br>');
        
        // Convert bullet points (- or *)
        html = html.replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        
        // Convert numbered lists
        html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
        
        // Handle emojis and preserve spacing
        html = html.replace(/  /g, '&nbsp;&nbsp;');
        
        return html;
    };
    
    // --- Calendar Logic ---
    const renderCalendar = () => {
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
            calendarGrid.innerHTML += `<span class="day-cell ${isToday ? 'today' : ''}">${day}</span>`;
        }
    };

    // --- Initial Setup ---
    const setupEventListeners = () => {
        // Chat listeners
        inputTextArea.addEventListener('input', () => {
            inputTextArea.style.height = 'auto';
            inputTextArea.style.height = `${inputTextArea.scrollHeight}px`;
        });
        sendButton.addEventListener('click', sendMessage);
        inputTextArea.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        });
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async () => {
                await fetch('/logout', { method: 'POST' });
                window.location.href = '/';
            });
        }
        
        // Calendar listeners
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
    };

    // --- Dynamic Styles for Typing Indicator ---
    const style = document.createElement('style');
    style.innerHTML = `
        .typing-indicator span {
            height: 8px;
            width: 8px;
            background-color: var(--dark-text);
            border-radius: 50%;
            display: inline-block;
            animation: bounce 1.4s infinite ease-in-out both;
        }
        .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1.0); }
        }
    `;
    document.head.appendChild(style);

    // --- Initial Load ---
    setupEventListeners();
    renderCalendar();
});