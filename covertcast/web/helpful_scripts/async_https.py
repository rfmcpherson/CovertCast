import asyncio
import multiprocessing
import os
import ssl
from time import sleep

addr = "127.0.0.1"
port = 8080


class HTTP2Session(asyncio.Protocol):    
    def __init__(self):
        asyncio.Protocol.__init__(self)
        
    def connection_made(self, transport):
        print(transport)
        sock = transport.get_extra_info('socket')
        print(sock)
        print(sock.selected_npn_protocol())
        
def server():
    sc = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    sc.load_cert_chain('../cert/server.crt', '../cert/server.key', password="1234")

    sc.set_npn_protocols(["hs"])
    
    print(sc)
    
    loop = asyncio.get_event_loop()
    coro = loop.create_server(HTTP2Session, addr, port, ssl=sc)
    server = loop.run_until_complete(coro)

    print('Serving on {}'.format(server.sockets[0].getsockname()))
    loop.run_forever()

if __name__ == '__main__':
    server()
