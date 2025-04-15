
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import threading
import time
import random

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

connected_pods = set()
stop_event = threading.Event()

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
    emit('pod_status', {'connected_pods': list(connected_pods)}, broadcast=True)

@socketio.on('disconnect_pod')
def handle_disconnect_pod(data):
    pod_id = data['pod_id']
    connected_pods.discard(pod_id)
    emit('pod_status', {'connected_pods': list(connected_pods)}, broadcast=True)

@socketio.on('start_game')
def handle_start_game(data):
    stop_event.clear()
    duration = int(data['duration'])
    interval = float(data['interval'])
    pause = float(data['pause'])
    mode = data.get('mode', 'classic')
    use_colors = data.get('use_colors', False)
    pod_count = int(data.get('required_pods', 4))

    colors = ['red', 'blue', 'green', 'yellow'] if use_colors else ['red']
    active_pods = sorted(list(connected_pods))[:pod_count]

    def game_loop():
        end_time = time.time() + duration * 60
        current_index = 0
        waiting_for_click = False

        while time.time() < end_time and not stop_event.is_set():
            if not active_pods:
                break
            pod_id = active_pods[current_index % len(active_pods)]
            color = random.choice(colors)

            socketio.emit('blink', {'pod_id': pod_id, 'color': color})

            if mode == 'touch':
                waiting_for_click = True
                while waiting_for_click and not stop_event.is_set():
                    socketio.sleep(0.1)
            else:
                socketio.sleep(interval)

            socketio.emit('blink', {'pod_id': pod_id, 'color': 'black'})
            socketio.sleep(pause)
            current_index += 1

        socketio.emit('game_over')

    threading.Thread(target=game_loop).start()

@socketio.on('pod_clicked')
def handle_pod_clicked(data):
    global stop_event
    stop_event.set()
    stop_event.clear()
    emit('next_touch', broadcast=True)

@socketio.on('stop_game')
def handle_stop_game():
    stop_event.set()
    socketio.emit('game_stopped')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000, allow_unsafe_werkzeug=True)
