
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Thread, Event
import random
import time
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app)

connected_pods = {}
stop_event = Event()
waiting_for_touch = {}
DEFAULT_COLORS = ["red", "blue", "green", "yellow", "white", "orange", "pink", "black", "violet"]
SHAPES = ["circle", "square", "triangle", "star"]
NUMBERS = ["1", "2", "3", "4"]

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
def disconnect():
    if request.sid in connected_pods:
        del connected_pods[request.sid]
    emit("update", list(set(connected_pods.values())), broadcast=True)

@socketio.on("start_game")
def start_game(data):
    stop_event.clear()
    duration = int(data.get("duration", 1)) * 60
    interval = float(data.get("interval", 1))
    pause = float(data.get("pause", 1))
    mode = data.get("mode", "classic")
    random_timing = data.get("randomTiming", False)
    colors = data.get("colors", DEFAULT_COLORS)
    target_color = data.get("target_color", random.choice(colors))  # Get target color from data or random

    # Ensure that only selected colors are passed
    colors = [color for color in colors if color in data.get('colors', [])]

    def game_loop():
        for i in range(10, 0, -1):
            socketio.emit("countdown_tick", {"value": i})
            time.sleep(1)
        socketio.emit("countdown_tick", {"value": 0})

        current_round = 0
        while current_round < 5 and time.time() < (time.time() + duration):
            if stop_event.is_set():
                socketio.emit("blink", {"target": None})
                socketio.emit("game_stopped")
                return

            active_pods = list(set(connected_pods.values()))
            if not active_pods:
                break

            # Show different colors on all pods
            pod_colors = random.sample(colors, len(active_pods))  # Ensure different colors on each pod
            for i, pod in enumerate(active_pods):
                socketio.emit("blink", {"target": pod, "color": pod_colors[i]})
            waiting_for_touch.clear()

            # Wait for the user to touch the correct pod (with target_color)
            while not waiting_for_touch.get(target_color, False) and not stop_event.is_set():
                time.sleep(0.05)

            # Move to next round after successful touch
            current_round += 1
            target_color = random.choice(colors)  # Change to a new random target color after each round
            time.sleep(1)

        socketio.emit("game_finished")
        socketio.emit("game_stopped")

    Thread(target=game_loop).start()

@socketio.on("pod_touched")
def pod_touched(data):
    pod_id = data.get("pod_id")
    color = data.get("color")
    if color == data.get("target_color"):
        waiting_for_touch[color] = True

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    socketio.emit("blink", {"target": None})
    socketio.emit("game_stopped")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
