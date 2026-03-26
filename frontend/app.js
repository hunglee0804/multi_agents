const API_BASE_URL = 'http://127.0.0.1:8000/backend-api';

// ==========================================
// 1. LOGIC TRANG ĐĂNG NHẬP (index.html)
// ==========================================
const authForm = document.getElementById('auth-form');
if (authForm) {
    authForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const messageDiv = document.getElementById('auth-message');
        const btn = document.getElementById('auth-btn');

        btn.disabled = true;
        messageDiv.innerText = 'Đang kết nối tới server...';

        try {
            if (isLoginMode) {
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
                    window.location.href = 'chat.html';
                } else {
                    messageDiv.innerText = data.detail || 'Sai email hoặc mật khẩu!';
                }
            } else {
                const res = await fetch(`${API_BASE_URL}/auth/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email, password: password })
                });

                const data = await res.json();
                if (res.ok) {
                    messageDiv.style.color = 'var(--accent-color)';
                    messageDiv.innerText = 'Đăng ký thành công! Đang chuyển sang đăng nhập...';
                    setTimeout(() => toggleAuthMode(), 1500);
                } else {
                    messageDiv.innerText = data.detail || 'Lỗi đăng ký!';
                }
            }
        } catch (err) {
            messageDiv.innerText = 'Không thể kết nối tới server.';
        } finally {
            btn.disabled = false;
        }
    });
}

// ==========================================
// 2. LOGIC TRANG CHAT (chat.html)
// ==========================================
let currentConversationId = null;

if (window.location.pathname.includes('chat.html')) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html'; 
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
    if (response.status === 401) logout();
    return response;
}

async function loadConversations() {
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/conversations?skip=0&limit=20`);
        if (res.ok) {
            const convs = await res.json();
            const list = document.getElementById('conversation-list');
            list.innerHTML = '';
            convs.forEach(c => {
                const div = document.createElement('div');
                div.className = 'conv-item';
                div.innerText = c.title;
                div.onclick = () => loadConversationDetail(c.id, div);
                list.appendChild(div);
            });
        }
    } catch (err) {
        console.error("Lỗi tải danh sách:", err);
    }
}

function startNewChat() {
    currentConversationId = null;
    document.getElementById('chat-history').innerHTML = `
        <div class="welcome-message">
            <h2>Xin chào Ke,</h2>
            <p>Tôi có thể hỗ trợ gì cho hệ thống multi-agents của bạn hôm nay?</p>
        </div>
    `;
    document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
    document.getElementById('current-chat-title').innerText = 'FPT AI Assistant';
}

async function loadConversationDetail(id, element) {
    currentConversationId = id;
    
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
        console.error("Lỗi tải chi tiết:", err);
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

    const welcome = document.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    appendMessage('user', text);
    scrollToBottom();

    // Lưu lại ID của dòng loading
    const loadingId = appendMessage('assistant', '<i class="fas fa-circle-notch fa-spin"></i> Các Agent đang xử lý...');
    scrollToBottom();

    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/f/conversation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversation_id: currentConversationId,
                message: text
            })
        });

        const data = await res.json();
        if (res.ok) {
            if (!currentConversationId) {
                currentConversationId = data.conversation_id;
                loadConversations(); 
            }
            updateMessage(loadingId, data.response);
        } else {
            updateMessage(loadingId, "Xin lỗi, đã xảy ra lỗi từ hệ thống API.");
        }
    } catch (err) {
        updateMessage(loadingId, "Không thể kết nối tới server FastAPI.");
    } finally {
        sendBtn.disabled = false;
        scrollToBottom();
    }
}

// --- UI Helpers ---

// Hàm xử lý định dạng text (xuống dòng và in đậm)
function formatText(text) {
    let formatted = text.replace(/\n/g, '<br>');
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    return formatted;
}

function appendMessage(role, content) {
    const history = document.getElementById('chat-history');
    const div = document.createElement('div');
    
    // FIX BUG ID: Thêm Math.random() để đảm bảo id luôn luôn khác nhau
    const id = 'msg-' + Date.now() + '-' + Math.floor(Math.random() * 10000);
    div.id = id;
    div.className = `message ${role}`;
    
    // Giao diện có Avatar giống Gemini
    if (role === 'assistant') {
        div.innerHTML = `
            <div class="avatar ai-avatar"><i class="fas fa-robot"></i></div>
            <div class="msg-content">${formatText(content)}</div>
        `;
    } else {
        div.innerHTML = `
            <div class="msg-content">${formatText(content)}</div>
        `;
    }
    
    history.appendChild(div);
    return id;
}

function updateMessage(id, content) {
    const div = document.getElementById(id);
    if (div) {
        const contentDiv = div.querySelector('.msg-content');
        if (contentDiv) {
            contentDiv.innerHTML = formatText(content);
        }
    }
}

function scrollToBottom() {
    const history = document.getElementById('chat-history');
    history.scrollTop = history.scrollHeight;
}