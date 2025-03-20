import random
import time
from collections import defaultdict

# Configurações de simulação
BUFSIZE = 64
MAX_MESSAGE_SIZE = 1024  # Tamanho máximo de mensagem
PACKET_LOSS_RATE = 0.2   # Probabilidade de perda de pacote (20%)
SIMULATION_DURATION = 30  # Duração da simulação em segundos

class Statistics:
    def __init__(self):
        self.packets_sent = 0
        self.packets_retransmitted = 0
        self.packets_received = 0
        self.packets_delivered = 0
        self.packets_corrupted = 0
        self.packets_lost = 0
        self.packets_out_of_order = 0
        self.timeouts = 0
        self.start_time = time.time()
        self.message_sizes = []
        self.rtt_samples = []
    
    def report(self):
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            elapsed = 0.001  # Evitar divisão por zero
        
        print("\n====== ESTATÍSTICAS DE DESEMPENHO ======")
        print(f"Duração da simulação: {elapsed:.2f} segundos")
        print(f"Pacotes enviados: {self.packets_sent}")
        print(f"Pacotes retransmitidos: {self.packets_retransmitted} ({self.packets_retransmitted/max(1, self.packets_sent)*100:.2f}%)")
        print(f"Pacotes recebidos: {self.packets_received}")
        print(f"Pacotes entregues à camada 5: {self.packets_delivered}")
        print(f"Pacotes corrompidos: {self.packets_corrupted}")
        print(f"Pacotes perdidos: {self.packets_lost} ({self.packets_lost/max(1, self.packets_sent)*100:.2f}%)")
        print(f"Pacotes fora de ordem: {self.packets_out_of_order}")
        print(f"Timeouts ocorridos: {self.timeouts}")
        
        throughput = self.packets_delivered / elapsed
        print(f"Taxa de transferência: {throughput:.2f} pacotes/segundo")
        
        if self.message_sizes:
            avg_size = sum(self.message_sizes) / len(self.message_sizes)
            print(f"Tamanho médio de mensagem: {avg_size:.2f} bytes")
        
        if self.rtt_samples:
            avg_rtt = sum(self.rtt_samples) / len(self.rtt_samples)
            print(f"RTT médio: {avg_rtt:.2f} ms")
        
        print("========================================")

# Estatísticas globais
stats = Statistics()

class Message:
    def __init__(self, data):
        self.data = data[:MAX_MESSAGE_SIZE]  # Limitando ao tamanho máximo
        stats.message_sizes.append(len(data))

class Packet:
    def __init__(self, seqnum=0, acknum=0, payload=""):
        self.seqnum = seqnum
        self.acknum = acknum
        self.payload = payload[:MAX_MESSAGE_SIZE]
        self.checksum = self.calculate_checksum()
        self.timestamp = time.time() * 1000  # Timestamp em milissegundos
        self.retransmissions = 0

    def calculate_checksum(self):
        checksum = self.seqnum + self.acknum
        checksum += sum(ord(char) for char in self.payload)
        return checksum
    
    def __str__(self):
        return f"Packet(seq={self.seqnum}, ack={self.acknum}, payload='{self.payload[:20]}{'...' if len(self.payload) > 20 else ''}', size={len(self.payload)})"

