import random
import time

BUFSIZE = 64

class Message:
    def __init__(self, data):
        self.data = data[:20]  # Limitando a 20 caracteres

class Packet:
    def __init__(self, seqnum=0, acknum=0, payload=""):
        self.seqnum = seqnum
        self.acknum = acknum
        self.payload = payload[:20]
        self.checksum = self.calculate_checksum()

    def calculate_checksum(self):
        checksum = self.seqnum + self.acknum
        checksum += sum(ord(char) for char in self.payload)
        return checksum

class Sender:
    def __init__(self, window_size=8, estimated_rtt=15):
        self.base = 1
        self.nextseq = 1
        self.window_size = window_size
        self.estimated_rtt = estimated_rtt
        self.buffer_next = 1
        self.packet_buffer = [None] * BUFSIZE

    def send_window(self):
        while self.nextseq < self.buffer_next and self.nextseq < self.base + self.window_size:
            packet = self.packet_buffer[self.nextseq % BUFSIZE]
            if packet:
                print(f"Enviando pacote (seq={packet.seqnum}): {packet.payload}")
                to_layer3(0, packet)
                if self.base == self.nextseq:
                    start_timer(0, self.estimated_rtt)
                self.nextseq += 1

    def output(self, message):
        if self.buffer_next - self.base >= BUFSIZE:
            print(f"Buffer cheio. Descartando mensagem: {message.data}")
            return
        print(f"Armazenando pacote (seq={self.buffer_next}): {message.data}")
        packet = Packet(seqnum=self.buffer_next, payload=message.data)
        self.packet_buffer[self.buffer_next % BUFSIZE] = packet
        self.buffer_next += 1
        self.send_window()

    def input(self, packet):
        if packet.checksum != packet.calculate_checksum():
            print(f"Pacote corrompido. Ignorando.")
            return
        if packet.acknum < self.base:
            print(f"ACK duplicado. Ignorando.")
            return
        print(f"Recebido ACK (ack={packet.acknum})")
        self.base = packet.acknum + 1
        if self.base == self.nextseq:
            stop_timer(0)
            print("Parando timer")
        else:
            start_timer(0, self.estimated_rtt)

    def timer_interrupt(self):
        print("Timeout! Reenviando pacotes não confirmados.")
        for i in range(self.base, self.nextseq):
            packet = self.packet_buffer[i % BUFSIZE]
            if packet:
                print(f"Reenviando pacote (seq={packet.seqnum}): {packet.payload}")
                to_layer3(0, packet)
        start_timer(0, self.estimated_rtt)

class Receiver:
    def __init__(self):
        self.expect_seq = 1
        self.packet_to_send = Packet(seqnum=-1, acknum=0)

    def input(self, packet):
        if packet.checksum != packet.calculate_checksum():
            print(f"Pacote corrompido. Enviando NAK (ack={self.packet_to_send.acknum})")
            to_layer3(1, self.packet_to_send)
            return
        if packet.seqnum != self.expect_seq:
            print(f"Pacote fora de ordem. Enviando NAK (ack={self.packet_to_send.acknum})")
            to_layer3(1, self.packet_to_send)
            return

        print(f"Recebido pacote (seq={packet.seqnum}): {packet.payload}")
        to_layer5(1, packet.payload)

        print(f"Enviando ACK (ack={self.expect_seq})")
        self.packet_to_send.acknum = self.expect_seq
        self.packet_to_send.checksum = self.packet_to_send.calculate_checksum()
        to_layer3(1, self.packet_to_send)

        self.expect_seq += 1

# Funções de simulação de rede
def to_layer3(AorB, packet):
    print(f"Enviando para camada 3: {packet.__dict__}")

def to_layer5(AorB, data):
    print(f"Entregando à camada 5: {data}")

def start_timer(AorB, increment):
    print(f"Iniciando timer para {AorB} por {increment} unidades de tempo")

def stop_timer(AorB):
    print(f"Parando timer para {AorB}")

# Inicialização
sender = Sender()
receiver = Receiver()

# Simulação de envio de mensagens
messages = [Message("Hello"), Message("World"), Message("GBN Protocol")]

for msg in messages:
    sender.output(msg)
    time.sleep(1)  # Simulação de tempo real

# Simulação de recebimento de ACKs
acks = [Packet(seqnum=0, acknum=1), Packet(seqnum=0, acknum=2)]

for ack in acks:
    sender.input(ack)
    time.sleep(1)

# Simulação de recebimento no receptor
packets = [Packet(seqnum=1, payload="Hello"), Packet(seqnum=2, payload="World")]

for pkt in packets:
    receiver.input(pkt)
    time.sleep(1)
