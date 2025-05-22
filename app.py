
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_pods = {}

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/pod/<int:pod_id>')
def pod(pod_id):
    return render_template('pod.html', pod_id=pod_id)

@socketio.on('connect_pod')
def handle_connect_pod(data):
    pod_id = data.get('pod_id')
    if pod_id:
        connected_pods[pod_id] = request.sid
        print(f"[INFO] Pod {pod_id} verbunden.")
        emit('update_pod_status', {'connected_pods': list(connected_pods.keys())}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    for pod_id, sid in list(connected_pods.items()):
        if sid == request.sid:
            print(f"[INFO] Pod {pod_id} getrennt.")
            del connected_pods[pod_id]
            break
    emit('update_pod_status', {'connected_pods': list(connected_pods.keys())}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
