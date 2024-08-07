import os
import time
from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio = SocketIO(app)

# Tracking user cooldowns and profile pictures
user_last_message_time = {}
user_last_image_time = {}
user_profile_pictures = {}

# Cooldown durations
MESSAGE_COOLDOWN = 1  # 1 second
IMAGE_COOLDOWN = 180  # 3 minutes

messages = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    username = request.form.get('username', 'Anonymous')

    # Check image cooldown
    current_time = time.time()
    last_image_time = user_last_image_time.get(username, 0)
    if current_time - last_image_time < IMAGE_COOLDOWN:
        return jsonify({'error': 'You can only upload one image every 3 minutes.'}), 400

    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_url = f'/uploads/{filename}'
        new_message = {
            'type': 'image',
            'content': f'{username} sent an image:',
            'image_url': image_url,
            'seen_by': 0,
            'profile_picture_url': user_profile_pictures.get(username, 'default-profile.png')
        }
        messages.append(new_message)
        socketio.emit('message', new_message)  # Broadcast to all clients
        user_last_image_time[username] = current_time  # Update image cooldown time
        return jsonify({'message': 'File uploaded successfully'}), 200

@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    username = request.form.get('username', 'Anonymous')

    if 'profile_picture' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(f"profile_{username}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        profile_picture_url = f'/uploads/{filename}'
        user_profile_pictures[username] = profile_picture_url  # Save the profile picture URL
        return jsonify({'message': 'Profile picture uploaded successfully', 'profile_picture_url': profile_picture_url}), 200

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@socketio.on('username')
def handle_username(username):
    if not username:
        username = "Anonymous"
    profile_picture_url = user_profile_pictures.get(username, 'default-profile.png')
    emit('set_username', {'username': username, 'profile_picture_url': profile_picture_url})

@socketio.on('message')
def handle_message(data):
    username = data['username']
    current_time = time.time()

    # Check message cooldown
    last_message_time = user_last_message_time.get(username, 0)
    if current_time - last_message_time < MESSAGE_COOLDOWN:
        emit('message_error', {'error': 'You can only send a message once every second.'})
        return

    if 'message' in data:
        msg = data['message'].strip()  # Use .strip() instead of .trim()
        if msg:
            profile_picture_url = user_profile_pictures.get(username, 'default-profile.png')
            new_message = {
                'type': 'text',
                'content': f'{username}: {msg}',
                'profile_picture_url': profile_picture_url,
                'seen_by': 0
            }
            messages.append(new_message)
            socketio.emit('message', new_message)  # Broadcast to all clients
            user_last_message_time[username] = current_time  # Update message cooldown time
        else:
            emit('message_error', {'error': 'Message cannot be empty.'})

@socketio.on('message_seen')
def handle_message_seen(index):
    if 0 <= index < len(messages):
        messages[index]['seen_by'] += 1
        socketio.emit('update_seen', {'index': index, 'seen_by': messages[index]['seen_by']})  # Broadcast to all clients

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    socketio.run(app, debug=True)
