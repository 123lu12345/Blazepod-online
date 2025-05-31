from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random
import time
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_pods = {}
game_running = False

@app.route("/")
def index():
    return "Server is running."

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

@socketio.on("start_game")
def handle_start_game(data):
    global game_running
    if game_running:
        return
    game_running = True
    print("Spiel gestartet mit Daten:", data)

    modus = data.get("modus", "Classic")
    duration = int(data.get("duration", 60))
    blink_count = int(data.get("blink_count", 30))
    colors = data.get("colors", ["Rot", "Blau"])
    pods = list(connected_pods.values())

    def game_thread():
        start_time = time.time()
        count = 0
        focus_hits = []
        focus_errors = 0

        while game_running:
            if duration > 0 and (time.time() - start_time) > duration:
                break
            if blink_count > 0 and count >= blink_count:
                break

            active_pod = random.choice(pods)
            chosen_color = random.choice(colors)
            socketio.emit("blink", {"color": chosen_color}, room=active_pod)
            print(f"Blink auf Pod: {active_pod} mit Farbe: {chosen_color}")

            # Wartezeit simulieren (z. B. 2 Sekunden + Pause)
            time.sleep(2)
            socketio.emit("blink", {"color": "black"}, room=active_pod)
            time.sleep(1)
            count += 1

        # Spiel zu Ende
        socketio.emit("blink", {"color": "black"})  # alle ausschalten
        game_running = False
        print("Spiel beendet.")

        # Trigger zum Dashboard senden
        socketio.emit("trigger_dashboard_save", {
            "mode": modus,
            "duration": duration,
            "colors": colors,
            "stats": {
                "hits": len(focus_hits),
                "errors": focus_errors
            } if modus == "Fokus" else None
        })

    threading.Thread(target=game_thread).start()

@socketio.on("stop_game")
def handle_stop():
    global game_running
    game_running = False
    socketio.emit("blink", {"color": "black"})  # sofort alles aus
    print("Spiel wurde manuell gestoppt.")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)