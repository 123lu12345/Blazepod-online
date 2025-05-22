
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_pods = {}
reaction_times = []
start_time = None
game_active = False

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/pod/<int:pod_id>")
def pod(pod_id):
    return render_template("pod.html", pod_id=pod_id)

@socketio.on("connect_pod")
def handle_connect_pod(data):
    pod_id = data["pod_id"]
    connected_pods[pod_id] = request.sid
    print(f"[INFO] Pod {pod_id} verbunden: {request.sid}")
    emit("pod_status", {"pod_id": pod_id, "status": "connected"}, broadcast=True)

@socketio.on("disconnect")
def handle_disconnect():
    for pod_id, sid in list(connected_pods.items()):
        if sid == request.sid:
            print(f"[INFO] Pod {pod_id} getrennt: {sid}")
            del connected_pods[pod_id]
            emit("pod_status", {"pod_id": pod_id, "status": "disconnected"}, broadcast=True)
            break

@socketio.on("start_game")
def handle_start_game(data):
    global start_time, game_active, reaction_times
    start_time = time.time()
    game_active = True
    reaction_times = []
    print("[INFO] Spiel gestartet")
    emit("start_game", data, broadcast=True)

@socketio.on("stop_game")
def handle_stop_game():
    global game_active
    game_active = False
    print("[INFO] Spiel gestoppt")
    emit("stop_game", broadcast=True)

@socketio.on("reaction")
def handle_reaction(data):
    global reaction_times
    if game_active and start_time:
        reaction_time = time.time() - start_time
        reaction_times.append(reaction_time)
        print(f"[INFO] Reaktion: {reaction_time:.3f} Sekunden")
        emit("reaction_ack", {"reaction_time": reaction_time})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
