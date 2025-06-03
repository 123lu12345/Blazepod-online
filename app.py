
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
DEFAULT_COLORS = ["red", "blue", "green", "yellow", "white", "orange", "violet", "gray", "brown"]
SHAPES = ["circle", "square", "triangle", "star"]
NUMBERS = ["1", "2", "3", "4"]

focus_hits = []
focus_errors = 0
reaction_times = []
blink_start_time = {}

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
    endMode = data.get('endMode', 'time')
    endMode = data.get('endMode', 'time')
    global focus_hits, focus_errors, reaction_times, blink_start_time
    target_color = data.get("targetColor", "red")
    stop_event.clear()
    duration = int(data.get("duration", 1)) * 60
    interval = float(data.get("interval", 1))
    pause = float(data.get("pause", 1))
    mode = data.get("mode", "classic")
    colors = data.get("colors", DEFAULT_COLORS)
    random_timing = data.get("randomTiming", False)
    colors = [color for color in colors if color in data.get('colors', [])]

    focus_hits = []
    focus_errors = 0
    reaction_times = []
    blink_start_time = {}

    def game_loop():
        for i in range(10, 0, -1):
            socketio.emit("countdown_tick", {"value": i})
            time.sleep(1)
    
         if mode == "focus" else None
        })

        time.sleep(1)
        socketio.emit("countdown_tick", {"value": 0})
        if endMode == "time":
            socketio.emit("start_timer", {"duration": duration // 60})
        blink_counter = 0
        blink_limit = int(data.get("blinkCount", 20))
    

        end_time = time.time() + duration
        while (endMode == 'time' and time.time() < end_time) or (endMode == 'blinks' and blink_counter < blink_limit):
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
                blink_start_time[target_pod] = time.time()

                distractor_colors = [c for c in colors if c != target_color]
                for pod_id, sid in connected_pods.items():
                    if pod_id != target_pod:
                        color = random.choice(distractor_colors) if distractor_colors else "white"
                        socketio.emit("blink", {"target": pod_id, "color": color, "mode": mode}, to=sid)

                waiting_for_touch["focus_allowed"] = target_pod
                while waiting_for_touch.get("focus_allowed") and not stop_event.is_set():
                    time.sleep(0.05)
                waiting_for_touch["focus_allowed"] = None
                for sid in connected_pods.values():
                    socketio.emit("blink", {"target": None}, to=sid)
                blink_counter += 1
                time.sleep(pause)
                continue

            target_pod = random.choice(pod_ids)
            target_sid = connected_pods[target_pod]

            if mode == "shapes":
                form = random.choice(SHAPES)
                color = random.choice(colors)
                socketio.emit("blink", {"target": target_pod, "form": form, "mode": mode, "color": color}, to=target_sid)
            elif mode == "numbers":
                number = random.choice(NUMBERS)
                color = random.choice(colors)
                socketio.emit("blink", {"target": target_pod, "number": number, "mode": mode, "color": color}, to=target_sid)
            elif mode == "touch-switch":
                color = random.choice(colors)
                socketio.emit("blink", {"target": target_pod, "color": color}, to=target_sid)
                waiting_for_touch[target_pod] = True
                while waiting_for_touch.get(target_pod, False) and not stop_event.is_set():
                    time.sleep(0.05)
                socketio.emit("blink", {"target": None}, to=target_sid)
                blink_counter += 1
                time.sleep(0.5)
                continue
            elif mode == "stroop":
                word_options = ["Rot", "Blau", "Grün", "Gelb", "Pink", "Orange", "Weiß", "Schwarz", "Violett"]
                color_options = colors.copy()
                word = random.choice(word_options)
                bg_color = random.choice(color_options)
                text_color = random.choice(color_options)
                while text_color == bg_color or word.lower() == bg_color or word.lower() == text_color:
                    bg_color = random.choice(color_options)
                    text_color = random.choice(color_options)
                socketio.emit("blink", {
                    "target": target_pod,
                    "mode": "stroop",
                    "bg_color": bg_color,
                    "text_color": text_color,
                    "word": word
                }, to=target_sid)
            elif mode == "all-at-once":
                color = random.choice(colors)
                for sid in connected_pods.values():
                    socketio.emit("blink", {"target": None, "color": color, "mode": mode}, to=sid)
            else:
                color = random.choice(colors)
                socketio.emit("blink", {"target": target_pod, "color": color, "mode": mode}, to=target_sid)

            blink_duration = random.uniform(0.6, interval) if random_timing else interval
            time.sleep(blink_duration)
            for sid in connected_pods.values():
                socketio.emit("blink", {"target": None}, to=sid)
            blink_counter += 1
            black_pause = random.uniform(0.3, pause) if random_timing else pause
            time.sleep(black_pause)

        for sid in connected_pods.values():
            socketio.emit("blink", {"target": None}, to=sid)
        socketio.emit("game_finished")
        if focus_hits:
            avg_time = round(sum(reaction_times) / len(reaction_times), 3)
        else:
            avg_time = 0.0

        if mode == "focus":
            if focus_hits:
                avg_time = round(sum(reaction_times) / len(reaction_times), 3)
            else:
                avg_time = 0.0
            socketio.emit("focus_stats", {
                "hits": len(focus_hits),
                "errors": focus_errors,
                "avg_time": avg_time,
                "details": focus_hits
            })


        socketio.emit("trigger_dashboard_save", {
            "mode": mode,
            "duration": duration,
            "colors": colors,
            "stats": {
                "treffer": len(focus_hits),
                "fehler": focus_errors,
                "avg_time": avg_time,
                "details": focus_hits
            } if mode == "focus" else None
        })

        time.sleep(1)
        socketio.emit("game_stopped")

    Thread(target=game_loop).start()

@socketio.on("pod_touched")
def pod_touched(data):
    global focus_hits, focus_errors, reaction_times, blink_start_time
    pod_id = data.get("pod_id")
    if waiting_for_touch.get("focus_allowed") == pod_id:
        reaction_time = time.time() - blink_start_time.get(pod_id, time.time())
        focus_hits.append({"pod": pod_id, "time": reaction_time})
        reaction_times.append(reaction_time)
        waiting_for_touch["focus_allowed"] = None
    elif pod_id in waiting_for_touch:
        waiting_for_touch[pod_id] = False
    else:
        focus_errors += 1

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    for sid in connected_pods.values():
        socketio.emit("blink", {"target": None}, to=sid)
    socketio.emit("game_stopped")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
