#!/usr/bin/env python3
# detect_and_server.py
# MobileNet-SSD detection + simple TCP server that sends JSON messages of detected objects.

import cv2, time, json, socket, threading
from datetime import datetime

# ------------ Config ------------
MODEL_PROTOTXT = "deploy.prototxt"
MODEL_WEIGHTS  = "mobilenet_iter_73000.caffemodel"
CONF_THRESHOLD = 0.45
FRAME_WIDTH  = 320   # reduce for speed
FRAME_HEIGHT = 240
PROCESS_EVERY_N_FRAMES = 2  # process every n-th frame to save CPU
TCP_LISTEN_IP = "0.0.0.0"   # listen on all interfaces
TCP_LISTEN_PORT = 5000      # pick a free port (>=1024)
# ---------------------------------

CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
           "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
           "dog", "horse", "motorbike", "person", "pottedplant",
           "sheep", "sofa", "train", "tvmonitor"]

# Load model (OpenCV DNN)
net = cv2.dnn.readNetFromCaffe(MODEL_PROTOTXT, MODEL_WEIGHTS)

# Camera init
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

if not cap.isOpened():
    print("ERROR: Cannot open camera")
    raise SystemExit(1)

# Server state
clients = []
clients_lock = threading.Lock()

def client_handler(conn, addr):
    print(f"[TCP] Client connected {addr}")
    try:
        # keep the connection open until client disconnects
        while True:
            # just block on recv; if returns 0-length -> disconnected
            data = conn.recv(1)
            if not data:
                break
            # ignore incoming data (we only push from server), but keep connection alive
    except Exception as e:
        print("[TCP] client_handler error:", e)
    finally:
        with clients_lock:
            try:
                clients.remove(conn)
            except ValueError:
                pass
        try:
            conn.close()
        except:
            pass
        print(f"[TCP] Client disconnected {addr}")

def server_thread():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((TCP_LISTEN_IP, TCP_LISTEN_PORT))
    srv.listen(5)
    print(f"[TCP] Listening on {TCP_LISTEN_IP}:{TCP_LISTEN_PORT}")
    while True:
        conn, addr = srv.accept()
        with clients_lock:
            clients.append(conn)
        t = threading.Thread(target=client_handler, args=(conn, addr), daemon=True)
        t.start()

def broadcast_message(obj_list):
    """Send JSON message to all connected clients. Non-blocking best-effort."""
    if not obj_list:
        return
    payload = {
        "ts": datetime.utcnow().isoformat(),
        "objects": obj_list
    }
    data = (json.dumps(payload) + "\n").encode()
    with clients_lock:
        dead = []
        for c in clients:
            try:
                c.sendall(data)
            except Exception as e:
                # mark dead for cleanup
                dead.append(c)
        for d in dead:
            try:
                clients.remove(d)
            except ValueError:
                pass

# Start server listener thread
thr = threading.Thread(target=server_thread, daemon=True)
thr.start()

print("Starting detection loop. Press Ctrl+C to quit.")
last_sent = ""  # remember last sent set to reduce duplicates
frame_count = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        frame_count += 1
        if frame_count % PROCESS_EVERY_N_FRAMES != 0:
            # optionally show preview but skip processing - you can also remove imshow for speed
            cv2.imshow("Preview", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)),
                                     0.007843, (300, 300), 127.5)
        net.setInput(blob)
        detections = net.forward()

        detected = []
        for i in range(detections.shape[2]):
            conf = float(detections[0, 0, i, 2])
            if conf > CONF_THRESHOLD:
                idx = int(detections[0, 0, i, 1])
                label = CLASSES[idx]
                detected.append(label)
                # draw box for preview
                box = detections[0, 0, i, 3:7] * [w, h, w, h]
                (startX, startY, endX, endY) = box.astype("int")
                cv2.rectangle(frame, (startX, startY), (endX, endY), (0,255,0), 2)
                cv2.putText(frame, f"{label} {conf:.2f}", (startX, max(startY-5,0)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,255,0), 1)

        unique = sorted(set(detected))
        msg = ",".join(unique) if unique else ""
        if msg and msg != last_sent:
            print("[DETECT] ->", unique)
            broadcast_message(unique)
            last_sent = msg
        elif not msg:
            last_sent = ""

        # preview window (optional - remove to save CPU)
        cv2.imshow("Detection Preview", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("Stopping...")

finally:
    cap.release()
    cv2.destroyAllWindows()
    print("Server exiting.")
	
