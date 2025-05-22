
from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_pods = set()

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/pod/<int:pod_id>')
def pod(pod_id):
    return render_template('pod.html', pod_id=pod_id)

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/serviceWorker.js')
def service_worker():
    return send_from_directory('.', 'serviceWorker.js')

@socketio.on('connect')
def handle_connect():
    print(f"[INFO] Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"[INFO] Client disconnected: {request.sid}")
    connected_pods.discard(request.sid)
    emit('update_connected', list(connected_pods), broadcast=True)

@socketio.on('register_pod')
def handle_register_pod(data):
    pod_id = data.get('pod_id')
    if pod_id:
        print(f"[INFO] Pod {pod_id} registered with SID {request.sid}")
        connected_pods.add(pod_id)
        emit('update_connected', list(connected_pods), broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
