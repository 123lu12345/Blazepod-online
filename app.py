
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

    global touch_count, reaction_times
    touch_count = 0
    reaction_times = []
@socketio.on("start_game")
reaction_times = []
touch_count = 0

def start_game(data):
    target_color = data.get("targetColor", "")  # ignoriert, falls nicht gebraucht
    stop_event.clear()
    duration = int(data.get("duration", 1)) * 60
    interval = float(data.get("interval", 1))
    pause = float(data.get("pause", 1))
    mode = data.get("mode", "classic")
    random_timing = data.get("randomTiming", False)
    colors = data.get("colors", DEFAULT_COLORS)

    # Ensure that only selected colors are passed
    colors = [color for color in colors if color in data.get('colors', [])]

    def game_loop():
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
                start_time = time.time()
                while waiting_for_touch.get(target, False) and not stop_event.is_set():
                    time.sleep(0.05)
                end_time = time.time()
                reaction_time = end_time - start_time
                reaction_times.append(reaction_time)
                global touch_count
                touch_count += 1
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
        if mode == "touch-switch" and touch_count > 0:
            avg_reaction = sum(reaction_times) / len(reaction_times)
            socketio.emit("touch_results", {"count": touch_count, "average": round(avg_reaction, 2)})
        time.sleep(1)
        socketio.emit("game_stopped")

    Thread(target=game_loop).start()

@socketio.on("pod_touched")
def pod_touched(data):
    pod_id = data.get("pod_id")
    waiting_for_touch[pod_id] = False

@socketio.on("stop_game")
def stop_game():
    stop_event.set()
    socketio.emit("blink", {"target": None})
    socketio.emit("game_stopped")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
