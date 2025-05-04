
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
reaktionsspiel_active = False
active_reaktionsspiel_pods = []
color_map = {}
target_pod_id = ""
score = {"points": 0}
current_target_color = "red"

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
    global score, current_target_color
    stop_event.clear()
    duration = int(data.get("duration", 1)) * 60
    interval = float(data.get("interval", 1))
    pause = float(data.get("pause", 1))
    mode = data.get("mode", "classic")
    random_timing = data.get("randomTiming", False)
    colors = data.get("colors", DEFAULT_COLORS)
    score = {"points": 0}
    current_target_color = data.get("targetColor", "red")

    def game_loop():
        global reaktionsspiel_active, active_reaktionsspiel_pods, color_map, target_pod_id

        for i in range(10, 0, -1):
            socketio.emit("countdown_tick", {"value": i})
            time.sleep(1)
        socketio.emit("countdown_tick", {"value": 0})

        end_time = time.time() + duration
        while time.time() < end_time:
            if stop_event.is_set():
                socketio.emit("blink", {"target": None})
                socketio.emit("game_stopped")
                return

            active_pods = list(set(connected_pods.values()))
            if not active_pods:
                break

            # Zielpod auswählen
            target_pod_id = random.choice(active_pods)
            distraction_colors = [c for c in colors if c != current_target_color]
            used_colors = random.sample(distraction_colors, len(active_pods) - 1)

            color_map = {}
            for pod_id in active_pods:
                if pod_id == target_pod_id:
                    color_map[pod_id] = current_target_color
                else:
                    color_map[pod_id] = used_colors.pop()

            for pod_id, color in color_map.items():
                socketio.emit("blink", {"target": pod_id, "color": color})

            # Spiel wartet auf Berührung
            reaktionsspiel_active = True
            waiting_for_touch[target_pod_id] = True
            while any(waiting_for_touch.get(pid, False) for pid in [target_pod_id]) and not stop_event.is_set():
                time.sleep(0.05)

            socketio.emit("blink", {"target": None})
            time.sleep(pause)

        reaktionsspiel_active = False
        socketio.emit("blink", {"target": None})
        socketio.emit("game_finished")
        time.sleep(1)
        socketio.emit("game_stopped")

    Thread(target=game_loop).start()

@socketio.on("pod_touched")
def pod_touched(data):
    pod_id = data.get("pod_id")
    waiting_for_touch[pod_id] = False

    if reaktionsspiel_active:
        if pod_id == target_pod_id:
            score["points"] += 1  # nur intern

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    socketio.emit("blink", {"target": None})
    socketio.emit("game_stopped")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
