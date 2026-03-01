PC Remote Control is a lightweight Flask-based web app that turns your PC into a remotely accessible device for mouse/keyboard control, live audio streaming, and system commands.

Key Features
Mouse Control: Real-time relative mouse movement via WebSocket (/ws/mouse), plus click/double-click/scroll endpoints

Live Audio Capture: WASAPI loopback audio streaming to multiple WebSocket clients (/ws/audio) with automatic device detection

Media Keys: Play/pause, volume control, track navigation via simple POST requests

System Controls: Shutdown (with 5s delay) and cancel endpoints

PWA Ready: Manifest.json for standalone mobile app experience with portrait orientation

Zero-Config: Runs on 0.0.0.0:5000 - access via browser/IP anywhere on network

Tech Stack
Flask + Flask-Sock (WebSockets) + PyAutoGUI (mouse/keyboard) + pyaudiowpatch (WASAPI audio capture). Single server.py bundles to EXE via PyInstaller. Serves bundled index.html PWA.

Use Cases
Mobile remote control for PC gaming/workstation

Audio monitoring (hear PC output remotely)

IT admin toolkit for headless machines

Media center controller

Perfect for LAN or secure tunnel deployment. Note: Antivirus may flag due to automation features (common for remote tools).
