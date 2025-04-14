from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Timer
import random
import time
import os

app = Flask(__name__)
socketio = SocketIO(app)

connected_pods = set()
all_pods = {"1", "2", "3", "4"}

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/pod/<pod_id>")
def pod(pod_id):
    return render_template("pod.html", pod_id=pod_id)

@socketio.on('register')
def register(data):
    pod_id = data.get('pod_id')
    connected_pods.add(pod_id)
    emit('update', list(connected_pods), broadcast=True)

@socketio.on('disconnect')
def disconnect():
    for pod_id in list(connected_pods):
        emit('update', list(connected_pods), broadcast=True)

@socketio.on('start_game')
def start_game():
    def game_loop():
        end_time = time.time() + 300  # 5 Minuten
        while time.time() < end_time:
            target = random.choice(list(all_pods))
            socketio.emit('blink', {'target': target})
            time.sleep(3)
        socketio.emit('blink', {'target': None})  # Stoppsignal

    socketio.emit('countdown', 20)
    Timer(20, game_loop).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
