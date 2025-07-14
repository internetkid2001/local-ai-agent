
document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');

    const state = {
        isRecording: false,
        timer: '00:00',
        seconds: 0,
        isVisible: true,
        askInput: '',
    };

    function render() {
        const html = `
            <div class="fixed top-6 right-6 z-50">
                <div class="bg-white/80 dark:bg-slate-900/80 backdrop-blur-lg rounded-2xl shadow-2xl border border-white/20 dark:border-slate-700/30 w-80">
                    <div class="flex items-center justify-between p-4 border-b border-gray-200/50 dark:border-slate-700/50">
                        <div class="flex items-center gap-3">
                            <div class="w-3 h-3 rounded-full ${state.isRecording ? 'bg-blue-500 animate-pulse' : 'bg-gray-300'}"></div>
                            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">${state.timer}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <button id="toggle-visibility" class="h-8 w-8 p-0 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                                ${state.isVisible ? '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>' : '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>'}
                            </button>
                            <button id="settings-button" class="h-8 w-8 p-0 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 0 2l-.15.08a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1 0-2l.15-.08a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
                            </button>
                            <button id="theme-toggle" class="h-8 w-8 p-0 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="M4.93 4.93l1.41 1.41"/><path d="M17.66 17.66l1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="M4.93 19.07l1.41-1.41"/><path d="M17.66 6.34l1.41-1.41"/></svg>
                            </button>
                        </div>
                    </div>
                    <div class="p-4 border-b border-gray-200/50 dark:border-slate-700/50">
                        <form id="ask-form" class="flex items-center gap-2">
                            <input id="ask-input" placeholder="Ask AI ⌘ ↵" value="${state.askInput}" class="flex-1 bg-gray-50/50 dark:bg-slate-800/50 border-gray-200/50 dark:border-slate-600/50 text-sm p-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                            <div class="text-xs text-gray-500 dark:text-gray-400">Show/Hide ⌘ ↑</div>
                        </form>
                    </div>
                    ${state.isVisible ? `
                    <div id="ai-response-area" class="p-4 min-h-[200px] overflow-y-auto">
                        <div class="flex items-start gap-3 mb-4">
                            <div class="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
                                <span class="text-white text-xs font-bold">AI</span>
                            </div>
                            <div class="text-sm text-gray-700 dark:text-gray-300">
                                <p class="font-medium mb-2">AI Response</p>
                                <div id="ai-response" class="text-gray-600 dark:text-gray-400">
                                    Hello! I'm your Local AI Agent. Ask me anything!
                                </div>
                            </div>
                        </div>
                    </div>
                    ` : ''}
                    <div class="p-4 flex items-center justify-center border-t border-gray-200/50 dark:border-slate-700/50">
                        <button id="toggle-recording" class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${state.isRecording ? 'bg-red-500 hover:bg-red-600' : 'bg-blue-500 hover:bg-blue-600'} text-white">
                            ${state.isRecording ? '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>' : '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>'}
                            ${state.isRecording ? 'Stop Listening' : 'Start Listening'}
                        </button>
                    </div>
                </div>
            </div>
        `;
        app.innerHTML = html;
        attachEventListeners();
    }

    function attachEventListeners() {
        document.getElementById('toggle-recording').addEventListener('click', toggleRecording);
        document.getElementById('toggle-visibility').addEventListener('click', toggleVisibility);
        document.getElementById('settings-button').addEventListener('click', handleSettingsClick);
        document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
        document.getElementById('ask-form').addEventListener('submit', handleAskSubmit);
        document.getElementById('ask-input').addEventListener('input', (e) => {
            state.askInput = e.target.value;
        });
    }

    function toggleRecording() {
        state.isRecording = !state.isRecording;
        if (state.isRecording) {
            state.seconds = 0;
            state.timer = '00:00';
            startTimer();
        } else {
            stopTimer();
        }
        render();
    }

    let timerInterval;
    function startTimer() {
        timerInterval = setInterval(() => {
            state.seconds++;
            const mins = Math.floor(state.seconds / 60);
            const secs = state.seconds % 60;
            state.timer = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            render();
        }, 1000);
    }

    function stopTimer() {
        clearInterval(timerInterval);
    }

    function toggleVisibility() {
        state.isVisible = !state.isVisible;
        render();
    }

    function handleSettingsClick() {
        alert("Settings button clicked!");
    }

    function toggleTheme() {
        document.documentElement.classList.toggle('dark');
    }

    async function handleAskSubmit(e) {
        e.preventDefault();
        const message = state.askInput.trim();
        if (!message) return;

        addMessage(message, 'You');
        state.askInput = '';
        render();

        const aiResponseEl = document.getElementById('ai-response');
        aiResponseEl.innerHTML = 'Thinking...'; // Use innerHTML for potential rich content

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            addMessage(data.response, 'AI Agent');

        } catch (error) {
            addMessage(`Error: ${error.message}`, 'AI Agent');
        }
    }

    function addMessage(content, sender) {
        const aiResponseArea = document.getElementById('ai-response-area');
        if (aiResponseArea) {
            const messageContainer = document.createElement('div');
            messageContainer.className = 'flex items-start gap-3 mb-4';

            const iconDiv = document.createElement('div');
            iconDiv.className = `w-6 h-6 rounded-full ${sender === 'AI Agent' ? 'bg-blue-500' : 'bg-gray-500'} flex items-center justify-center flex-shrink-0`;
            iconDiv.innerHTML = `<span class="text-white text-xs font-bold">${sender === 'AI Agent' ? 'AI' : 'You'}</span>`;

            const textContentDiv = document.createElement('div');
            textContentDiv.className = 'text-sm text-gray-700 dark:text-gray-300';
            
            let formattedContent = `<p class="font-medium mb-2">${sender}</p>`;
            if (sender === 'AI Agent') {
                // Attempt to parse content for structured display
                try {
                    const parsedContent = JSON.parse(content);
                    if (parsedContent.question && parsedContent.features) {
                        formattedContent += `<p class="text-gray-600 dark:text-gray-400 mb-3">${parsedContent.question}</p>`;
                        formattedContent += `<p class="font-medium text-gray-700 dark:text-gray-300 mb-2">Features:</p>`;
                        formattedContent += `<ol class="text-gray-600 dark:text-gray-400 space-y-1 text-xs">`;
                        parsedContent.features.forEach(feature => {
                            formattedContent += `<li><strong>${feature.title}:</strong> ${feature.description}</li>`;
                        });
                        formattedContent += `</ol>`;
                    } else {
                        formattedContent += `<p class="text-gray-600 dark:text-gray-400">${content}</p>`;
                    }
                } catch (e) {
                    formattedContent += `<p class="text-gray-600 dark:text-gray-400">${content}</p>`;
                }
            } else {
                formattedContent += `<p class="text-gray-600 dark:text-gray-400">${content}</p>`;
            }

            textContentDiv.innerHTML = formattedContent;

            messageContainer.appendChild(iconDiv);
            messageContainer.appendChild(textContentDiv);
            aiResponseArea.appendChild(messageContainer);
            aiResponseArea.scrollTop = aiResponseArea.scrollHeight;
        }
    }

    // Keyboard shortcut for Show/Hide
    document.addEventListener('keydown', (e) => {
        if (e.metaKey && e.key === 'ArrowUp') { // ⌘ ↑
            e.preventDefault();
            toggleVisibility();
        }
    });

    render();
});