class Sender:
    def __init__(self, window_size=8, initial_rtt=15):
        self.base = 1
        self.nextseq = 1
        self.window_size = window_size
        self.estimated_rtt = initial_rtt
        self.buffer_next = 1
        self.packet_buffer = [None] * BUFSIZE
        self.timeout_multiplier = 1  # Para backoff exponencial
        self.max_timeout = 120       # Timeout máximo em segundos
        self.timer_running = False
        self.sent_times = {}         # Para calcular RTT
        self.send_buffer = []        # Fila de mensagens pendentes
        self.seq_counter = 1         # Contador de sequência
        self.transmission_start = time.time()  # Para calcular throughput

    def send_window(self):
        while self.nextseq < self.buffer_next and self.nextseq < self.base + self.window_size:
            packet = self.packet_buffer[self.nextseq % BUFSIZE]
            if packet:
                print(f"Enviando pacote {packet}")
                self.send_packet(packet, is_retransmission=False)
                if self.base == self.nextseq:
                    self.start_timer()
                self.nextseq += 1

    def send_packet(self, packet, is_retransmission=False):
        self.sent_times[packet.seqnum] = time.time() * 1000  # Timestamp em ms
        
        if is_retransmission:
            packet.retransmissions += 1
            stats.packets_retransmitted += 1
            print(f"RETRANSMISSÃO #{packet.retransmissions} para pacote {packet.seqnum}")
        else:
            stats.packets_sent += 1
        
        # Simular perda de pacote
        if random.random() < PACKET_LOSS_RATE:
            stats.packets_lost += 1
            print(f"Pacote {packet.seqnum} foi PERDIDO na transmissão!")
            return
        
        # Simular corrupção ocasional (1% de chance)
        if random.random() < 0.01:
            corrupt_packet = Packet(
                seqnum=packet.seqnum,
                acknum=packet.acknum,
                payload=packet.payload
            )
            # Modificar o checksum para simular corrupção
            corrupt_packet.checksum += 1
            to_layer3(0, corrupt_packet)
            print(f"Pacote {packet.seqnum} foi CORROMPIDO na transmissão!")
        else:
            to_layer3(0, packet)

    def output(self, message):
        # Se o buffer estiver cheio, enfileirar para envio posterior
        if self.buffer_next - self.base >= BUFSIZE:
            print(f"Buffer cheio. Enfileirando mensagem: {message.data[:20]}...")
            self.send_buffer.append(message)
            return
        
        # Fragmentar mensagens grandes em múltiplos pacotes
        max_payload = 20  # Tamanho máximo de payload por pacote
        data = message.data
        
        while data:
            chunk = data[:max_payload]
            data = data[max_payload:]
            
            print(f"Armazenando pacote (seq={self.buffer_next}): {chunk}")
            packet = Packet(seqnum=self.buffer_next, payload=chunk)
            self.packet_buffer[self.buffer_next % BUFSIZE] = packet
            self.buffer_next += 1
        
        self.send_window()
        
        # Processar mensagens enfileiradas se houver espaço
        self.process_queued_messages()

    def process_queued_messages(self):
        while self.send_buffer and (self.buffer_next - self.base < BUFSIZE):
            message = self.send_buffer.pop(0)
            self.output(message)

    def input(self, packet):
        # Verificar checksum
        if packet.checksum != packet.calculate_checksum():
            print(f"ACK corrompido. Ignorando.")
            return
        
        # Ignorar ACKs duplicados ou mais antigos
        if packet.acknum < self.base:
            print(f"ACK duplicado ou antigo (ack={packet.acknum}). Ignorando.")
            return
        
        print(f"Recebido ACK (ack={packet.acknum})")
        
        # Calcular RTT para adaptação do timeout
        if packet.acknum in self.sent_times:
            rtt = time.time() * 1000 - self.sent_times[packet.acknum]  # RTT em ms
            stats.rtt_samples.append(rtt)
            print(f"RTT medido: {rtt:.2f} ms")
            
            # Atualizar estimativa de RTT (Algoritmo de Jacobson/Karels)
            alpha = 0.125
            beta = 0.25
            if not hasattr(self, 'rtt_dev'):
                self.rtt_dev = rtt / 2  # Desvio inicial
            
            error = rtt - self.estimated_rtt
            self.estimated_rtt = self.estimated_rtt + alpha * error
            self.rtt_dev = self.rtt_dev + beta * (abs(error) - self.rtt_dev)
            self.timeout_multiplier = 1  # Reset do multiplicador após ACK bem-sucedido
            
            # RTO = RTT + 4 * Desvio
            timeout = self.estimated_rtt + 4 * self.rtt_dev
            print(f"Timeout atualizado: {timeout:.2f} ms")
            
            # Remover da tabela de timestamps
            del self.sent_times[packet.acknum]
        
        old_base = self.base
        self.base = packet.acknum + 1
        
        # Liberar espaço no buffer e processar mensagens enfileiradas
        if old_base != self.base:
            self.process_queued_messages()
        
        if self.base == self.nextseq:
            self.stop_timer()
            print("Janela vazia - Parando timer")
        else:
            self.start_timer()  # Reiniciar timer para o próximo pacote

    def timer_interrupt(self):
        stats.timeouts += 1
        print(f"Timeout! (Multiplicador: {self.timeout_multiplier}x) Reenviando pacotes não confirmados.")
        
        # Backoff exponencial - dobrar o timeout a cada retransmissão
        self.timeout_multiplier = min(self.timeout_multiplier * 2, self.max_timeout / self.estimated_rtt)
        
        # Retransmitir todos os pacotes não confirmados na janela
        for i in range(self.base, self.nextseq):
            packet = self.packet_buffer[i % BUFSIZE]
            if packet:
                print(f"Reenviando pacote seq={packet.seqnum}: {packet.payload[:20]}")
                self.send_packet(packet, is_retransmission=True)
        
        self.start_timer()

    def start_timer(self):
        if self.timer_running:
            stop_timer(0)
        
        timeout = self.estimated_rtt * self.timeout_multiplier
        start_timer(0, timeout)
        self.timer_running = True

    def stop_timer(self):
        if self.timer_running:
            stop_timer(0)
            self.timer_running = False

