
from flask import Flask, render_template, request, jsonify
from threading import Thread
import time
import random

app = Flask(__name__)

connected_pods = set()
required_pods = 4
game_settings = {
    'mode': 'Classic',
    'duration': 60,
    'interval': 3,
    'pause': 1,
    'multicolor': False,
    'memory_length': 5
}
current_color = 'red'
active = False
countdown_thread = None
remaining_time = 0
memory_sequence = []
memory_index = 0

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/pod/<int:pod_id>')
def pod(pod_id):
    return render_template('pod.html', pod_id=pod_id)

@app.route('/connect', methods=['POST'])
def connect():
    pod_id = request.json['pod_id']
    connected_pods.add(pod_id)
    return jsonify({'status': 'connected', 'connected_pods': list(connected_pods)})

@app.route('/status')
def status():
    return jsonify({
        'connected': list(connected_pods),
        'required': required_pods,
        'active': active,
        'remaining_time': remaining_time,
        'mode': game_settings['mode'],
        'sequence': memory_sequence if game_settings['mode'] == 'Memory' else []
    })

@app.route('/update_settings', methods=['POST'])
def update_settings():
    global required_pods, game_settings
    data = request.json
    game_settings.update(data)
    required_pods = int(data.get('pods', 4))
    return jsonify({'status': 'settings updated'})

@app.route('/start', methods=['POST'])
def start():
    global active, countdown_thread, remaining_time, memory_sequence, memory_index
    if not active:
        active = True
        remaining_time = int(game_settings['duration']) * 60
        if game_settings['mode'] == 'Memory':
            memory_sequence = [random.choice(sorted(connected_pods)) for _ in range(game_settings['memory_length'])]
            memory_index = 0
        countdown_thread = Thread(target=game_loop)
        countdown_thread.start()
    return jsonify({'status': 'started'})

@app.route('/stop', methods=['POST'])
def stop():
    global active, remaining_time
    active = False
    remaining_time = 0
    return jsonify({'status': 'stopped'})

@app.route('/touch', methods=['POST'])
def touch():
    global memory_index, active
    pod_id = request.json['pod_id']
    if not active:
        return jsonify({'status': 'inactive'})
    if game_settings['mode'] == 'Touch to Switch':
        return jsonify({'status': 'next'})
    elif game_settings['mode'] == 'Memory':
        expected = memory_sequence[memory_index]
        if pod_id == expected:
            memory_index += 1
            if memory_index >= len(memory_sequence):
                memory_index = 0
            return jsonify({'status': 'correct'})
        else:
            memory_index = 0
            return jsonify({'status': 'wrong'})
    return jsonify({'status': 'ignored'})

def game_loop():
    global remaining_time, active
    while remaining_time > 0 and active:
        pod_id = random.choice(sorted(connected_pods))
        color = random.choice(['red', 'blue', 'green', 'yellow']) if game_settings['multicolor'] else 'red'
        app.config['active_pod'] = pod_id
        app.config['active_color'] = color
        time.sleep(game_settings['interval'])
        app.config['active_pod'] = None
        time.sleep(game_settings['pause'])
        remaining_time -= game_settings['interval'] + game_settings['pause']
    active = False

if __name__ == '__main__':
    app.run(debug=True)
