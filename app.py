import time
import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_pods = {}
active_pods = []

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/pod/<int:pod_id>")
def pod(pod_id):
    return render_template("pod.html", pod_id=pod_id)

@socketio.on("register_pod")
def handle_register_pod(pod_id):
    connected_pods[pod_id] = request.sid
    if pod_id not in active_pods:
        active_pods.append(pod_id)
    print(f"Pod {pod_id} registriert.")
    emit("update", active_pods, broadcast=True)

@socketio.on("disconnect")
def disconnect():
    for pod_id, sid in list(connected_pods.items()):
        if sid == request.sid:
            print(f"Pod {pod_id} getrennt")
            connected_pods.pop(pod_id, None)
            if pod_id in active_pods:
                active_pods.remove(pod_id)
    emit("update", active_pods, broadcast=True)

@socketio.on("start_game")
def start_game(settings):
    mode = settings.get("mode")
    duration = int(settings.get("duration", 60))
    blink_interval = float(settings.get("interval", 3))
    pause_between = float(settings.get("pause", 1))

    print(f"Starte Spielmodus: {mode} mit {len(active_pods)} Pods")

    if mode == "reaktionsspiel":
        total_points = 0
        target_color = settings.get("targetColor", "red")
        color_options = settings.get("activeColors", ["red", "blue", "green", "yellow", "orange", "pink", "white", "black", "violet"])
        color_options = [c for c in color_options if c != target_color]

        start_time = time.time()
        while time.time() - start_time < duration:
            target_pod = random.choice(active_pods)
            current_colors = {}
            used_colors = set([target_color])
            for pid in active_pods:
                if pid == target_pod:
                    current_colors[pid] = target_color
                else:
                    available = [c for c in color_options if c not in used_colors]
                    if not available:
                        used_colors = set([target_color])
                        available = [c for c in color_options]
                    chosen = random.choice(available)
                    used_colors.add(chosen)
                    current_colors[pid] = chosen

            for pid in active_pods:
                emit("show_color", {"color": current_colors[pid]}, to=connected_pods[pid])

            clicked_pod = wait_for_click_or_timeout(active_pods, blink_interval)
            if clicked_pod == target_pod:
                total_points += 1

            for pid in active_pods:
                emit("show_color", {"color": "black"}, to=connected_pods[pid])
            time.sleep(pause_between)

        for pid in active_pods:
            emit("show_score", {"score": total_points}, to=connected_pods[pid])

def wait_for_click_or_timeout(pods, timeout):
    time.sleep(timeout)
    return None

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)