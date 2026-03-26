const API_BASE_URL = 'http://127.0.0.1:8000/backend-api';
let isLoginMode = true;

// --- AUTH PAGE LOGIC (index.html) ---
const authForm = document.getElementById('auth-form');
if (authForm) {
    authForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const messageDiv = document.getElementById('auth-message');
        const btn = document.getElementById('auth-btn');

        btn.disabled = true;
        messageDiv.innerText = 'Connecting...';

        try {
            if (isLoginMode) {
                // LOGIN
                const formData = new URLSearchParams();
                formData.append('username', email); 
                formData.append('password', password);

                const res = await fetch(`${API_BASE_URL}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: formData.toString()
                });

                const data = await res.json();
                if (res.ok) {
                    localStorage.setItem('token', data.access_token);
                    window.location.href = 'chat.html'; // Chuyển sang chat
                } else {
                    messageDiv.innerText = data.detail || 'Wrong email or password!';
                }
            } else {
                // REGISTER
                const res = await fetch(`${API_BASE_URL}/auth/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email, password: password })
                });

                const data = await res.json();
                if (res.ok) {
                    messageDiv.style.color = 'var(--accent-color)';
                    messageDiv.innerText = 'Registered successfully! Switching to login...';
                    setTimeout(() => toggleAuthMode(), 1500);
                } else {
                    messageDiv.innerText = data.detail || 'Registration failed!';
                }
            }
        } catch (err) {
            messageDiv.innerText = 'Could not connect to the server.';
        } finally {
            btn.disabled = false;
        }
    });
}

function toggleAuthMode() {
    isLoginMode = !isLoginMode;
    document.getElementById('auth-title').innerText = isLoginMode ? 'Log in' : 'Register an Account';
    document.getElementById('auth-btn').innerText = isLoginMode ? 'Log in' : 'Register';
    document.getElementById('toggle-text').innerHTML = isLoginMode 
        ? 'Don not have an account yet? <span onclick="toggleAuthMode()">Register now</span>' 
        : 'Already have an account? <span onclick="toggleAuthMode()">Log in</span>';
    document.getElementById('auth-message').innerText = '';
}

// --- CHAT PAGE LOGIC (chat.html) ---
let currentConversationId = null;

if (window.location.pathname.includes('chat.html')) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html'; // redirect if not logged in
    } else {
        loadConversations();
    }
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = 'index.html';
}

async function fetchWithAuth(url, options = {}) {
    const token = localStorage.getItem('token');
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
    };
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) logout(); // if unauthorized, logout
    return response;
}

async function loadConversations() {
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/conversations?skip=0&limit=20`);
        if (res.ok) {
            const convs = await res.json();
            const list = document.getElementById('conversation-list');
            
            // Keep the header "Saved conversations"
            const header = list.querySelector('h4');
            list.innerHTML = '';
            if (header) list.appendChild(header);

            convs.forEach(c => {
                const div = document.createElement('div');
                div.className = 'conv-item';
                
                // Phần tiêu đề (Click vào để xem chat)
                const titleSpan = document.createElement('span');
                titleSpan.className = 'conv-title';
                titleSpan.innerText = c.title;
                titleSpan.onclick = () => loadConversationDetail(c.id, div);
                
                // Nút Xóa (Icon thùng rác)
                const delBtn = document.createElement('button');
                delBtn.className = 'delete-btn';
                delBtn.innerHTML = '<i class="fas fa-trash"></i>';
                delBtn.onclick = (e) => deleteConversation(c.id, e); // Gọi hàm xóa
                
                div.appendChild(titleSpan);
                div.appendChild(delBtn);
                list.appendChild(div);
            });
        }
    } catch (err) {
        console.error("Error loading conversations:", err);
    }
}

function startNewChat() {
    currentConversationId = null;
    document.getElementById('chat-history').innerHTML = `
        <div class="welcome-message">
            <h2>Hello</h2>
            <p>I am a multi-system integrated AI support. How can I assist with what you are doing today?</p>
        </div>
    `;
    document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
    document.getElementById('current-chat-title').innerText = 'FPT AI Assistant';
}

async function loadConversationDetail(id, element) {
    currentConversationId = id;
    
    // update active state in sidebar
    document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
    if(element) element.classList.add('active');

    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/conversation/${id}`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById('current-chat-title').innerText = data.title;
            
            const history = document.getElementById('chat-history');
            history.innerHTML = '';
            
            data.messages.forEach(msg => {
                appendMessage(msg.role, msg.content);
            });
            scrollToBottom();
        }
    } catch (err) {
        console.error("Error loading conversation detail:", err);
    }
}

