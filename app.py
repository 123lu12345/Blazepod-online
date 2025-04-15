from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Event, Thread
import random
import time
import os

app = Flask(__name__)
socketio = SocketIO(app)

connected_pods = {}  # sid -> pod_id
stop_event = Event()
COLORS = ["red", "blue", "green", "yellow"]

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
    duration = int(data.get("duration", 5)) * 60
    mode = data.get("mode", "classic")
    interval = int(data.get("interval", 3))
    pause = float(data.get("pause", 1))
    multicolor = data.get("multicolor", False)

    def countdown_and_game():
        for i in range(10, 0, -1):
            socketio.emit("countdown_tick", {"value": i})
            time.sleep(1)
        socketio.emit("countdown_tick", {"value": 0})

        if mode == "touch":
            run_touch_to_switch_mode(duration, multicolor)
        else:
            run_classic_mode(duration, interval, pause, multicolor)

    Thread(target=countdown_and_game).start()

def run_classic_mode(duration, interval, pause, multicolor):
    end_time = time.time() + duration
    while time.time() < end_time:
        if stop_event.is_set():
            socketio.emit("blink", {"target": None})
            socketio.emit("game_stopped")
            return
        active_pods = list(set(connected_pods.values()))
        if active_pods:
            target = random.choice(active_pods)
            color = random.choice(COLORS) if multicolor else "red"
            socketio.emit("blink", {"target": target, "color": color})
            time.sleep(interval)
            socketio.emit("blink", {"target": None})
            time.sleep(pause)
    socketio.emit("blink", {"target": None})
    socketio.emit("game_finished")
    time.sleep(1)
    socketio.emit("game_stopped")

def run_touch_to_switch_mode(duration, multicolor):
    end_time = time.time() + duration

    def blink_next():
        if stop_event.is_set():
            return None, None
        active_pods = list(set(connected_pods.values()))
        if not active_pods:
            return None, None
        target = random.choice(active_pods)
        color = random.choice(COLORS) if multicolor else "red"
        socketio.emit("blink", {"target": target, "color": color})
        return target, color

    current_target, color = blink_next()
    while time.time() < end_time:
        if stop_event.is_set():
            break
        time.sleep(0.1)
    socketio.emit("blink", {"target": None})
    socketio.emit("game_finished")
    time.sleep(1)
    socketio.emit("game_stopped")

clicked_event = Event()
clicked_pod = None

@socketio.on("pod_clicked")
def pod_clicked(data):
    global clicked_pod
    clicked_pod = data.get("pod_id")
    clicked_event.set()

    # Start the next blink immediately
    if not stop_event.is_set():
        active_pods = list(set(connected_pods.values()))
        if active_pods:
            next_target = random.choice(active_pods)
            color = random.choice(COLORS)
            socketio.emit("blink", {"target": next_target, "color": color})

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    socketio.emit("blink", {"target": None})
    socketio.emit("game_stopped")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
