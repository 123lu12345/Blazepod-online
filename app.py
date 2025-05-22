
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app)

connected_pods = set()

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/pod/<int:pod_id>')
def pod(pod_id):
    return render_template('pod.html', pod_id=pod_id)

@socketio.on('connect_pod')
def handle_connect_pod(data):
    pod_id = data.get('pod_id')
    if pod_id is not None:
        connected_pods.add(str(pod_id))
        emit('update', list(connected_pods), broadcast=True)
        print(f"[+] Pod {pod_id} verbunden.")

@socketio.on('disconnect')
def handle_disconnect():
    connected_pods.clear()
    emit('update', list(connected_pods), broadcast=True)
    print("[-] Alle Pods getrennt.")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
