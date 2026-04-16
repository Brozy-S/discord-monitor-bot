from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json
import os
import subprocess
import threading

app = Flask(__name__)
CORS(app)

# Store messages in memory (use database for production)
messages = []
MAX_MESSAGES = 100

def run_bot():
    """Start the Discord bot as a background process"""
    print("🚀 Starting Discord Bot...")
    # On Render/Linux, 'python' is usually correct. 
    subprocess.Popen(["python", "bot.py"])

@app.route('/api/messages', methods=['POST'])
def receive_message():
    """Receive message from Discord bot"""
    data = request.json
    data['receivedAt'] = datetime.utcnow().isoformat()
    
    messages.insert(0, data)
    
    # Keep only last 100 messages
    if len(messages) > MAX_MESSAGES:
        messages.pop()
    
    print(f"📨 New message from {data['user']['username']}: {data['content'][:50]}...")
    return jsonify({"status": "success", "id": data['messageId']})

@app.route('/api/messages', methods=['GET'])
def get_messages():
    """Send messages to dashboard"""
    return jsonify(messages)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics"""
    unique_users = len(set(m['user']['id'] for m in messages))
    today = datetime.utcnow().strftime('%Y-%m-%d')
    today_count = len([m for m in messages if m['timestamp'].startswith(today)])
    
    return jsonify({
        "total": len(messages),
        "uniqueUsers": unique_users,
        "today": today_count
    })

# Serve the dashboard HTML
@app.route('/')
def dashboard():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    # Start bot in a separate process
    run_bot()
    
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Server starting on port {port}")
    app.run(host='0.0.0.0', port=port)
