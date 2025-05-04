from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Thread, Event
import random
import time
import os

app = Flask(__name__)
socketio = SocketIO(app)

connected_pods = {}
stop_event = Event()
selected_game_mode = "classic"

@app.route("/")
def dashboard():
    return render_template("dashboard.html", mode=selected_game_mode)

@app.route("/pod/<int:pod_id>")
def pod(pod_id):
    return render_template("pod.html")

@socketio.on("register")
def handle_register(data):
    pod_id = data["pod_id"]
    connected_pods[request.sid] = str(pod_id)
    emit("pod_connected", pod_id, broadcast=True)

@socketio.on("disconnect")
def handle_disconnect():
    disconnected_pod = connected_pods.pop(request.sid, None)
    if disconnected_pod:
        emit("pod_disconnected", disconnected_pod, broadcast=True)

@socketio.on("pod_touched")
def handle_pod_touch(data):
    print(f"Pod {data['pod_id']} touched")

@socketio.on("start")
def handle_start(data):
    global selected_game_mode
    selected_game_mode = data.get("mode", "classic")
    stop_event.clear()
    duration = int(data.get("duration", 60))
    interval = float(data.get("interval", 2))
    pause = float(data.get("pause", 1))
    colors = data.get("colors", ["red", "blue", "green"])

    pod_ids = list(set(connected_pods.values()))
    if not pod_ids:
        socketio.emit("blink", {"text": "⚠ Keine Pods verbunden"})
        return

    thread = Thread(target=start_classic_mode_with_countdown, args=(duration, interval, pause, colors, pod_ids))
    thread.start()

@socketio.on("stop")
def handle_stop():
    stop_event.set()
    socketio.emit("blink", {"text": "❌ Spiel abgebrochen"})

def start_classic_mode_with_countdown(duration, interval, pause, colors, pod_ids):
    # Gemeinsamer Countdown für Dashboard & Pods
    for i in range(10, 0, -1):
        socketio.emit("countdown_tick", {"value": i})
        time.sleep(1)
    socketio.emit("countdown_tick", {"value": "Start!"})

    start_time = time.time()
    end_time = start_time + duration

    while time.time() < end_time and not stop_event.is_set():
        active_pod = random.choice(pod_ids)
        color = random.choice(colors)
        for pid in pod_ids:
            if pid == active_pod:
                socketio.emit("blink", {"pod_id": pid, "color": color, "text": ""})
            else:
                socketio.emit("blink", {"pod_id": pid, "color": "black", "text": ""})
        time.sleep(interval)
        for pid in pod_ids:
            socketio.emit("blink", {"pod_id": pid, "color": "black", "text": ""})
        time.sleep(pause)

    if not stop_event.is_set():
        socketio.emit("blink", {"text": "✔ Spiel beendet"})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))