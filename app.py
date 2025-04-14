from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
from threading import Timer, Event
import random
import time
import os

app = Flask(__name__)
socketio = SocketIO(app)

connected_pods = {}  # sid -> pod_id
stop_event = Event()

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/pod/<pod_id>")
def pod(pod_id):
    return render_template("pod.html", pod_id=pod_id)

@socketio.on('register')
def register(data):
    pod_id = data.get('pod_id')
    connected_pods[request.sid] = pod_id
    emit('update', list(set(connected_pods.values())), broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    if request.sid in connected_pods:
        del connected_pods[request.sid]
    emit('update', list(set(connected_pods.values())), broadcast=True)

@socketio.on('start_game')
def start_game(data):
    stop_event.clear()
    duration = int(data.get("duration", 5)) * 60
    interval = int(data.get("interval", 3))

    socketio.emit('countdown', 20)

    def game_loop():
        end_time = time.time() + duration
        while time.time() < end_time:
            if stop_event.is_set():
                break
            active_pods = list(set(connected_pods.values()))
            if active_pods:
                target = random.choice(active_pods)
                socketio.emit('blink', {'target': target})
            time.sleep(interval)
        socketio.emit('blink', {'target': None})
        socketio.emit('game_stopped')

    Timer(20, game_loop).start()

@socketio.on('stop_game')
def stop_game():
    stop_event.set()
    socketio.emit('blink', {'target': None})
    socketio.emit('game_stopped')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
