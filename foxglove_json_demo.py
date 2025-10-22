import socket, json, time

UDP_IP = "127.0.0.1"   # or your receiver address
UDP_PORT = 9999        # match your server
HZ = 50                # 50Hz
DT = 1.0 / HZ          # 20ms

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

velocity = 0.0
position = 0.0

def get_accel(t):
    if t < 1:       return 100 * t              # 0 to 100 in first 1s
    elif t < 4:     return 100                  # hold 100 until 4s
    elif t < 5:     return 100 - 100*(t-4)      # ramp down to 0 by 5s
    else:           return -position/1000

start = time.time()
while True:
    t = time.time() - start

    accel = get_accel(t)
    velocity += accel * DT
    position += velocity * DT

    msg = {
        "time": round(t, 3),
        "acceleration": accel,
        "velocity": velocity,
        "position": position,
    }

    encoded_msg = json.dumps(msg).encode("utf-8")
    sock.sendto(encoded_msg, (UDP_IP, UDP_PORT))

    print(msg)
    time.sleep(DT)
