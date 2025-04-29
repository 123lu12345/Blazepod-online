
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Thread, Event
import random
import time
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app)

connected_pods = {}  # sid -> pod_id
stop_event = Event()
waiting_for_touch = {}  # pod_id -> waiting state
COLORS = ["red", "blue", "green", "yellow"]

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/pod/<pod_id>")
def pod(pod_id):
    return render_template("pod.html", pod_id=pod_id)

@socketio.on("register")
def register(data):
    pod_id = data.get("pod_id")
    connected_pods[request.sid] = pod_id
    emit("update", list(set(connected_pods.values())), broadcast=True)

@socketio.on("disconnect")
def on_disconnect():
    if request.sid in connected_pods:
        del connected_pods[request.sid]
    emit("update", list(set(connected_pods.values())), broadcast=True)

@socketio.on("start_game")
def start_game(data):
    stop_event.clear()
    mode = data.get("mode", "classic")

    def game_loop():
        active_pods = list(set(connected_pods.values()))
        if not active_pods:
            return

        while not stop_event.is_set():
            target = random.choice(active_pods)

            color = "red"
            if mode in ["multicolor", "touch-switch-multicolor"]:
                color = random.choice(COLORS)

            socketio.emit("blink", {"target": target, "color": color})

            if mode in ["touch-switch", "touch-switch-multicolor"]:
                waiting_for_touch[target] = True
                while waiting_for_touch.get(target, False) and not stop_event.is_set():
                    time.sleep(0.05)
            else:
                time.sleep(2)  # Classic Modes delay

            socketio.emit("blink", {"target": None})
            time.sleep(0.5)  # Black screen pause

    Thread(target=game_loop).start()

@socketio.on("pod_touched")
def pod_touched(data):
    pod_id = data.get("pod_id")
    waiting_for_touch[pod_id] = False

@socketio.on("stop_game")
def stop_game():
    stop_event.set()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
