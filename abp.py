import heapq


def get_checksum(packet):
    """ Calcula o checksum do pacote """
    return sum(ord(c) for c in packet['payload']) + packet['seqnum'] + packet['acknum']


class ABPProtocol:
    def __init__(self):
        self.A = {'seqnum': 0, 'last_packet': None}
        self.B = {'expected_seqnum': 0}
        self.event_queue = []
        self.time = 0.0

    def to_layer3(self, packet):
        """ Envia o pacote para a camada 3 """
        heapq.heappush(self.event_queue, (self.time + 5, 'FROM_LAYER3', packet))
        print(f"Sent to layer 3: {packet}")

    def to_layer5(self, message):
        """ Entrega a mensagem à camada 5 (destino final) """
        print(f"Delivered to layer 5: {message}")

    def A_output(self, message):
        """ A envia um pacote """
        packet = {'seqnum': self.A['seqnum'], 'acknum': 0, 'payload': message}
        packet['checksum'] = get_checksum(packet)
        self.A['last_packet'] = packet  # Armazena o último pacote enviado
        print(f"A_output: Sending packet: {message}")
        self.to_layer3(packet)

    def A_timerinterrupt(self):
        """ Reenvia pacote ao ocorrer timeout """
        print("Event: TIMER_INTERRUPT")
        if self.A['last_packet']:
            print("A_timerinterrupt: Resending last packet.")
            self.to_layer3(self.A['last_packet'])

    def B_input(self, packet):
        """ B recebe um pacote """
        if not isinstance(packet, dict):
            print("B_input: Received an invalid packet format.")
            return

        print(f"B_input: Received message: {packet.get('payload', '[No Payload]')}")

        if packet['checksum'] != get_checksum(packet):
            print("B_input: Checksum error! Ignoring packet.")
            return

        if packet['seqnum'] == self.B['expected_seqnum']:
            self.to_layer5(packet['payload'])
            ack_packet = {'seqnum': packet['seqnum'], 'acknum': packet['seqnum'], 'payload': '', 'checksum': 0}
            self.to_layer3(ack_packet)
            self.B['expected_seqnum'] = 1 - self.B['expected_seqnum']
        else:
            print("B_input: Unexpected sequence number. Sending NAK.")
            nak_packet = {'seqnum': self.B['expected_seqnum'], 'acknum': self.B['expected_seqnum'], 'payload': '',
                          'checksum': 0}
            self.to_layer3(nak_packet)

    def run(self):
        """ Executa o protocolo """
        while self.event_queue:
            self.time, event_type, args = heapq.heappop(self.event_queue)
            print(f"Event: {event_type} at time {self.time}")

            if event_type == 'FROM_LAYER3':
                if isinstance(args, dict):
                    self.B_input(args)
                else:
                    print("Error: Invalid packet received from layer 3.")
            elif event_type == 'TIMER_INTERRUPT':
                self.A_timerinterrupt()


# Teste simples
protocol = ABPProtocol()
protocol.A_output("Hello, B!")
protocol.run()
