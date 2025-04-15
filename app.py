from flask import Flask, render_template, request, jsonify
import threading, random, time

app = Flask(__name__)
connected_pods = set()
game_settings = {}
active_pod = None
active_color = "red"
game_running = False
touched = False

@app.route('/')
def dashboard():
    return render_template('dashboard_touch.html')

@app.route('/pod/<int:pod_id>')
def pod(pod_id):
    return render_template('pod_touch.html')

@app.route('/connect', methods=['POST'])
def connect():
    connected_pods.add(request.json['pod_id'])
    return '', 204

@app.route('/status')
def status():
    return jsonify({
        "active_pod": active_pod,
        "active_color": active_color,
        "running": game_running
    })

@app.route('/start_game', methods=['POST'])
def start_game():
    global game_running, game_settings
    game_settings = request.json
    game_running = True
    threading.Thread(target=game_loop).start()
    return '', 204

@app.route('/stop_game', methods=['POST'])
def stop_game():
    global game_running
    game_running = False
    return '', 204

@app.route('/touch', methods=['POST'])
def touch():
    global touched
    if game_settings.get("mode") == "touch":
        touched = True
    return '', 204

def game_loop():
    global active_pod, active_color, touched, game_running
    duration = game_settings.get("duration", 1) * 60
    interval = game_settings.get("interval", 2)
    pause = game_settings.get("pause", 1)
    mode = game_settings.get("mode", "classic")
    start = time.time()
    while game_running and time.time() - start < duration:
        if not connected_pods:
            time.sleep(1)
            continue
        active_pod = random.choice(list(connected_pods))
        active_color = random.choice(["red", "blue", "green", "yellow"])
        if mode == "touch":
            touched = False
            while not touched and game_running and time.time() - start < duration:
                time.sleep(0.1)
        else:
            time.sleep(interval)
        active_pod = None
        time.sleep(pause)
    game_running = False
