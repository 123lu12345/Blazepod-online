from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app)

connected_pods = set()
required_pods = 4
game_running = False
countdown_thread = None

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/pod/<int:pod_id>')
def pod(pod_id):
    return render_template('pod.html', pod_id=pod_id)

@socketio.on('register')
def handle_register(data):
    pod_id = data['pod_id']
    connected_pods.add(pod_id)
    socketio.emit('update_connected', list(connected_pods))
    check_pods_ready()

@socketio.on('unregister')
def handle_unregister(data):
    pod_id = data['pod_id']
    connected_pods.discard(pod_id)
    socketio.emit('update_connected', list(connected_pods))

@socketio.on('start_game')
def start_game(data):
    global game_running, countdown_thread
    if not game_running:
        game_running = True
        countdown_thread = threading.Thread(target=run_game, args=(data,))
        countdown_thread.start()

@socketio.on('stop_game')
def stop_game():
    global game_running
    game_running = False
    socketio.emit('game_stopped')

def run_game(settings):
    global game_running
    duration = int(settings.get("duration", 1)) * 60
    interval = float(settings.get("interval", 1))
    pause = float(settings.get("pause", 1))
    mode = settings.get("mode", "Classic")
    use_colors = settings.get("colors", False)
    required = int(settings.get("required_pods", 4))
    memory_length = int(settings.get("memory_length", 5))

    start_time = time.time()
    socketio.emit('countdown_start', {'seconds': 10})
    time.sleep(10)

    if not game_running:
        return

    socketio.emit('game_started', {'mode': mode})

    if mode == "Memory":
        sequence = random.choices(list(connected_pods)[:required], k=memory_length)
        for pod in sequence:
            socketio.emit('activate', {'pod_id': pod, 'color': random_color() if use_colors else 'red'})
            time.sleep(interval)
            socketio.emit('deactivate_all')
            time.sleep(pause)
        socketio.emit('memory_sequence', {'sequence': sequence})
    else:
        last_pod = None
        while game_running and time.time() - start_time < duration:
            available_pods = list(connected_pods)[:required]
            if not available_pods:
                break
            pod = random.choice([p for p in available_pods if p != last_pod])
            color = random_color() if use_colors else 'red'
            socketio.emit('activate', {'pod_id': pod, 'color': color})
            if mode == "Touch to Switch":
                socketio.sleep(30)
            else:
                time.sleep(interval)
                socketio.emit('deactivate_all')
                time.sleep(pause)
            last_pod = pod

    if game_running:
        socketio.emit('game_finished')
    else:
        socketio.emit('game_stopped')

    game_running = False

def random_color():
    return random.choice(['red', 'blue', 'green', 'yellow'])

def check_pods_ready():
    socketio.emit('update_ready', len(connected_pods))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000, allow_unsafe_werkzeug=True)