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
DEFAULT_COLORS = ["red", "blue", "green", "yellow", "white", "orange", "pink", "gray", "violet"]

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
    target_color = data.get("targetColor", "red")
    stop_event.clear()
    duration = int(data.get("duration", 1)) * 60
    interval = float(data.get("interval", 1))
    pause = float(data.get("pause", 1))
    mode = data.get("mode", "classic")
    colors = data.get("colors", DEFAULT_COLORS)

    def game_loop():
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

            if mode == "focus":
                active_pods = [p for p in connected_pods.values() if p]
                if not active_pods:
                    break
                target_pod = random.choice(active_pods)
                # 1. Zielpod zuerst senden
                socketio.emit("blink", {"target": target_pod, "color": target_color, "mode": mode})
                # 2. Andere Pods erhalten andere Farben (nicht Zielpod!)
                other_pods = [p for p in active_pods if p != target_pod]
                distractor_colors = [c for c in colors if c != target_color]
                for pod in other_pods:
                    color = random.choice(distractor_colors) if distractor_colors else "gray"
                    socketio.emit("blink", {"target": pod, "color": color, "mode": mode})
                waiting_for_touch["focus_allowed"] = target_pod
                while waiting_for_touch.get("focus_allowed") and not stop_event.is_set():
                    time.sleep(0.05)
                waiting_for_touch["focus_allowed"] = None
                socketio.emit("blink", {"target": None})
                time.sleep(pause)
                continue
            else:
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
    if waiting_for_touch.get("focus_allowed") == pod_id:
        waiting_for_touch["focus_allowed"] = None
    elif pod_id in waiting_for_touch:
        waiting_for_touch[pod_id] = False

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    socketio.emit("blink", {"target": None})
    socketio.emit("game_stopped")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)