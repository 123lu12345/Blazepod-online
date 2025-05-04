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
DEFAULT_COLORS = ["red", "blue", "green", "yellow", "white", "orange", "pink", "black", "violet"]
SHAPES = ["circle", "square", "triangle", "star"]
NUMBERS = ["1", "2", "3", "4"]
reaktionsspiel_active = False
active_reaktionsspiel_pods = []
color_map = {}
current_target_color = ""
score = {"points": 0}

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
    duration = int(data.get("duration", 1)) * 60
    interval = float(data.get("interval", 1))
    pause = float(data.get("pause", 1))
    mode = data.get("mode", "classic")
    random_timing = data.get("randomTiming", False)
    colors = data.get("colors", DEFAULT_COLORS)

    def game_loop():
        for i in range(10, 0, -1):
            socketio.emit("countdown_tick", {"value": i})
            time.sleep(1)
        socketio.emit("countdown_tick", {"value": 0})

        end_time = time.time() + duration
        while time.time() < end_time:
        if mode == "reaktionsspiel":
            active_pods = list(set(connected_pods.values()))
            if not active_pods:
                break

            used_colors = random.sample(colors, len(active_pods))
            target_color = random.choice(used_colors)
            socketio.emit("reaktionsspiel_target", {"color": target_color})

            global reaktionsspiel_active, active_reaktionsspiel_pods, color_map, current_target_color
            reaktionsspiel_active = True
            active_reaktionsspiel_pods = active_pods
            color_map = {pid: col for pid, col in zip(active_pods, used_colors)}
            current_target_color = target_color

            for pod_id, color in color_map.items():
                socketio.emit("blink", {"target": pod_id, "color": color})

            blink_duration = random.uniform(0.6, interval) if random_timing else interval
            time.sleep(blink_duration)

            socketio.emit("blink", {"target": None})
            black_pause = random.uniform(0.3, pause) if random_timing else pause
            time.sleep(black_pause)
            continue

            if stop_event.is_set():
                socketio.emit("blink", {"target": None})
                socketio.emit("game_stopped")
                return

            active_pods = list(set(connected_pods.values()))
            if not active_pods:
                break
            target = random.choice(active_pods)

            if mode == "shapes":
                form = random.choice(SHAPES)
                color = random.choice(colors)
                socketio.emit("blink", {"target": target, "form": form, "mode": mode, "color": color})
            elif mode == "numbers":
                number = random.choice(NUMBERS)
                color = random.choice(colors)
                socketio.emit("blink", {"target": target, "number": number, "mode": mode, "color": color})
            elif mode == "touch-switch":
                color = random.choice(colors)
                socketio.emit("blink", {"target": target, "color": color})
                waiting_for_touch[target] = True
                while waiting_for_touch.get(target, False) and not stop_event.is_set():
                    time.sleep(0.05)
                socketio.emit("blink", {"target": None})
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
                    "target": target,
                    "mode": "stroop",
                    "bg_color": bg_color,
                    "text_color": text_color,
                    "word": word
                })
            else:
                color = random.choice(colors)
                socketio.emit("blink", {"target": target, "color": color, "mode": mode})

            blink_duration = random.uniform(0.6, interval) if random_timing else interval
            time.sleep(blink_duration)

            socketio.emit("blink", {"target": None})
            black_pause = random.uniform(0.3, pause) if random_timing else pause
            time.sleep(black_pause)

        socketio.emit("blink", {"target": None})
        socketio.emit("game_finished")
        time.sleep(1)
        socketio.emit("game_stopped")

    Thread(target=game_loop).start()

@socketio.on("pod_touched")
def pod_touched(data):
    pod_id = data.get("pod_id")
    waiting_for_touch[pod_id] = False

if reaktionsspiel_active:
        if pod_id in active_reaktionsspiel_pods and color_map.get(pod_id) == current_target_color:
            score["points"] += 1
            socketio.emit("reaktionsspiel_score", {"score": score["points"]})

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    socketio.emit("blink", {"target": None})
    socketio.emit("game_stopped")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)