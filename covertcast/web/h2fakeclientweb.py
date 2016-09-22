import asyncio
import multiprocessing
import nghttp2
import ssl
import zlib

from .h2clientweb import *


# client proxy to respond to HTTP/2 request
class FakeClientShim(asyncio.Protocol):
    def __init__(self):
        asyncio.Protocol.__init__(self)
        self.buff = b''

    
    # input is (bytes)url (bytes)status (bytes)content
    # all parts seperated by b' '
    # status is the bytes corresponding to the int value, not the str
    def _process_data_l(self, data):
        url, status = data.split()[0:2]
        print("Got: {}".format(url))
        content = data[len(url)+1+len(status)+1:]
        status = int.from_bytes(status, byteorder='big')
        url_d[url] = [status, content]

        
    # checks the packet type and calls the appropiate method
    def _process_packet(self, packet):
        packet = zlib.decompress(packet)

        # remove first space
        packet = packet[1:] 

        # find type
        # we use packet[2:] due to space after packet_type
        packet_type = packet[0]
        if packet_type == 0:
            self._process_url_l(packet[2:])
        elif packet_type == 1:
            self._process_data_l(packet[2:])
        else:
            raise Exception("Bad packet type: {}".format(packet[0]))

            
    # input is [(bytes)url, ...]
    # the first url depends upon the rest
    def _process_url_l(self, data):
        urls = data.split()
        dependency_d[urls[0]] = urls[1:]

        
    def connection_lost(self, exec):
        pass

        
    # Called when a connection is made
    # There should one be one for this class
    def connection_made(self, transport):
        self.transport = transport

        
    # Called when data is received
    def data_received(self, data):    
                    
        # add to buffer
        self.buff += data

        # splits buffer into packets
        while len(self.buff) > 4:

            # check length of packet
            length_str = self.buff[:4]
            length = int.from_bytes(length_str, byteorder='big')
            print("len", length)

            # if we have a full 'packet', remove it
            if length <= len(self.buff[4:]):
                self.buff = self.buff[4:]
                self._process_packet(self.buff[:length])
                self.buff = self.buff[length:]
            else:
                break    
    
    
# Fakes the CovertCast client and returns presaved files
# urls is dictionary of urls to files to return 
class FakeWebClient(WebClient):
    def __init__(self):
        input_q = multiprocessing.Queue()
        kill_e = multiprocessing.Event()
        flags = []
        
        WebClient.__init__(self, input_q, kill_e, flags)
        
    # Create proxy for the server side (aka youtube side)
    def _create_server_side(self, ip, port):
        print("Creating fake data consumer")
        coro = self.loop.create_server(FakeClientShim, ip, 8081)
        server = self.loop.run_until_complete(coro)
        
        return


if __name__=="__main__":
    client = FakeWebClient()
    client.run()
