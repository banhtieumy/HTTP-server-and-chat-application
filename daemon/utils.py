import os
import json
PEER_LIST = "db/peers.jon"
MESSAGE_QUEUE_FILE = "db/message_queues.txt"

# ----------------------
# Peer list
# ----------------------
def save_peer_list(peer_list):
    """Save given peer list to file in JSON format"""
    try:
        with open(PEER_LIST, "w", encoding="utf-8") as f:
            json.dump(peer_list, f, indent=4)
        print("Saved peer list successfully")
        return True
    except Exception as e:
        print("[utils] save_peer_list error:", e)
        return False
def load_peer_list():
    """Load peer list from file - support both JSON and text formats"""
    try:
        if not os.path.exists(PEER_LIST):
            return []
            
        with open(PEER_LIST, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
            # Try to parse as JSON first
            if content.startswith('['):
                return json.loads(content)
            else:
                # Fallback to text format parsing
                peers = []
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse: name=Alice;ip=127.0.0.1;port=5001
                        parts = line.split(';')
                        peer = {}
                        for part in parts:
                            if '=' in part:
                                key, value = part.split('=', 1)
                                peer[key] = value
                        if peer:
                            peers.append(peer)
                return peers
                
    except Exception as e:
        print("[utils] load_peer_list error:", e)
        return []
# ----------------------
# Message queue
# ----------------------
def save_message_queue(message_queues):
    """Save message queues dict to file (line-by-line)"""
    try:
        with open(MESSAGE_QUEUE_FILE, "w", encoding="utf-8") as f:
            for peer, msgs in message_queues.items():
                for m in msgs:
                    line = "peer={};from={};to={};message={};type={};channel={};timestamp={}\n".format(
                        peer,
                        m.get('from',''),
                        m.get('to',''),
                        m.get('message',''),
                        m.get('type',''),
                        m.get('channel',''),
                        m.get('timestamp', 0)
                    )
                    f.write(line)
        print("Saved message queue successfully")
        return True
    except Exception as e:
        print("[utils] save_message_queue error:", e)
        return False

def load_message_queue():
    """Load message queues from file"""
    if not os.path.exists(MESSAGE_QUEUE_FILE):
        return {}

    queues = {}
    try:
        with open(MESSAGE_QUEUE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(";")
                m = {}
                peer = None
                for part in parts:
                    if "=" not in part:
                        continue
                    k, v = part.split("=", 1)
                    if k == "peer":
                        peer = v
                    else:
                        m[k] = v
                if peer:
                    if peer not in queues:
                        queues[peer] = []
                    # timestamp convert về float
                    if "timestamp" in m:
                        try:
                            m["timestamp"] = float(m["timestamp"])
                        except:
                            m["timestamp"] = 0
                    queues[peer].append(m)
        return queues
    except Exception as e:
        print("[utils] load_message_queue error:", e)
        return {}
