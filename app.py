
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
    colors = [c for c in data.get("colors", DEFAULT_COLORS) if c in DEFAULT_COLORS]

    def game_loop():
        for i in range(10, 0, -1):
            socketio.emit("countdown_tick", {"value": i})
            time.sleep(1)
        socketio.emit("countdown_tick", {"value": 0})

        end_time = time.time() + duration
        while time.time() < end_time and not stop_event.is_set():
            active_pods = list(set(connected_pods.values()))
            if not active_pods:
                break

            if mode == "fokus":
                target = random.choice(active_pods)
                blink_data = []
                for pod in active_pods:
                    color = "red" if pod == target else random.choice([c for c in colors if c != "red"])
                    blink_data.append((pod, color))
                for pod_id, color in blink_data:
                    socketio.emit("blink", {"target": pod_id, "color": color, "mode": "fokus"})
                waiting_for_touch[target] = True
                while waiting_for_touch.get(target, False) and not stop_event.is_set():
                    time.sleep(0.05)
                socketio.emit("blink", {"target": None})
                time.sleep(pause)
                continue

            # Fallback Classic
            target = random.choice(active_pods)
            color = random.choice(colors)
            socketio.emit("blink", {"target": target, "color": color, "mode": mode})
            time.sleep(interval)
            socketio.emit("blink", {"target": None})
            time.sleep(pause)

        socketio.emit("blink", {"target": None})
        socketio.emit("game_finished")
        time.sleep(1)
        socketio.emit("game_stopped")

    Thread(target=game_loop).start()

@socketio.on("pod_touched")
def pod_touched(data):
    pod_id = data.get("pod_id")
    waiting_for_touch[pod_id] = False

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    socketio.emit("blink", {"target": None})
    socketio.emit("game_stopped")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
