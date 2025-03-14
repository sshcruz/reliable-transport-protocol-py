import random
import heapq

class Message:
    def __init__(self, data):
        self.data = data[:20]

class Packet:
    def __init__(self, seqnum, acknum, payload=""):
        self.seqnum = seqnum
        self.acknum = acknum
        self.payload = payload[:20]
        self.checksum = self.compute_checksum()

    def compute_checksum(self):
        return self.seqnum + self.acknum + sum(ord(c) for c in self.payload)

class Sender:
    WAIT_LAYER5 = 0
    WAIT_ACK = 1

    def __init__(self):
        self.state = self.WAIT_LAYER5
        self.seq = 0
        self.estimated_rtt = 15
        self.last_packet = None

class Receiver:
    def __init__(self):
        self.seq = 0

A = Sender()
B = Receiver()
event_queue = []
time = 0.0

def start_timer(entity, duration):
    heapq.heappush(event_queue, (time + duration, "TIMER_INTERRUPT", entity))

def stop_timer(entity):
    global event_queue
    event_queue = [e for e in event_queue if not (e[1] == "TIMER_INTERRUPT" and e[2] == entity)]
    heapq.heapify(event_queue)

def to_layer3(entity, packet):
    heapq.heappush(event_queue, (time + random.uniform(5, 10), "FROM_LAYER3", entity, packet))

def to_layer5(entity, data):
    print(f"Layer 5 received at entity {entity}: {data}")

def A_output(message):
    if A.state != Sender.WAIT_LAYER5:
        print(f"A_output: Waiting for ACK, dropping message: {message.data}")
        return
    print(f"A_output: Sending packet: {message.data}")
    packet = Packet(A.seq, 0, message.data)
    A.last_packet = packet
    A.state = Sender.WAIT_ACK
    to_layer3(0, packet)
    start_timer(0, A.estimated_rtt)

def A_input(packet):
    if A.state != Sender.WAIT_ACK:
        print("A_input: Unexpected state, dropping packet.")
        return
    if packet.checksum != packet.compute_checksum():
        print("A_input: Corrupt ACK, dropping.")
        return
    if packet.acknum != A.seq:
        print("A_input: Unexpected ACK, dropping.")
        return
    print("A_input: ACK received.")
    stop_timer(0)
    A.seq = 1 - A.seq
    A.state = Sender.WAIT_LAYER5

def A_timerinterrupt():
    if A.state != Sender.WAIT_ACK:
        print("A_timerinterrupt: No pending ACK, ignoring.")
        return
    print(f"A_timerinterrupt: Resending packet: {A.last_packet.payload}")
    to_layer3(0, A.last_packet)
    start_timer(0, A.estimated_rtt)

def A_init():
    A.state = Sender.WAIT_LAYER5
    A.seq = 0
    A.estimated_rtt = 15

def send_ack(entity, ack):
    packet = Packet(0, ack)
    to_layer3(entity, packet)

def B_input(packet):
    if packet.checksum != packet.compute_checksum():
        print("B_input: Corrupt packet, sending NAK.")
        send_ack(1, 1 - B.seq)
        return
    if packet.seqnum != B.seq:
        print("B_input: Unexpected sequence number, sending NAK.")
        send_ack(1, 1 - B.seq)
        return
    print(f"B_input: Received message: {packet.payload}")
    send_ack(1, B.seq)
    to_layer5(1, packet.payload)
    B.seq = 1 - B.seq

def B_init():
    B.seq = 0

def simulate():
    global time
    while event_queue:
        event = heapq.heappop(event_queue)
        time = event[0]
        if event[1] == "TIMER_INTERRUPT":
            if event[2] == 0:
                A_timerinterrupt()
        elif event[1] == "FROM_LAYER3":
            if event[2] == 0:
                A_input(event[3])
            else:
                B_input(event[3])

A_init()
B_init()
simulate()
