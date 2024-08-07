document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    let username = "Anonymous";

    const usernameInput = document.getElementById('username-input');
    const setUsernameButton = document.getElementById('set-username-button');
    const chatContainer = document.getElementById('chat-container');
    const messagesDiv = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const imageInput = document.getElementById('image-input');
    const sendImageButton = document.getElementById('send-image-button');
    const modeToggle = document.getElementById('modeToggle');

    // Initialize mode based on saved preference or default to light mode
    const currentMode = localStorage.getItem('mode') || 'light-mode';
    document.body.classList.add(currentMode);
    if (currentMode === 'dark-mode') {
        modeToggle.checked = true;
    }

    // Handle dark mode toggle
    modeToggle.addEventListener('change', () => {
        if (modeToggle.checked) {
            document.body.classList.replace('light-mode', 'dark-mode');
            localStorage.setItem('mode', 'dark-mode');
        } else {
            document.body.classList.replace('dark-mode', 'light-mode');
            localStorage.setItem('mode', 'light-mode');
        }
    });

    setUsernameButton.onclick = () => {
        username = usernameInput.value || "Anonymous";
        socket.emit('username', username);
        document.getElementById('username-container').style.display = 'none';
        chatContainer.style.display = 'block';
    };

    const sendMessage = () => {
        const message = messageInput.value.trim();
        if (message !== "") {
            socket.emit('message', { username, message });
        } else {
            alert("Message cannot be empty.");
        }
        messageInput.value = '';  // Clear input field
    };

    sendButton.onclick = sendMessage;

    messageInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    sendImageButton.onclick = () => {
        const file = imageInput.files[0];
        if (file) {
            const formData = new FormData();
            formData.append('image', file);
            formData.append('username', username);

            fetch('/upload', {
                method: 'POST',
                body: formData,
            }).then(response => response.json()).then(data => {
                if (data.error) {
                    alert(data.error);  // Display error from the server
                } else {
                    console.log(data.message);
                }
            }).catch(error => {
                console.error('Error uploading image:', error);
            });

            imageInput.value = '';  // Clear file input
        }
    };

    socket.on('set_username', (data) => {
        username = data.username;
    });

    socket.on('message', (msgData) => {
        const messageElement = document.createElement('div');
        if (msgData.type === 'text') {
            messageElement.innerHTML = `
                <div class="message">
                    ${msgData.content} 
                    <span class="seen-count">(Seen by ${msgData.seen_by})</span>
                </div>`;
        } else if (msgData.type === 'image') {
            messageElement.innerHTML = `
                <div class="message">
                    ${msgData.content} 
                    <br><img src="${msgData.image_url}" class="chat-image">
                    <br><span class="seen-count">(Seen by ${msgData.seen_by})</span>
                </div>`;
        }
        messagesDiv.appendChild(messageElement);
        socket.emit('message_seen', messagesDiv.children.length - 1);
    });

    socket.on('update_seen', (data) => {
        const messageElement = messagesDiv.children[data.index];
        const seenCountElement = messageElement.querySelector('.seen-count');
        seenCountElement.textContent = `(Seen by ${data.seen_by})`;
    });

    socket.on('message_error', (data) => {
        alert(data.error);  // Display error messages from the server
    });
});
