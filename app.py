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
    print("[Server] Spiel startet...")
    stop_event.clear()
    duration = int(data.get("duration", 60))
    interval = float(data.get("interval", 2))
    colors = data.get("colors", ["red", "green"])
    pod_ids = list(set(connected_pods.values()))
    thread = Thread(target=start_game, args=(duration, interval, colors, pod_ids))
    thread.start()

@socketio.on("stop")
def stop():
    stop_event.set()
    socketio.emit("blink", {"text": "❌ Abgebrochen"})

def start_game(duration, interval, colors, pod_ids):
    for i in range(10, 0, -1):
        socketio.emit("countdown_tick", {"value": i})
        time.sleep(1)
    socketio.emit("countdown_tick", {"value": "Start!"})
    end_time = time.time() + duration
    while time.time() < end_time and not stop_event.is_set():
        target = random.choice(pod_ids)
        color = random.choice(colors)
        for pid in pod_ids:
            socketio.emit("blink", {"pod_id": pid, "color": color if pid == target else "black", "text": ""})
        time.sleep(interval)
    socketio.emit("blink", {"text": "✔️ Spiel beendet"})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), allow_unsafe_werkzeug=True)