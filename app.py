from flask import Flask, request
from flask_socketio import SocketIO, emit
import random
import time
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_pods = {}
game_running = False
expected_pod = None
expected_color = None
focus_hits = []
focus_errors = 0
focus_target_color = "Rot"

@app.route("/")
def index():
    return "Server läuft"

@socketio.on("connect_pod")
def handle_connect_pod(data):
    pod_id = data.get("pod_id")
    connected_pods[pod_id] = request.sid
    print(f"Pod {pod_id} verbunden.")

@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    for pod_id, pod_sid in list(connected_pods.items()):
        if pod_sid == sid:
            del connected_pods[pod_id]
            print(f"Pod {pod_id} getrennt.")

@socketio.on("reaction")
def handle_reaction(data):
    global focus_hits, focus_errors
    pod_id = data.get("pod_id")
    if game_running:
        if pod_id == expected_pod and expected_color == focus_target_color:
            print(f"Treffer auf Pod {pod_id}")
            focus_hits.append(time.time())
        else:
            print(f"Fehlerhafter Klick auf Pod {pod_id}")
            focus_errors += 1

@socketio.on("start_game")
def handle_start_game(data):
    global game_running, expected_pod, expected_color
    global focus_hits, focus_errors, focus_target_color

    if game_running:
        return
    game_running = True
    print("Spiel gestartet:", data)

    modus = data.get("modus", "Classic")
    duration = int(data.get("duration", 60))
    blink_count = int(data.get("blink_count", 30))
    colors = data.get("colors", ["Rot", "Blau"])
    pods = list(connected_pods.values())

    if modus == "Fokus":
        focus_target_color = colors[0] if colors else "Rot"
        focus_hits = []
        focus_errors = 0

    def game_loop():
        global game_running, expected_pod, expected_color
        start_time = time.time()
        count = 0

        while game_running:
            if duration > 0 and (time.time() - start_time) > duration:
                break
            if blink_count > 0 and count >= blink_count:
                break

            expected_pod = random.choice(list(connected_pods.keys()))
            expected_sid = connected_pods[expected_pod]
            expected_color = random.choice(colors)

            socketio.emit("blink", {"color": expected_color}, room=expected_sid)
            print(f"{expected_pod} blinkt mit {expected_color}")

            time.sleep(2)
            socketio.emit("blink", {"color": "black"}, room=expected_sid)
            time.sleep(1)
            count += 1

        game_running = False
        socketio.emit("blink", {"color": "black"})  # alle aus

        # Analyse an Dashboard
        socketio.emit("trigger_dashboard_save", {
            "mode": modus,
            "duration": duration,
            "colors": colors,
            "stats": {
                "hits": len(focus_hits),
                "errors": focus_errors
            } if modus == "Fokus" else None
        })
        print("Spiel beendet.")

    threading.Thread(target=game_loop).start()

@socketio.on("stop_game")
def handle_stop():
    global game_running
    game_running = False
    socketio.emit("blink", {"color": "black"})
    print("Manuell gestoppt")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)