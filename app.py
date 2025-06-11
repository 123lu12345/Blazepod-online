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
DEFAULT_COLORS = ["red", "blue", "green", "yellow", "white", "orange", "violet", "gray", "brown"]
SHAPES = ["circle", "square", "triangle", "star"]
NUMBERS = ["1", "2", "3", "4"]
ARROWS = ["↑", "↓", "→", "←"]

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
    stop_event.clear()
    mode = data.get("mode", "classic")
    duration = int(data.get("duration", 1)) * 60
    interval = float(data.get("interval", 1))
    pause = float(data.get("pause", 1))
    endMode = data.get("endMode", "time")
    blink_limit = int(data.get("blinkCount", 20))
    colors = data.get("colors", DEFAULT_COLORS)

    def game_loop():
        for i in range(10, 0, -1):
            socketio.emit("countdown_tick", {"value": i})
            time.sleep(1)
        socketio.emit("countdown_tick", {"value": 0})
        if endMode == "time":
            socketio.emit("start_timer", {"duration": duration // 60})
        blink_counter = 0
        end_time = time.time() + duration

        while (endMode == "time" and time.time() < end_time) or (endMode == "blinks" and blink_counter < blink_limit):
            if stop_event.is_set():
                for sid in connected_pods.values():
                    socketio.emit("blink", {"target": None}, to=sid)
                socketio.emit("game_stopped")
                return

            pod_ids = list(connected_pods.keys())
            if not pod_ids:
                break

            target_pod = random.choice(pod_ids)
            target_sid = connected_pods[target_pod]

            if mode == "arrows":
                arrow = random.choice(ARROWS)
                color = random.choice(colors)
                socketio.emit("blink", {
                    "target": target_pod,
                    "number": arrow,
                    "mode": mode,
                    "color": color
                }, to=target_sid)
            else:
                color = random.choice(colors)
                socketio.emit("blink", {
                    "target": target_pod,
                    "color": color,
                    "mode": mode
                }, to=target_sid)

            time.sleep(interval)
            for sid in connected_pods.values():
                socketio.emit("blink", {"target": None}, to=sid)
            blink_counter += 1
            time.sleep(pause)

        for sid in connected_pods.values():
            socketio.emit("blink", {"target": None}, to=sid)
        socketio.emit("game_finished")
        socketio.emit("game_stopped")

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    for sid in connected_pods.values():
        socketio.emit("blink", {"target": None}, to=sid)
    socketio.emit("game_stopped")

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/pod/<pod_id>")
def pod(pod_id):
    return render_template("pod.html", pod_id=pod_id)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)