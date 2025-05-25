from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Thread, Event
import random
import time
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app)

connected_pods = {}  # pod_id -> socket_id
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
    pod_id = str(data.get("pod_id"))
    connected_pods[pod_id] = request.sid
    emit("update", list(connected_pods.keys()), broadcast=True)

@socketio.on("disconnect")
def disconnect():
    disconnected = None
    for pod_id, sid in connected_pods.items():
        if sid == request.sid:
            disconnected = pod_id
            break
    if disconnected:
        del connected_pods[disconnected]
    emit("update", list(connected_pods.keys()), broadcast=True)

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
                for sid in connected_pods.values():
                    socketio.emit("blink", {"target": None}, to=sid)
                socketio.emit("game_stopped")
                return

            pod_ids = list(connected_pods.keys())
            if not pod_ids:
                break

            if mode == "focus":
                target_pod = random.choice(pod_ids)
                target_sid = connected_pods[target_pod]
                socketio.emit("blink", {"target": target_pod, "color": target_color, "mode": mode}, to=target_sid)

                distractor_colors = [c for c in colors if c != target_color]
                for pod_id, sid in connected_pods.items():
                    if pod_id != target_pod:
                        color = random.choice(distractor_colors) if distractor_colors else "gray"
                        socketio.emit("blink", {"target": pod_id, "color": color, "mode": mode}, to=sid)

                waiting_for_touch["focus_allowed"] = target_pod
                while waiting_for_touch.get("focus_allowed") and not stop_event.is_set():
                    time.sleep(0.05)
                waiting_for_touch["focus_allowed"] = None
                for sid in connected_pods.values():
                    socketio.emit("blink", {"target": None}, to=sid)
                time.sleep(pause)
                continue
            else:
                target_pod = random.choice(pod_ids)
                color = random.choice(colors)
                socketio.emit("blink", {"target": target_pod, "color": color, "mode": mode}, to=connected_pods[target_pod])

            time.sleep(interval)
            for sid in connected_pods.values():
                socketio.emit("blink", {"target": None}, to=sid)
            time.sleep(pause)

        for sid in connected_pods.values():
            socketio.emit("blink", {"target": None}, to=sid)
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
    for sid in connected_pods.values():
        socketio.emit("blink", {"target": None}, to=sid)
    socketio.emit("game_stopped")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)