class Receiver:
    def __init__(self):
        self.expect_seq = 1
        self.last_ack = Packet(seqnum=0, acknum=0)
        self.reassembly_buffer = defaultdict(list)  # Para mensagens fragmentadas
        self.fragment_timeout = 5  # Timeout para reassembly em segundos
        self.last_fragment_time = {}  # Timestamp do último fragmento recebido

    def input(self, packet):
        stats.packets_received += 1
        
        # Verificar checksum
        if packet.checksum != packet.calculate_checksum():
            print(f"Pacote corrompido. Enviando ACK anterior (ack={self.last_ack.acknum})")
            stats.packets_corrupted += 1
            to_layer3(1, self.last_ack)
            return
        
        # Verificar se o pacote está na sequência esperada
        if packet.seqnum != self.expect_seq:
            print(f"Pacote fora de ordem (recebido={packet.seqnum}, esperado={self.expect_seq}). Enviando ACK anterior.")
            stats.packets_out_of_order += 1
            to_layer3(1, self.last_ack)
            return

        print(f"Recebido pacote em ordem (seq={packet.seqnum}): {packet.payload}")
        stats.packets_delivered += 1
        
        # Entregar à camada 5
        to_layer5(1, packet.payload)
        
        # Atualizar último ACK
        self.last_ack = Packet(seqnum=0, acknum=self.expect_seq)
        self.last_ack.checksum = self.last_ack.calculate_checksum()
        
        # Avançar sequência esperada
        self.expect_seq += 1
        
        print(f"Enviando ACK (ack={self.last_ack.acknum})")
        to_layer3(1, self.last_ack)

