
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app)

connected_pods = set()
start_time = None
reaction_times = []
hit_times = []

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/pod/<int:pod_id>')
def pod(pod_id):
    return render_template('pod.html', pod_id=pod_id)

@socketio.on('connect')
def handle_connect():
    print("Client verbunden")

@socketio.on('pod_ready')
def handle_pod_ready(data):
    pod_id = data['pod_id']
    connected_pods.add(pod_id)
    print(f"✅ Pod {pod_id} verbunden")
    emit('update_connected_pods', list(connected_pods), broadcast=True)

@socketio.on('start_game')
def start_game(data):
    global start_time, reaction_times, hit_times
    start_time = time.time()
    reaction_times = []
    hit_times = []
    emit('game_started', data, broadcast=True)
    print(f"🕒 Spiel gestartet mit Daten: {data}")

@socketio.on('pod_touched')
def pod_touched(data):
    global reaction_times, hit_times
    timestamp = time.time()
    reaction_time = timestamp - start_time if start_time else 0
    reaction_times.append(reaction_time)
    hit_times.append(timestamp)
    print(f"🎯 Treffer! Reaktionszeit: {reaction_time:.2f} Sekunden")
    emit('reaction_time', {'reaction_time': reaction_time}, broadcast=True)

@socketio.on('end_game')
def end_game():
    global reaction_times
    if not reaction_times:
        average = 0
    else:
        average = sum(reaction_times) / len(reaction_times)
    print("🛑 Spiel beendet")
    emit('game_ended', {
        'average_reaction_time': round(average, 2),
        'hits': len(reaction_times),
        'individual_times': [round(t, 2) for t in reaction_times]
    }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
