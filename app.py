
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
from threading import Thread, Event
import random
import time
import os

app = Flask(__name__)
socketio = SocketIO(app)

connected_pods = {}  # sid -> pod_id
stop_event = Event()
COLORS = ["red", "blue", "green", "yellow"]
SHAPES = ["circle", "square", "triangle", "star"]

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
def on_disconnect():
    if request.sid in connected_pods:
        del connected_pods[request.sid]
    emit("update", list(set(connected_pods.values())), broadcast=True)

@socketio.on("start_game")
def start_game(data):
    stop_event.clear()
    duration = int(data.get("duration", 5)) * 60
    interval = float(data.get("interval", 3))
    pause = float(data.get("pause", 1))
    multicolor = data.get("multicolor", False)
    random_timing = data.get("randomTiming", False)
    mode = data.get("mode", "classic")

    def countdown_and_game():
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
            if active_pods:
                target = random.choice(active_pods)
                if mode == "shapes":
                    form = random.choice(SHAPES)
                    socketio.emit("blink", {"target": target, "form": form})
                else:
                    color = random.choice(COLORS) if multicolor or mode == "multicolor" else "red"
                    socketio.emit("blink", {"target": target, "color": color})

                blink_duration = random.uniform(0.6, interval) if random_timing else interval
                time.sleep(blink_duration)

                socketio.emit("blink", {"target": None})
                black_pause = random.uniform(0.3, pause) if random_timing else pause
                time.sleep(black_pause)

        socketio.emit("blink", {"target": None})
        socketio.emit("game_finished")
        time.sleep(1)
        socketio.emit("game_stopped")

    Thread(target=countdown_and_game).start()

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    socketio.emit("blink", {"target": None})
    socketio.emit("game_stopped")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