# Simulação de ambiente de rede
class NetworkSimulator:
    def __init__(self):
        self.events = []  # Fila de eventos
        self.current_time = 0
        self.sender = Sender(window_size=8, initial_rtt=15)
        self.receiver = Receiver()
        self.timers = {}
    
    def schedule_event(self, time_delta, event_type, params=None):
        event_time = self.current_time + time_delta
        self.events.append((event_time, event_type, params))
        self.events.sort()  # Ordenar eventos por tempo
    
    def to_layer3(self, AorB, packet):
        # Simular latência de rede (entre 5-15ms)
        latency = random.uniform(5, 15)
        dest = 1 if AorB == 0 else 0  # Oposto do remetente
        
        print(f"Camada 3: Agendando entrega do pacote {packet} em {latency:.2f}ms")
        self.schedule_event(latency, "PACKET_ARRIVAL", {"dest": dest, "packet": packet})
    
    def to_layer5(self, AorB, data):
        print(f"Camada 5 [{('Receiver' if AorB == 1 else 'Sender')}]: Dados recebidos: {data}")
    
    def start_timer(self, AorB, increment):
        entity = "Sender" if AorB == 0 else "Receiver"
        print(f"Timer iniciado para {entity} com duração de {increment:.2f}ms")
        self.timers[AorB] = self.current_time + increment
        self.schedule_event(increment, "TIMER_INTERRUPT", {"entity": AorB})
    
    def stop_timer(self, AorB):
        entity = "Sender" if AorB == 0 else "Receiver"
        print(f"Timer parado para {entity}")
        if AorB in self.timers:
            del self.timers[AorB]
            
            # Remover eventos de timer pendentes
            self.events = [e for e in self.events if not (e[1] == "TIMER_INTERRUPT" and e[2]["entity"] == AorB)]
    
    def run_simulation(self, duration):
        self.schedule_event(0, "STATISTICS", {})  # Evento inicial de estatísticas
        end_time = self.current_time + duration
        
        while self.events and self.current_time < end_time:
            event = self.events.pop(0)
            event_time, event_type, params = event
            self.current_time = event_time
            
            print(f"\n[TEMPO: {self.current_time:.2f}] Processando evento: {event_type}")
            
            if event_type == "PACKET_ARRIVAL":
                dest, packet = params["dest"], params["packet"]
                if dest == 0:  # Sender
                    self.sender.input(packet)
                else:  # Receiver
                    self.receiver.input(packet)
            
            elif event_type == "TIMER_INTERRUPT":
                entity = params["entity"]
                if entity == 0:  # Sender
                    self.sender.timer_interrupt()
            
            elif event_type == "SEND_MESSAGE":
                message = params["message"]
                self.sender.output(message)
            
            elif event_type == "STATISTICS":
                # Agendar próxima atualização de estatísticas
                self.schedule_event(5, "STATISTICS", {})
                
                # Gerar mensagem aleatória ocasionalmente
                if random.random() < 0.3:  # 30% de chance
                    msg_length = random.randint(10, 100)
                    msg_data = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(msg_length))
                    message = Message(msg_data)
                    print(f"\n[TESTE] Gerando nova mensagem de {len(msg_data)} bytes")
                    self.schedule_event(0.1, "SEND_MESSAGE", {"message": message})
        
        print("\nSimulação concluída!")
        stats.report()

# Redefinir funções para usar o simulador
simulator = NetworkSimulator()

def to_layer3(AorB, packet):
    simulator.to_layer3(AorB, packet)

def to_layer5(AorB, data):
    simulator.to_layer5(AorB, data)

def start_timer(AorB, increment):
    simulator.start_timer(AorB, increment)

def stop_timer(AorB):
    simulator.stop_timer(AorB)

# Executar simulação
if __name__ == "__main__":
    print("Iniciando simulação de protocolo Go-Back-N com melhorias...")
    print(f"Configurações: Janela={simulator.sender.window_size}, Taxa de perda={PACKET_LOSS_RATE*100}%")
    
    # Criar algumas mensagens iniciais
    messages = [
        Message("Hello GBN Protocol"),
        Message("Este é um teste de fragmentação de mensagens grandes. " * 3),
        Message("Mensagem curta")
    ]
    
    # Agendar envio das mensagens iniciais
    for i, msg in enumerate(messages):
        simulator.schedule_event(i * 2, "SEND_MESSAGE", {"message": msg})
    
    # Executar simulação
    simulator.run_simulation(SIMULATION_DURATION)
