
import random
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Lock, Event

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_pods = {}
stop_event = Event()

@app.route("/")
def index():
    return "Dashboard läuft"

@app.route("/pod/<int:pod_id>")
def pod(pod_id):
    return f"Pod {pod_id} verbunden"

@socketio.on("register")
def register(data):
    pod_id = data.get("pod_id")
    connected_pods[request.sid] = pod_id
    emit("pod_connected", pod_id, broadcast=True)
    emit("update", list(set(connected_pods.values())), broadcast=True)

@socketio.on("disconnect")
def disconnect():
    if request.sid in connected_pods:
        del connected_pods[request.sid]
        emit("update", list(set(connected_pods.values())), broadcast=True)

@socketio.on("start_game")
def start_game(data):
    stop_event.clear()
    mode = data.get("mode", "classic")
    duration = int(data.get("duration", 60))
    interval = float(data.get("interval", 1))
    pause = float(data.get("pause", 1))
    colors = data.get("colors", ["red", "blue", "green"])
    print(f"START_GAME: mode={mode}, duration={duration}, interval={interval}, pause={pause}, colors={colors}")

    for sec in range(10, 0, -1):
        if stop_event.is_set():
            return
        socketio.emit("countdown_tick", {"value": sec})
        time.sleep(1)

    socketio.emit("countdown_tick", {"value": "Start!"})
    time.sleep(1)

    if mode == "classic":
        socketio.start_background_task(start_classic_mode, duration, interval, pause, colors)

def start_classic_mode(duration, interval, pause, colors):
    print("CLASSIC MODE gestartet")
    start_time = time.time()
    pod_ids = list(set(connected_pods.values()))
    print(f"Angemeldete Pods: {pod_ids}")
    if not pod_ids:
        print("KEINE Pods verbunden")
        return

    while not stop_event.is_set() and time.time() - start_time < duration:
        pod = random.choice(pod_ids)
        color = random.choice(colors)
        print(f"Blinke {pod} mit Farbe {color}")
        socketio.emit("show_color", {"pod_id": pod, "color": color})
        time.sleep(interval)
        socketio.emit("clear", {}, broadcast=True)
        time.sleep(pause)

    socketio.emit("show_text", {"text": "✔ Spiel beendet"})

@socketio.on("stop_game")
def stop_game():
    print("Spiel abgebrochen")
    stop_event.set()
    socketio.emit("show_text", {"text": "❌ Spiel abgebrochen"})
    socketio.emit("clear", {}, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
