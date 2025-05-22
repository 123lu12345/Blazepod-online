from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app)

connected_pods = set()
reaction_times = []

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/pod/<int:pod_id>")
def pod(pod_id):
    return render_template("pod.html", pod_id=pod_id)

@socketio.on("connect_pod")
def on_connect_pod(data):
    pod_id = data.get("pod_id")
    connected_pods.add(pod_id)
    emit("pod_connected", {"pod_id": pod_id}, broadcast=True)

@socketio.on("start_game")
def on_start_game(data):
    mode = data.get("mode", "touchswitch")
    print(f"🎮 Spielmodus: {mode}")

    if mode == "touchswitch":
        try:
            duration = int(data.get("duration", 1)) * 60
            if duration <= 0:
                duration = 60
        except:
            duration = 60
        print(f"[DEBUG] Spielzeit in Sekunden: {duration}")
        emit("start_touchswitch", {"duration": duration}, broadcast=True)

@socketio.on("reaction_time")
def on_reaction_time(data):
    reaction_times.append(data)
    print(f"⏱️ Neue Reaktionszeit: {data}")

@socketio.on("end_game")
def on_end_game():
    if reaction_times:
        total_time = sum([entry["time"] for entry in reaction_times])
        count = len(reaction_times)
        average = round(total_time / count, 2)
        emit("game_results", {
            "count": count,
            "average": average,
            "details": reaction_times
        }, broadcast=True)
    else:
        emit("game_results", {
            "count": 0,
            "average": 0,
            "details": []
        }, broadcast=True)

    reaction_times.clear()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
