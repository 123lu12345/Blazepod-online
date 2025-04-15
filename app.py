from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Thread, Event
import random
import time

app = Flask(__name__)
socketio = SocketIO(app)
connected_pods = set()
game_thread = None
stop_event = Event()
countdown_thread = None
current_mode = "Classic"
memory_sequence = []
memory_index = 0

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/pod/<int:pod_id>')
def pod(pod_id):
    return render_template('pod.html', pod_id=pod_id)

@socketio.on('connect_pod')
def handle_connect_pod(data):
    pod_id = data['pod_id']
    connected_pods.add(pod_id)
    emit('pod_connection_update', list(connected_pods), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    # Optional: implement specific pod disconnect logic
    pass

@socketio.on('start_game')
def start_game(settings):
    global game_thread, stop_event, current_mode, memory_sequence, memory_index
    stop_event.clear()
    current_mode = settings.get("mode", "Classic")
    duration = int(settings.get("duration", 5)) * 60
    interval = float(settings.get("interval", 3))
    pause = float(settings.get("pause", 1))
    pods_required = int(settings.get("pods_required", 4))
    memory_length = int(settings.get("memory_length", 5))
    multi_color = settings.get("multi_color", False)

    active_pods = sorted(list(connected_pods))[:pods_required]

    if len(active_pods) < pods_required:
        emit('not_enough_pods', broadcast=True)
        return

    if countdown_thread and countdown_thread.is_alive():
        pass  # Already running
    else:
        def countdown():
            remaining = 10
            while remaining >= 0 and not stop_event.is_set():
                socketio.emit("countdown", {"remaining": remaining})
                time.sleep(1)
                remaining -= 1
        global countdown_thread
        countdown_thread = Thread(target=countdown)
        countdown_thread.start()
        countdown_thread.join()

    def game_loop():
        end_time = time.time() + duration
        if current_mode == "Memory":
            memory_sequence.clear()
            memory_index = 0
            memory_sequence.extend(random.choices(active_pods, k=memory_length))
            for pod in memory_sequence:
                if stop_event.is_set():
                    break
                socketio.emit("activate_pod", {"pod_id": pod, "color": "red" if not multi_color else random.choice(["red", "blue", "green", "yellow"])})
                time.sleep(interval)
                socketio.emit("deactivate_all")
                time.sleep(pause)

            socketio.emit("memory_ready", {"sequence": memory_sequence})
        else:
            while time.time() < end_time and not stop_event.is_set():
                chosen = random.choice(active_pods)
                socketio.emit("activate_pod", {"pod_id": chosen, "color": "red" if not multi_color else random.choice(["red", "blue", "green", "yellow"])})
                time.sleep(interval)
                socketio.emit("deactivate_all")
                time.sleep(pause)

        if not stop_event.is_set():
            socketio.emit("game_ended", {"message": "Spiel beendet"})

    game_thread = Thread(target=game_loop)
    game_thread.start()

@socketio.on('stop_game')
def stop_game():
    global stop_event
    stop_event.set()
    socketio.emit("deactivate_all")
    socketio.emit("game_ended", {"message": "Spiel abgebrochen"})

@socketio.on('pod_clicked')
def pod_clicked(data):
    global memory_index
    pod_id = data["pod_id"]
    if current_mode == "Memory":
        if memory_index < len(memory_sequence) and memory_sequence[memory_index] == pod_id:
            memory_index += 1
            if memory_index == len(memory_sequence):
                socketio.emit("memory_complete", {"message": "Reihenfolge korrekt abgeschlossen!"})
        else:
            socketio.emit("memory_failed", {"message": "Falsche Reihenfolge!"})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)