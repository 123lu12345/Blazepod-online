from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Thread, Event
import random
import time
import os

app = Flask(__name__)
socketio = SocketIO(app)

connected_pods = {}  # sid -> pod_id
stop_event = Event()
COLORS = ["red", "blue", "green", "yellow"]
game_mode = "classic"
game_running = False
memory_sequence = []
memory_progress = []

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
    global game_mode, game_running, memory_sequence, memory_progress
    stop_event.clear()
    game_running = True
    game_mode = data.get("mode", "classic")
    duration = int(data.get("duration", 5)) * 60
    interval = float(data.get("interval", 3))
    pause = float(data.get("pause", 1))
    multicolor = data.get("multicolor", False)
    memory_length = int(data.get("memoryLength", 4))

    def countdown_and_game():
        for i in range(10, 0, -1):
            socketio.emit("countdown_tick", {"value": i})
            time.sleep(1)
        socketio.emit("countdown_tick", {"value": 0})

        if game_mode == "classic":
            run_classic(duration, interval, pause, multicolor)
        elif game_mode == "touch":
            run_touch_to_switch(duration, multicolor)
        elif game_mode == "memory":
            run_memory_mode(memory_length, interval, pause, multicolor)

    Thread(target=countdown_and_game).start()

def run_classic(duration, interval, pause, multicolor):
    end_time = time.time() + duration
    while time.time() < end_time:
        if stop_event.is_set():
            break
        pods = list(set(connected_pods.values()))
        if pods:
            target = random.choice(pods)
            color = random.choice(COLORS) if multicolor else "red"
            socketio.emit("blink", {"target": target, "color": color})
            time.sleep(interval)
            socketio.emit("blink", {"target": None})
            time.sleep(pause)
    socketio.emit("blink", {"target": None})
    socketio.emit("game_finished")
    time.sleep(1)
    socketio.emit("game_stopped")

def run_touch_to_switch(duration, multicolor):
    end_time = time.time() + duration
    if not connected_pods: return
    pods = list(set(connected_pods.values()))
    next_target = random.choice(pods)
    color = random.choice(COLORS) if multicolor else "red"
    socketio.emit("blink", {"target": next_target, "color": color})

    while time.time() < end_time:
        if stop_event.is_set():
            break
        time.sleep(0.1)
    socketio.emit("blink", {"target": None})
    socketio.emit("game_finished")
    time.sleep(1)
    socketio.emit("game_stopped")

def run_memory_mode(length, interval, pause, multicolor):
    global memory_sequence, memory_progress
    pods = list(set(connected_pods.values()))
    if not pods: return
    memory_sequence = [random.choice(pods) for _ in range(length)]
    memory_progress = []
    for pod in memory_sequence:
        color = random.choice(COLORS) if multicolor else "red"
        socketio.emit("blink", {"target": pod, "color": color})
        time.sleep(interval)
        socketio.emit("blink", {"target": None})
        time.sleep(pause)
    socketio.emit("memory_input", {}, broadcast=True)

@socketio.on("pod_clicked")
def handle_pod_click(data):
    global memory_progress
    pod_id = data.get("pod_id")
    if game_mode == "touch":
        if not stop_event.is_set():
            pods = list(set(connected_pods.values()))
            target = random.choice(pods)
            socketio.emit("blink", {"target": target, "color": "red"})
    elif game_mode == "memory":
        expected = memory_sequence[len(memory_progress)]
        if pod_id == expected:
            memory_progress.append(pod_id)
            if len(memory_progress) == len(memory_sequence):
                socketio.emit("memory_result", {"success": True}, broadcast=True)
                socketio.emit("game_finished")
                time.sleep(1)
                socketio.emit("game_stopped")
        else:
            socketio.emit("memory_result", {"success": False}, broadcast=True)
            socketio.emit("game_stopped")

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    socketio.emit("blink", {"target": None})
    socketio.emit("game_stopped")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
