
# --- Flask BlazePod System mit Touch-to-Switch-Modus, Reaktionszeitauswertung & Dashboard ---
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from datetime import datetime
import random

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_pods = set()
reaction_times = []
last_timestamp = None
game_running = False
start_time = None

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/pod/<int:pod_id>')
def pod(pod_id):
    return render_template('pod.html', pod_id=pod_id)

@socketio.on('connect_pod')
def handle_connect_pod(data):
    pod_id = data['pod_id']
    connected_pods.add(pod_id)
    print(f"✅ Pod {pod_id} verbunden")
    emit('update_connected_pods', list(connected_pods), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    for pod_id in list(connected_pods):
        connected_pods.discard(pod_id)
    emit('update_connected_pods', list(connected_pods), broadcast=True)

@socketio.on('start_game')
def handle_start_game(data):
    global game_running, start_time, last_timestamp, reaction_times
    game_running = True
    reaction_times = []
    start_time = datetime.now()
    last_timestamp = datetime.now()
    print("🎮 Spiel gestartet")
    emit('countdown', broadcast=True)

@socketio.on('touch')
def handle_touch(data):
    global last_timestamp, reaction_times, game_running

    if not game_running:
        return

    current_timestamp = datetime.now()
    if last_timestamp:
        reaction_time = (current_timestamp - last_timestamp).total_seconds()
        reaction_times.append(reaction_time)
        print(f"⏱️ Reaktion: {reaction_time:.2f} Sekunden")
    last_timestamp = current_timestamp

    emit('next', broadcast=True)

@socketio.on('end_game')
def handle_end_game():
    global game_running
    game_running = False
    print("🛑 Spiel beendet")

    if reaction_times:
        avg_reaction = sum(reaction_times) / len(reaction_times)
    else:
        avg_reaction = 0.0

    emit('game_summary', {
        'reaction_times': reaction_times,
        'avg_reaction': round(avg_reaction, 2),
        'clicks': len(reaction_times)
    }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
