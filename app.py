from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time, random, os
from threading import Thread, Event

app = Flask(__name__)
socketio = SocketIO(app)
connected_pods = {}
stop_event = Event()

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/pod/<int:pod_id>")
def pod(pod_id):
    return render_template("pod.html")

@socketio.on("register")
def register(data):
    connected_pods[request.sid] = str(data["pod_id"])
    emit("pod_connected", data["pod_id"], broadcast=True)

@socketio.on("disconnect")
def disconnect():
    pid = connected_pods.pop(request.sid, None)
    if pid:
        emit("pod_disconnected", pid, broadcast=True)

@socketio.on("start")
def start(data):
    stop_event.clear()
    mode = data.get("mode", "classic")
    duration = int(data.get("duration", 60))
    interval = float(data.get("interval", 2))
    pause = float(data.get("pause", 1))
    colors = data.get("colors", ["red", "green", "blue"])
    target_color = data.get("target_color", "red")
    pod_ids = list(set(connected_pods.values()))
    thread = Thread(target=run_game, args=(mode, duration, interval, pause, colors, target_color, pod_ids))
    thread.start()

@socketio.on("stop")
def stop():
    stop_event.set()
    socketio.emit("blink", {"text": "❌ Abgebrochen"})

@socketio.on("pod_touched")
def on_touch(data):
    # Wird je nach Modus genutzt, z.B. bei Touch-to-Switch oder Reaktionsspiel
    print(f"Pod {data.get('pod_id')} touched")

def run_game(mode, duration, interval, pause, colors, target_color, pod_ids):
    for i in range(10, 0, -1):
        socketio.emit("countdown_tick", {"value": i})
        time.sleep(1)
    socketio.emit("countdown_tick", {"value": "Start!"})

    start_time = time.time()
    end_time = start_time + duration

    while time.time() < end_time and not stop_event.is_set():
        if mode == "classic":
            target = random.choice(pod_ids)
            color = random.choice(colors)
            for pid in pod_ids:
                socketio.emit("blink", {
                    "pod_id": pid,
                    "color": color if pid == target else "black",
                    "text": ""
                })
        elif mode == "formen":
            shape = random.choice(["●", "■", "▲", "⬟"])
            target = random.choice(pod_ids)
            for pid in pod_ids:
                socketio.emit("blink", {
                    "pod_id": pid,
                    "color": "black" if pid != target else "blue",
                    "text": shape if pid == target else ""
                })
        elif mode == "zahlen":
            number = str(random.randint(1, 4))
            target = random.choice(pod_ids)
            for pid in pod_ids:
                socketio.emit("blink", {
                    "pod_id": pid,
                    "color": "black" if pid != target else "yellow",
                    "text": number if pid == target else ""
                })
        elif mode == "touch":
            target = random.choice(pod_ids)
            socketio.emit("blink", {"pod_id": target, "color": random.choice(colors), "text": "👆"})
            # warte bis Stopp oder Zeit um
            time.sleep(interval)
        elif mode == "reaktion":
            correct = random.choice(pod_ids)
            for pid in pod_ids:
                socketio.emit("blink", {
                    "pod_id": pid,
                    "color": target_color if pid == correct else random.choice(colors),
                    "text": ""
                })
        elif mode == "stoop":
            word = random.choice(["Rot", "Blau", "Grün", "Gelb"])
            color = random.choice(["red", "blue", "green", "yellow"])
            target = random.choice(pod_ids)
            for pid in pod_ids:
                socketio.emit("blink", {
                    "pod_id": pid,
                    "color": color if pid == target else "black",
                    "text": word if pid == target else ""
                })
        time.sleep(interval)
        for pid in pod_ids:
            socketio.emit("blink", {"pod_id": pid, "color": "black", "text": ""})
        time.sleep(pause)

    if not stop_event.is_set():
        socketio.emit("blink", {"text": "✔️ Spiel beendet"})