async function deleteConversation(id, event) {
    // Ngăn sự kiện click lan truyền sang việc load lịch sử chat
    event.stopPropagation(); 
    
    if (!confirm("Are you sure to delete this chat?")) return;

    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/conversation/${id}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            // Nếu đoạn chat đang mở bị xóa, reset lại khung chat chính
            if (currentConversationId === id) {
                startNewChat();
            }
            loadConversations(); // Tải lại Sidebar
        } else {
            alert("Error: Cannot delete chat.");
        }
    } catch (err) {
        console.error("Error when deleting:", err);
    }
}

async function sendMessage(e) {
    e.preventDefault();
    const input = document.getElementById('message-input');
    const text = input.value.trim();
    if (!text) return;

    const sendBtn = document.getElementById('send-btn');
    input.value = '';
    sendBtn.disabled = true;

    // 1. remove welcome message if present
    const welcome = document.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    // 2. append user message instantly
    appendMessage('user', text);
    scrollToBottom();

    // 3. THÊM ĐIỀU CHỈNH TẠI ĐÂY: Hiển thị tin nhắn "Loading" tạm thời
    // Chúng ta tạo ra một tin nhắn mới có icon xoay và lưu lại DOM element của nó
    const loadingMessageId = 'loading-' + Date.now();
    appendMessage('assistant', `<i class="fas fa-spinner loading-spinner"></i> <span class="loading-text">Agent is executing...</span>`, loadingMessageId);
    scrollToBottom();

    try {
        // 4. Gọi API gửi tin nhắn
        const res = await fetchWithAuth(`${API_BASE_URL}/f/conversation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversation_id: currentConversationId,
                message: text
            })
        });

        const data = await res.json();

        // 5. THÊM ĐIỀU CHỈNH TẠI ĐÂY: Thay thế nội dung Loading bằng kết quả thực tế
        const loadingMessageElement = document.getElementById(loadingMessageId);
        if (loadingMessageElement) {
            const contentDiv = loadingMessageElement.querySelector('.msg-content');
            if (res.ok) {
                if (!currentConversationId) {
                    currentConversationId = data.conversation_id;
                    loadConversations(); // Reload sidebar
                }
                // Thay thế icon spinner bằng nội dung AI trả về
                contentDiv.innerHTML = data.response.replace(/\n/g, '<br>');
            } else {
                contentDiv.innerHTML = "Xin lỗi, đã xảy ra lỗi từ hệ thống API.";
            }
        }
        
    } catch (err) {
        // Xử lý lỗi kết nối
        const loadingMessageElement = document.getElementById(loadingMessageId);
        if (loadingMessageElement) {
            loadingMessageElement.querySelector('.msg-content').innerHTML = "Unable to connect to the FastAPI server.";
        }
    } finally {
        sendBtn.disabled = false;
        scrollToBottom();
    }
}

// Cập nhật hàm appendMessage để hỗ trợ custom ID (tham số thứ 3)
function appendMessage(role, content, customId = null) {
    const history = document.getElementById('chat-history');
    const div = document.createElement('div');
    div.className = `message ${role}`;
    
    // Nếu có truyền customId (như 'loading-...'), thì dùng nó,
    // nếu không, tự sinh một ID tạm (cho tin nhắn cũ/user)
    div.id = customId || ('msg-' + Date.now());
    
    // Add Avatar for AI
    if (role === 'assistant') {
        div.innerHTML = `
            <div class="avatar ai-avatar"><i class="fas fa-robot"></i></div>
            <div class="msg-content">${content.replace(/\n/g, '<br>')}</div>
        `;
    } else {
        // User messages don't have avatar
        div.innerHTML = `
            <div class="msg-content">${content.replace(/\n/g, '<br>')}</div>
        `;
    }
    
    history.appendChild(div);
}

function scrollToBottom() {
    const history = document.getElementById('chat-history');
    history.scrollTop = history.scrollHeight;
}