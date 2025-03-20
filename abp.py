import heapq
import time

def get_checksum(packet):
    """ Calcula o checksum do pacote """
    return sum(ord(c) for c in packet['payload']) + packet['seqnum'] + packet['acknum']

class ABPProtocol:
    def __init__(self):
        self.A = {'seqnum': 0, 'last_packet': None, 'waiting_ack': False}
        self.B = {'expected_seqnum': 0}
        self.event_queue = []
        self.current_time = 0.0
        self.timeout = 10.0  # Tempo de timeout em unidades de tempo
        
    def to_layer3(self, packet, from_A=True):
        """ Envia o pacote para a camada 3 """
        # Simula atraso de rede
        delay = 5.0
        # Adiciona um evento para simular a chegada do pacote
        if from_A:
            heapq.heappush(self.event_queue, (self.current_time + delay, 'A_TO_B', packet.copy()))
            print(f"Time {self.current_time:.1f}: A sent to layer 3: {packet}")
        else:
            heapq.heappush(self.event_queue, (self.current_time + delay, 'B_TO_A', packet.copy()))
            print(f"Time {self.current_time:.1f}: B sent to layer 3: {packet}")
    
    def to_layer5(self, message, from_A=False):
        """ Entrega a mensagem à camada 5 (destino final) """
        sender = "A" if from_A else "B"
        print(f"Time {self.current_time:.1f}: {sender} delivered to layer 5: {message}")
    
    def start_timer(self):
        """ Inicia o timer para retransmissão """
        heapq.heappush(self.event_queue, (self.current_time + self.timeout, 'TIMER_INTERRUPT', None))
        print(f"Time {self.current_time:.1f}: Timer started")
    
    def stop_timer(self):
        """ Para o timer (removendo eventos de timeout) """
        # Remover eventos de timeout da fila (na prática, criaríamos uma nova fila)
        new_queue = []
        for event in self.event_queue:
            if event[1] != 'TIMER_INTERRUPT':
                new_queue.append(event)
        self.event_queue = new_queue
        heapq.heapify(self.event_queue)
        print(f"Time {self.current_time:.1f}: Timer stopped")
    
    def A_output(self, message):
        """ A envia um pacote """
        if self.A['waiting_ack']:
            print(f"Time {self.current_time:.1f}: A is waiting for ACK. Message queued.")
            return
        
        packet = {'seqnum': self.A['seqnum'], 'acknum': 0, 'payload': message}
        packet['checksum'] = get_checksum(packet)
        self.A['last_packet'] = packet.copy()  # Armazena o último pacote enviado
        self.A['waiting_ack'] = True
        
        print(f"Time {self.current_time:.1f}: A_output: Sending packet with seqnum={packet['seqnum']}: {message}")
        self.to_layer3(packet, from_A=True)
        self.start_timer()
    
    def A_input(self, packet):
        """ A recebe um pacote (ACK ou NAK) """
        print(f"Time {self.current_time:.1f}: A_input: Received ACK/NAK with acknum={packet['acknum']}")
        
        # Verifica se o checksum está correto
        if packet.get('checksum', 0) != get_checksum(packet):
            print(f"Time {self.current_time:.1f}: A_input: Checksum error! Ignoring packet.")
            return
        
        # Verifica se o ACK é para o pacote atual
        if packet['acknum'] == self.A['seqnum']:
            print(f"Time {self.current_time:.1f}: A_input: Received ACK for packet {self.A['seqnum']}")
            self.stop_timer()
            self.A['seqnum'] = 1 - self.A['seqnum']  # Alterna o bit de sequência
            self.A['waiting_ack'] = False
        else:
            print(f"Time {self.current_time:.1f}: A_input: Received outdated or incorrect ACK. Ignoring.")
    
    def A_timerinterrupt(self):
        """ Reenvia pacote ao ocorrer timeout """
        print(f"Time {self.current_time:.1f}: A_timerinterrupt: Timer expired")
        if self.A['last_packet'] and self.A['waiting_ack']:
            print(f"Time {self.current_time:.1f}: A_timerinterrupt: Resending last packet with seqnum={self.A['seqnum']}")
            self.to_layer3(self.A['last_packet'], from_A=True)
            self.start_timer()
    
    def B_input(self, packet):
        """ B recebe um pacote """
        if not isinstance(packet, dict):
            print(f"Time {self.current_time:.1f}: B_input: Received an invalid packet format.")
            return
        
        print(f"Time {self.current_time:.1f}: B_input: Received packet with seqnum={packet['seqnum']}: {packet.get('payload', '[No Payload]')}")
        
        # Verifica o checksum
        if packet.get('checksum', 0) != get_checksum(packet):
            print(f"Time {self.current_time:.1f}: B_input: Checksum error! Sending NAK.")
            nak_packet = {'seqnum': 0, 'acknum': 1 - self.B['expected_seqnum'], 'payload': '', 'checksum': 0}
            nak_packet['checksum'] = get_checksum(nak_packet)
            self.to_layer3(nak_packet, from_A=False)
            return
        
        # Verifica se o número de sequência é o esperado
        if packet['seqnum'] == self.B['expected_seqnum']:
            # Entrega o pacote à camada 5
            self.to_layer5(packet['payload'])
            
            # Envia ACK
            ack_packet = {'seqnum': 0, 'acknum': packet['seqnum'], 'payload': '', 'checksum': 0}
            ack_packet['checksum'] = get_checksum(ack_packet)
            self.to_layer3(ack_packet, from_A=False)
            
            # Atualiza o número de sequência esperado
            self.B['expected_seqnum'] = 1 - self.B['expected_seqnum']
        else:
            print(f"Time {self.current_time:.1f}: B_input: Unexpected sequence number. Sending ACK for previous packet.")
            ack_packet = {'seqnum': 0, 'acknum': 1 - self.B['expected_seqnum'], 'payload': '', 'checksum': 0}
            ack_packet['checksum'] = get_checksum(ack_packet)
            self.to_layer3(ack_packet, from_A=False)
    
    def run_simulation(self, messages):
        """ Executa a simulação com múltiplas mensagens """
        for msg in messages:
            self.A_output(msg)
            self.run_events()
            print("\n--- Simulation paused ---\n")
    
    def run_events(self):
        """ Processa eventos da fila até que ela esteja vazia """
        while self.event_queue:
            event_time, event_type, data = heapq.heappop(self.event_queue)
            self.current_time = event_time
            
            if event_type == 'A_TO_B':
                self.B_input(data)
            elif event_type == 'B_TO_A':
                self.A_input(data)
            elif event_type == 'TIMER_INTERRUPT':
                self.A_timerinterrupt()
                
            # Pequena pausa para melhor visualização
            time.sleep(0.5)

# Teste de simulação
def test_abp():
    # Criar uma instância do protocolo
    protocol = ABPProtocol()
    
    # Lista de mensagens para enviar
    messages = [
        "Hello, world!",
        "This is a test of the ABP protocol",
        "Third message to test sequence numbers"
    ]
    
    # Executar a simulação
    print("Starting ABP protocol simulation:")
    protocol.run_simulation(messages)
    
    # Simulação com perda de pacote
    print("\n\n--- Simulation with packet loss ---\n")
    protocol = ABPProtocol()
    
    # Enviar mensagem
    protocol.A_output("Message that will be lost")
    
    # Remover evento de transmissão para simular perda
    protocol.event_queue = [evt for evt in protocol.event_queue if evt[1] != 'A_TO_B']
    heapq.heapify(protocol.event_queue)
    
    # Rodar simulação - deveria ocorrer timeout e retransmissão
    protocol.run_events()

if __name__ == "__main__":
    test_abp()
