import multiprocessing
import socket
import time

from .h2serverweb import *


# Fake WebServer that loads a perset page
# and sends the data locally
class FakeWebServer(WebServer):

    def __init__(self):
        packet_queue = multiprocessing.Queue() 
        kill_e = multiprocessing.Event()
        next_page_e = multiprocessing.Event()
        flags = [True, True]
        
        self.count = 0
        
        WebServer.__init__(self, packet_queue, kill_e, next_page_e, flags)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(('127.0.0.1', 8081))
        
        self.next_page_e.set()
    
    def _send_packets(self, packets):
        super()._send_packets(packets)
        
        while 1:
            try:
                packet = self.output_q.get(timeout=0.5)
            except:
                break
            self.sock.sendall(packet)
        
        if self.count < 4:
            self.next_page_e.set()
            self.count += 1