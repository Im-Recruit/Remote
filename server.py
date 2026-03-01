from flask import Flask, request, jsonify, send_file
from flask_sock import Sock
import pyautogui
import logging
import json
import pyaudiowpatch as pyaudio
import threading
import os

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
sock = Sock(app)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# --- Audio state ---
audio_clients = set()
audio_clients_lock = threading.Lock()
audio_stream = None
pa_instance = None

CHUNK = 128

def get_loopback_device():
    p = pyaudio.PyAudio()
    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        print("❌ WASAPI not available")
        p.terminate()
        return None, None

    default_speakers = p.get_device_info_by_index(wasapi_info['defaultOutputDevice'])

    if not default_speakers.get('isLoopbackDevice', False):
        for loopback in p.get_loopback_device_info_generator():
            if default_speakers['name'] in loopback['name']:
                default_speakers = loopback
                break

    return p, default_speakers

def audio_callback(in_data, frame_count, time_info, status):
    with audio_clients_lock:
        dead = set()
        for client in audio_clients:
            try:
                client.send(in_data)
            except Exception:
                dead.add(client)
        for c in dead:
            audio_clients.discard(c)
    return (in_data, pyaudio.paContinue)

def start_audio_stream():
    global audio_stream, pa_instance
    if audio_stream is not None:
        return

    p, device = get_loopback_device()
    if device is None:
        return

    pa_instance = p
    channels = device['maxInputChannels']
    rate = int(device['defaultSampleRate'])
    print(f"✅ Capturing: {device['name']} | {channels}ch | {rate}Hz")

    audio_stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=rate,
        frames_per_buffer=CHUNK,
        input=True,
        input_device_index=device['index'],
        stream_callback=audio_callback
    )
    audio_stream.start_stream()

def stop_audio_stream():
    global audio_stream, pa_instance
    if audio_stream is not None:
        audio_stream.stop_stream()
        audio_stream.close()
        audio_stream = None
    if pa_instance is not None:
        pa_instance.terminate()
        pa_instance = None

# --- Routes ---
@app.route('/')
def index():
    return send_file('index.html')

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "PC Remote",
        "short_name": "Remote",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#111111",
        "theme_color": "#111111",
        "orientation": "portrait"
    })

@app.route('/audio/info')
def audio_info():
    p = pyaudio.PyAudio()
    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        device = p.get_device_info_by_index(wasapi_info['defaultOutputDevice'])
        rate = int(device['defaultSampleRate'])
        channels = int(device['maxOutputChannels'])
    except Exception:
        rate = 48000
        channels = 2
    finally:
        p.terminate()
    return jsonify(sampleRate=rate, channels=channels)

@sock.route('/ws/mouse')
def ws_mouse(ws):
    while True:
        data = ws.receive()
        if data is None:
            break
        try:
            msg = json.loads(data)
            pyautogui.moveRel(msg['dx'], msg['dy'], _pause=False)
        except Exception:
            pass

@sock.route('/ws/audio')
def ws_audio(ws):
    with audio_clients_lock:
        audio_clients.add(ws)
        if len(audio_clients) == 1:
            threading.Thread(target=start_audio_stream, daemon=True).start()
    try:
        while True:
            msg = ws.receive()
            if msg is None:
                break
    finally:
        with audio_clients_lock:
            audio_clients.discard(ws)
            if not audio_clients:
                stop_audio_stream()

@app.route('/mouse/click', methods=['POST'])
def mouse_click():
    btn = request.json.get('button', 'left')
    pyautogui.click(button=btn)
    return jsonify(ok=True)

@app.route('/mouse/doubleclick', methods=['POST'])
def mouse_doubleclick():
    pyautogui.doubleClick()
    return jsonify(ok=True)

@app.route('/mouse/scroll', methods=['POST'])
def mouse_scroll():
    pyautogui.scroll(request.json.get('amount', 8))
    return jsonify(ok=True)

@app.route('/media/<action>', methods=['POST'])
def media(action):
    keys = {
        'play':     'playpause',
        'next':     'nexttrack',
        'prev':     'prevtrack',
        'vol_up':   'volumeup',
        'vol_down': 'volumedown',
        'mute':     'volumemute'
    }
    if action in keys:
        pyautogui.press(keys[action])
    return jsonify(ok=True)

@app.route('/system/shutdown', methods=['POST'])
def shutdown():
    os.system('shutdown /s /t 5')
    return jsonify(ok=True, message='Shutting down in 5 seconds...')

@app.route('/system/cancel_shutdown', methods=['POST'])
def cancel_shutdown():
    os.system('shutdown /a')
    return jsonify(ok=True, message='Shutdown cancelled')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
