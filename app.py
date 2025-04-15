
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app)

connected_pods = set()
required_pods = 4
countdown_thread = None
countdown_running = False

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/pod/<int:pod_id>')
def pod(pod_id):
    return render_template('pod.html', pod_id=pod_id)

@socketio.on('connect_pod')
def on_connect_pod(data):
    pod_id = data['pod_id']
    connected_pods.add(pod_id)
    emit('update_pods', list(connected_pods), broadcast=True)

@socketio.on('disconnect_pod')
def on_disconnect_pod(data):
    pod_id = data['pod_id']
    connected_pods.discard(pod_id)
    emit('update_pods', list(connected_pods), broadcast=True)

@socketio.on('update_required_pods')
def on_update_required_pods(data):
    global required_pods
    required_pods = data['required_pods']
    emit('required_pods_updated', required_pods, broadcast=True)

@socketio.on('start_game')
def on_start_game(data):
    global countdown_thread
    global countdown_running

    if countdown_thread and countdown_thread.is_alive():
        countdown_thread.cancel()

    countdown_thread = threading.Thread(target=start_countdown, args=(data,))
    countdown_running = True
    countdown_thread.start()

@socketio.on('stop_game')
def on_stop_game():
    global countdown_running
    countdown_running = False
    emit('game_stopped', broadcast=True)

def start_countdown(data):
    global countdown_running

    countdown = 10
    while countdown > 0 and countdown_running:
        socketio.emit('countdown', countdown)
        time.sleep(1)
        countdown -= 1

    if countdown_running:
        socketio.emit('countdown', 0)
        socketio.emit('game_started', data)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000, allow_unsafe_werkzeug=True)
