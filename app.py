
import random
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Event

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_pods = {}
stop_event = Event()

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/pod/<int:pod_id>")
def pod(pod_id):
    return render_template("pod.html", pod_id=pod_id)

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
    target_color = data.get("target_color", "red")

    for sec in range(10, 0, -1):
        if stop_event.is_set():
            return
        socketio.emit("countdown_tick", {"value": sec})
        time.sleep(1)

    socketio.emit("countdown_tick", {"value": "Start!"})
    time.sleep(1)

    if mode == "classic":
        socketio.start_background_task(start_classic_mode, duration, interval, pause, colors)
    elif mode == "reaktionsspiel":
        socketio.start_background_task(start_reaktionsspiel, duration, colors, target_color)
    elif mode == "touch_to_switch":
        socketio.start_background_task(start_touch_to_switch, duration, colors)
    elif mode == "formen":
        socketio.start_background_task(start_formen, duration)
    elif mode == "zahlen":
        socketio.start_background_task(start_zahlen, duration)
    elif mode == "stoop_test":
        socketio.start_background_task(start_stoop_test, duration)


def start_classic_mode(duration, interval, pause, colors):
    pod_ids = list(set(connected_pods.values()))
    print(f"CLASSIC START: erkannte Pods: {pod_ids}")
    if not pod_ids:
        socketio.emit("show_text", {"text": "⚠ Keine Pods verbunden – Spiel abgebrochen"})
        return

    start_time = time.time()
    pod_ids = list(set(connected_pods.values()))
    while not stop_event.is_set() and time.time() - start_time < duration:
        pod = random.choice(pod_ids)
        color = random.choice(colors)
        socketio.emit("show_color", {"pod_id": pod, "color": color})
        time.sleep(interval)
        socketio.emit("clear", {}, broadcast=True)
        time.sleep(pause)
    socketio.emit("show_text", {"text": "✔ Spiel beendet"})


def start_reaktionsspiel(duration, colors, target_color):
    pod_ids = list(set(connected_pods.values()))
    print(f"REAKTIONSSPIEL START: erkannte Pods: {pod_ids}")
    if not pod_ids:
        socketio.emit("show_text", {"text": "⚠ Keine Pods verbunden – Spiel abgebrochen"})
        return

    start_time = time.time()
    pod_ids = list(set(connected_pods.values()))
    while not stop_event.is_set() and time.time() - start_time < duration:
        correct_pod = random.choice(pod_ids)
        for pod in pod_ids:
            color = target_color if pod == correct_pod else random.choice([c for c in colors if c != target_color])
            socketio.emit("show_color", {"pod_id": pod, "color": color})
        time.sleep(5)  # Reaktion erwartet
        socketio.emit("clear", {}, broadcast=True)
        time.sleep(1)
    socketio.emit("show_text", {"text": "✔ Spiel beendet"})


def start_touch_to_switch(duration, colors):
    pod_ids = list(set(connected_pods.values()))
    print(f"TOUCH TO SWITCH START: erkannte Pods: {pod_ids}")
    if not pod_ids:
        socketio.emit("show_text", {"text": "⚠ Keine Pods verbunden – Spiel abgebrochen"})
        return

    start_time = time.time()
    pod_ids = list(set(connected_pods.values()))
    while not stop_event.is_set() and time.time() - start_time < duration:
        pod = random.choice(pod_ids)
        color = random.choice(colors)
        socketio.emit("show_color", {"pod_id": pod, "color": color})
        time.sleep(3)  # Zeit geben, bis der Pod "getoucht" wird
        socketio.emit("clear", {}, broadcast=True)
        time.sleep(1)
    socketio.emit("show_text", {"text": "✔ Spiel beendet"})


def start_formen(duration):
    pod_ids = list(set(connected_pods.values()))
    print(f"FORMEN START: erkannte Pods: {pod_ids}")
    if not pod_ids:
        socketio.emit("show_text", {"text": "⚠ Keine Pods verbunden – Spiel abgebrochen"})
        return

    formen = ["Kreis", "Viereck", "Dreieck", "Fünfeck"]
    start_time = time.time()
    pod_ids = list(set(connected_pods.values()))
    while not stop_event.is_set() and time.time() - start_time < duration:
        pod = random.choice(pod_ids)
        form = random.choice(formen)
        socketio.emit("show_text", {"pod_id": pod, "text": form})
        time.sleep(2)
        socketio.emit("clear", {}, broadcast=True)
        time.sleep(1)
    socketio.emit("show_text", {"text": "✔ Spiel beendet"})


def start_zahlen(duration):
    pod_ids = list(set(connected_pods.values()))
    print(f"ZAHLEN START: erkannte Pods: {pod_ids}")
    if not pod_ids:
        socketio.emit("show_text", {"text": "⚠ Keine Pods verbunden – Spiel abgebrochen"})
        return

    start_time = time.time()
    pod_ids = list(set(connected_pods.values()))
    while not stop_event.is_set() and time.time() - start_time < duration:
        pod = random.choice(pod_ids)
        number = str(random.randint(1, 99))
        socketio.emit("show_text", {"pod_id": pod, "text": number})
        time.sleep(2)
        socketio.emit("clear", {}, broadcast=True)
        time.sleep(1)
    socketio.emit("show_text", {"text": "✔ Spiel beendet"})


def start_stoop_test(duration):
    pod_ids = list(set(connected_pods.values()))
    print(f"STOOP TEST START: erkannte Pods: {pod_ids}")
    if not pod_ids:
        socketio.emit("show_text", {"text": "⚠ Keine Pods verbunden – Spiel abgebrochen"})
        return

    farbnamen = ["Rot", "Blau", "Grün", "Gelb"]
    farbcodes = ["red", "blue", "green", "yellow"]
    start_time = time.time()
    pod_ids = list(set(connected_pods.values()))
    while not stop_event.is_set() and time.time() - start_time < duration:
        pod = random.choice(pod_ids)
        text = random.choice(farbnamen)
        color = random.choice(farbcodes)
        socketio.emit("show_stoop", {"pod_id": pod, "text": text, "color": color})
        time.sleep(3)
        socketio.emit("clear", {}, broadcast=True)
        time.sleep(1)
    socketio.emit("show_text", {"text": "✔ Spiel beendet"})

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    socketio.emit("show_text", {"text": "❌ Spiel abgebrochen"})
    socketio.emit("clear", {}, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
