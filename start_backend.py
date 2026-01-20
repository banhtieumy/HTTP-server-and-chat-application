#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_backend
~~~~~~~~~~~~~~~~~

This module provides a simple entry point for deploying backend server process
using the socket framework. It parses command-line arguments to configure the
server's IP address and port, and then launches the backend server.
"""

import socket
import argparse
import threading

from daemon import create_backend
from daemon.weaprous import WeApRous
from daemon.utils import *

# Default port number used if none is specified via command-line arguments.
PORT = 9000

# Global peer tracking for chat application
peer_list = []
peer_list_lock = threading.Lock()

# Global message queue for real-time messaging
# Structure: { 'peer_name': [ {from, message, timestamp}, ... ] }
message_queues = {}
message_queues_lock = threading.Lock()

# Channel message history (persistent during server run)
# Structure: { 'channel_name': [ {from, message, timestamp}, ... ] }
channel_history = {
    'general': [],
    'random': [],
    'tech': []
}
channel_history_lock = threading.Lock()

# Create WeApRous app with chat routes
app = WeApRous()

# CORS middleware - Add CORS headers to all responses
def add_cors_headers(response):
    """Add CORS headers to allow cross-origin requests from ngrok."""
    if isinstance(response, dict):
        # WeApRous returns dict, we need to add headers in the framework
        pass
    return response
# THÊM đoạn code này vào file start_backend.py, trước dòng if __name__ == "__main__":

@app.route("/health", methods=["GET", "HEAD"])
def health_check(headers="", body=""):
    """Health check endpoint for proxies and load balancers"""
    import time
    return {
        "status": "healthy",
        "service": "chat_backend", 
        "timestamp": time.time(),
        "version": "1.0",
        "peers_count": len(peer_list)
    }
@app.route("/submit-info", methods=["POST"])
def submit_info(headers="guest", body="anonymous"):
    """Register a new peer with the tracker server."""
    print("[ChatApp] Received peer registration request")
    print("[DEBUG] Headers:", headers)
    
    # Parse form data
    peer_data = {}
    if body:
        for param in body.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                peer_data[key] = value
    
    name = peer_data.get('name', 'Unknown')
    ip = peer_data.get('ip', '127.0.0.1')
    port = peer_data.get('port', '5000')
    
    # Add to peer list
    with peer_list_lock:
        # Check if peer already exists
        existing = False
        for peer in peer_list:
            if peer['name'] == name:
                peer['ip'] = ip  # Update IP
                peer['port'] = port  # Update port
                existing = True
                break
        
        if not existing:
            peer_list.append({
                'name': name,
                'ip': ip,
                'port': port
            })
        with open("db/peers.json", "w") as f:
            f.write("[\n")
            for i, p in enumerate(peer_list):
                if i == len(peer_list) - 1:  # Last item - no comma
                    f.write('    {{"name": "{}", "ip": "{}", "port": "{}"}}\n'.format(p['name'], p['ip'], p['port']))
                else:
                    f.write('    {{"name": "{}", "ip": "{}", "port": "{}"}},\n'.format(p['name'], p['ip'], p['port']))
            f.write("]\n")
     # Initialize message queue for this peer
    with message_queues_lock:
        if name not in message_queues:
            message_queues[name] = []
    
    print("[ChatApp] Registered peer: {} at {}:{}".format(name, ip, port))
    print("[ChatApp] Total peers: {}".format(len(peer_list)))
    
    return {"status": "success", "message": "Peer registered: {} at {}:{}".format(name, ip, port)}


@app.route("/add-list", methods=["POST"])
def add_list(headers="guest", body="anonymous"):
    """Alternative endpoint for adding peers to the list."""
    return submit_info(headers, body)


@app.route("/get-list", methods=["GET"])
def get_list(headers="guest", body="anonymous"):
    """Get the list of all active peers."""
    print("[ChatApp] Peer list requested")
    
    with peer_list_lock:
        peers = list(peer_list)  # Create a copy
    
    return {"peers": peers, "count": len(peers)}


@app.route("/connect-peer", methods=["POST"])
def connect_peer(headers="guest", body="anonymous"):
    """Establish connection with a specific peer."""
    print("[ChatApp] Peer connection request")
    
    # Parse form data
    data = {}
    if body:
        for param in body.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                data[key] = value
    
    target_ip = data.get('target_ip', '')
    target_port = data.get('target_port', '')
    
    print("[ChatApp] Connecting to peer: {}:{}".format(target_ip, target_port))
    
    return {"status": "success", "message": "Connection established"}


@app.route("/send-peer", methods=["POST"])
def send_peer(headers="guest", body="anonymous"):
    """Send a message to a specific peer (P2P direct messaging)."""
    print("[ChatApp] Direct message request")
    
    # Parse form data
    data = {}
    if body:
        for param in body.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                # URL decode
                value = value.replace('+', ' ')
                try:
                    # Simple URL decode for %20, %21, etc
                    import urllib.parse
                    value = urllib.parse.unquote(value)
                except:
                    pass
                data[key] = value
    
    sender_name = data.get('sender_name', 'Anonymous')
    target_name = data.get('target_name', '')
    message = data.get('message', '')
    channel = data.get('channel', 'general')  # Get channel
    
    print("[ChatApp] Message from {} to {} [{}]: {}".format(sender_name, target_name, channel, message))
    
    # Find target peer
    target_found = False
    with peer_list_lock:
        for peer in peer_list:
            if peer['name'] == target_name:
                target_found = True
                break
    
    if target_found:
        # Add message to BOTH target's and sender's queue (for echo-back)
        import time
        msg_data = {
            'from': sender_name,
            'to': target_name,
            'message': message,
            'type': 'direct',
            'channel': channel,
            'timestamp': time.time()
        }
        
        with message_queues_lock:
            # Queue for receiver
            if target_name not in message_queues:
                message_queues[target_name] = []
            message_queues[target_name].append(msg_data.copy())
            
            # Queue for sender (echo-back)
            if sender_name not in message_queues:
                message_queues[sender_name] = []
            message_queues[sender_name].append(msg_data.copy())

            save_message_queue()
        
        print("[ChatApp] DM queued: {} -> {}".format(sender_name, target_name))
        return {"status": "success", "message": "Message sent to {}".format(target_name)}
    else:
        return {"status": "error", "message": "Peer {} not found".format(target_name)}


@app.route("/broadcast-peer", methods=["POST"])
def broadcast_peer(headers="guest", body="anonymous"):
    """Broadcast a message to all connected peers."""
    print("[ChatApp] Broadcast message request")
    
    # Parse form data
    data = {}
    if body:
        for param in body.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                # URL decode
                value = value.replace('+', ' ')
                try:
                    import urllib.parse
                    value = urllib.parse.unquote(value)
                except:
                    pass
                data[key] = value
    
    sender_name = data.get('sender_name', 'Anonymous')
    message = data.get('message', '')
    channel = data.get('channel', 'general')  # Get channel
    
    print("[ChatApp] Broadcast from {} [{}]: {}".format(sender_name, channel, message))
    
    # Add message to channel history (persistent)
    import time
    msg_data = {
        'from': sender_name,
        'message': message,
        'type': 'broadcast',
        'channel': channel,
        'timestamp': time.time()
    }
    
    with channel_history_lock:
        if channel in channel_history:
            channel_history[channel].append(msg_data)
            # Keep only last 100 messages per channel
            if len(channel_history[channel]) > 100:
                channel_history[channel] = channel_history[channel][-100:]
    
    # Add message to ALL peers' queues (including sender to see confirmation)
    broadcast_count = 0
    
    # Get all registered peers
    with peer_list_lock:
        all_peers = [p['name'] for p in peer_list]
    
    print("[ChatApp] Broadcasting to peers: {}".format(all_peers))
    
    with message_queues_lock:
        for peer_name in all_peers:
            # Ensure queue exists
            if peer_name not in message_queues:
                message_queues[peer_name] = []
            
            message_queues[peer_name].append(msg_data.copy())
            broadcast_count += 1
    
    print("[ChatApp] Broadcast queued for {} peers (including sender)".format(broadcast_count))
    
    return {"status": "success", "message": "Broadcast sent", "peer_count": broadcast_count}


@app.route('/get-messages', methods=['POST'])
def get_messages(headers="guest", body="anonymous"):
    # Parse form data
    data = {}
    if body:
        for param in body.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                # URL decode
                try:
                    import urllib.parse
                    value = urllib.parse.unquote(value)
                except:
                    pass
                data[key] = value
    
    peer_name = data.get('peer_name', '').strip()
    
    if not peer_name:
        return {'status': 'error', 'message': 'Missing peer_name'}
    
    with message_queues_lock:
        messages = message_queues.get(peer_name, [])
        message_queues[peer_name] = []  # Clear after reading
    
    return {'status': 'success', 'messages': messages}

@app.route('/get-channel-history', methods=['POST'])
def get_channel_history(headers="guest", body="anonymous"):
    """Get full message history for a specific channel."""
    # Parse form data
    data = {}
    if body:
        for param in body.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                try:
                    import urllib.parse
                    value = urllib.parse.unquote(value)
                except:
                    pass
                data[key] = value
    
    channel_name = data.get('channel', 'general').strip()
    
    with channel_history_lock:
        history = channel_history.get(channel_name, [])
    
    print("[ChatApp] Channel history requested for #{}: {} messages".format(channel_name, len(history)))
    return {'status': 'success', 'messages': history, 'channel': channel_name}

@app.route('/unregister', methods=['POST'])
def unregister(headers="guest", body="anonymous"):
    # Parse form data
    data = {}
    if body:
        for param in body.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                # URL decode
                try:
                    import urllib.parse
                    value = urllib.parse.unquote(value)
                except:
                    pass
                data[key] = value
    
    peer_name = data.get('name', '').strip()
    
    if not peer_name:
        return {'status': 'error', 'message': 'Missing name'}
    
    with peer_list_lock:
        global peer_list
        peer_list = [p for p in peer_list if p['name'] != peer_name]
    
    with message_queues_lock:
        if peer_name in message_queues:
            del message_queues[peer_name]
    
    print(f"[Unregister] {peer_name} disconnected")
    return {'status': 'success', 'message': f'{peer_name} unregistered'} 

if __name__ == "__main__":
    """
    Entry point for launching the backend server.

    This block parses command-line arguments to determine the server's IP address
    and port. It then calls `create_backend(ip, port)` to start the RESTful
    application server.

    :arg --server-ip (str): IP address to bind the server (default: 127.0.0.1).
    :arg --server-port (int): Port number to bind the server (default: 9000).
    """

    parser = argparse.ArgumentParser(
        prog='Backend',
        description='Start the backend process',
        epilog='Backend daemon for http_deamon application'
    )
    parser.add_argument('--server-ip',
        type=str,
        default='0.0.0.0',
        help='IP address to bind the server. Default is 0.0.0.0'
    )
    parser.add_argument(
        '--server-port',
        type=int,
        default=PORT,
        help='Port number to bind the server. Default is {}.'.format(PORT)
    )
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    print("="*60)
    print("Backend Server with Authentication + Real-Time Chat")
    print("="*60)
    print("Starting server on {}:{}".format(ip, port))
    print("Available endpoints:")
    print("  - POST /login (authentication)")
    print("  - GET  /index.html (with cookie auth)")
    print("  - POST /submit-info (peer registration)")
    print("  - GET  /get-list (peer discovery)")
    print("  - POST /send-peer (direct messaging)")
    print("  - POST /broadcast-peer (broadcast)")
    print("  - POST /get-messages (fetch pending messages)")
    print("  - Chat UI: http://localhost:{}/chat.html".format(port))
    print("="*60)

    # Prepare and run the app with routes
    app.prepare_address(ip, port)
    with peer_list_lock:
        peer_list = load_peer_list()
    with message_queues_lock:
        message_queues = load_message_queue()
    app.run()
