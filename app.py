
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_pods = {}

@app.route("/")
def index():
    return "Dashboard läuft"

@app.route("/pod/<int:pod_id>")
def pod(pod_id):
    return f"Pod {pod_id} verbunden"

@socketio.on('connect')
def handle_connect():
    print(f"✅ Verbindung hergestellt: {request.sid}")

@socketio.on('register_pod')
def register_pod(data):
    pod_id = data.get('pod_id')
    if pod_id is not None:
        connected_pods[pod_id] = request.sid
        print(f"🔌 Pod {pod_id} registriert mit SID {request.sid}")
        emit('pod_registered', {'pod_id': pod_id}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    for pod_id, sid in list(connected_pods.items()):
        if sid == request.sid:
            print(f"❌ Pod {pod_id} getrennt")
            del connected_pods[pod_id]

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
