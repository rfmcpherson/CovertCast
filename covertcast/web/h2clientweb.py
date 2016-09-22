import asyncio
import multiprocessing 
import nghttp2
import ssl
import sys
import threading
import zlib

from obj import Request, Response
if sys.platform != "win32":
    try:
        import video
    except:
        sys.path.insert(0, '..')
        sys.path.insert(0, '../video/')
        import video

    
h2ip = "127.0.0.1"
h2port = 8080

shimip = "127.0.0.1"
shimport = 8081

VERBOSE = True

# dict of (bytes) urls to list of (bytes) urls
# maps page dependencies
dependency_d = {}

# dict of (bytes) urls to [(int) status, (bytes) content]
# maps urls to their content
url_d = {}

# This class works as the handler for our nghttp2 proxy 
# TODO: still checks dependency_d which is no longer used. Remove
class NGHTTP2Handler(nghttp2.BaseRequestHandler):

    def _push_dependency(self, url):
        # if not in cache, return 404
        if not url in url_d:
            if VERBOSE:
                print("Pushing 404: {}".format(url))
            
            self.push(path=url.decode('utf-8'), status=404)
            return False
        else:
            if VERBOSE:
                print("Pushing 200: {}".format(url))
            
            status, data = url_d[url]
            self.push(path=url.decode('utf-8'), body=data, status=status)
            return True

            
    def on_headers(self):
    
        # Unwanted HTTPS (mostly Mozilla and extension requests)
        if not self.scheme:
            if VERBOSE:
                print("BAD SCHEME: {}".format(self.host))
            # 502 == Bad Gateway aka Not my problem
            self.send_response(status=502)
        
        else:
            # build request URL
            url =  self.scheme + b"://"
            url += self.host
            requested_url = url + self.path
            
            # if not in cache
            if not requested_url in url_d:

                if VERBOSE:
                    print("Requested 404: {}".format(requested_url))

                # return 404
                self.send_response(status=404)
            
            # if in cache
            else:

                if VERBOSE:
                    print("Requested 200: {}".format(requested_url))

                # push dependencies
                if requested_url in dependency_d:
                    dependencies = dependency_d[requested_url]
                    for dependency in dependencies:
                        self._push_dependency(dependency)
                else:
                    print("Non-primary URL requested")
                    print(requested_url)

                # send response
                status, data = url_d[requested_url]
                
                self.send_response(body=data, status=status)
                

# HTTP/1.1 proxy
class HTTP11Protcol(asyncio.Protocol):
    # Protocol init-like
    def connection_made(self, transport):
        self.transport = transport


    # Takes raw request and returns Request
    # TODO: more elagant code
    # TODO: figure out how to spell
    def parse_request(self, request):
        meta_data = request.split('\r\n\r\n')[0]
        method, url = meta_data.split(' ')[:2]
        
        method = method.encode('utf-8')
        url = url.split('?')[0].encode('utf-8')

        headers = {}
        for line in meta_data.split('\r\n')[1:]:
            header, value = line.split(': ')
            headers[header] = value

        body = '\r\n'.join(request.split('\r\n\r\n')[1:])

        return Request(url=url, method=method, headers=headers, body=body)


    # Send a response
    def respond(self, response):
        if response.status == None:
            data = b""
        else:
            data =  b"HTTP/1.1 "
            data += str(response.status).encode('utf-8')
            data += b'\r\n'
            for header, value in response.headers.items():
                data += header
                data += b': '
                data += value
                data += b'\r\n'
            data += b"\r\n" 
            data += response.body
                
        self.transport.write(data)


    # What to do when you need to do something
    # (most helpful description ever?)
    def data_received(self, data):
        message = data.decode()
        request = self.parse_request(message)

        if request.method.lower() == 'connect':
            print("Requested CONNECT: 500 {}".format(request.url))
            response = Response(status=500)
        elif request.url in url_d:
            status, data = url_d[request.url]
            print("Requested Found: {} {}".format(status, request.url))
            response = Response(status=status, body=data)
        else:
            print("Requested Missing: 404 {}".format(request.url))
            response = Response(status=404)
            
        self.respond(response)
        self.transport.close()


# input is (bytes)url (bytes)status (bytes)content
# all parts seperated by b' '
# status is the bytes corresponding to the int value, not the str
def _process_data_l(data):
    url, status = data.split()[0:2]
    print("GOT: ({}) {}".format(status,url))
    content = data[len(url)+1+len(status)+1:]
    status = int.from_bytes(status, byteorder='big')
    url_d[url] = [status, content]

    
# checks the packet type and calls the appropiate method
def _process_packet(packet):

    try:
        packet = zlib.decompress(packet)
    except Exception as e:
        print("Decompression error:", e)
        return False

    # remove first space
    packet = packet[1:] 

    # find type
    # we use packet[2:] due to space after packet_type
    packet_type = packet[0]
    if packet_type == 0:
        print("We don't use url_l anymore")
    elif packet_type == 1:
        _process_data_l(packet[2:])
    else:
        print(packet)
        print("Bad packet type: {}".format(packet[0]))  
        return False
    
    return True
  
  
# client proxy to respond to HTTP/2 request
@asyncio.coroutine
def ClientShim(input_q):
    
    # this is where the data goes
    buff = b''

    while 1:
        # get the data from the queue
        new_image, data = yield from input_q.coro_get()
        if new_image:
            buff = data
        else:
            buff += data   
        
        # splits buffer into packets
        while len(buff) > 4:
        
            # check length of packet
            length_str = buff[:4]
            length = int.from_bytes(length_str, byteorder='big')
            
            # if we have a full 'packet', remove it
            if length <= len(buff[4:]):
                buff = buff[4:]
                ret = _process_packet(buff[:length])
                if ret == False:
                    print("Bad packet found")
                buff = buff[length:]
            else:
                break

 
# The CovertCast client and returns presaved files
# urls is dictionary of urls to files to return 
class WebClient(multiprocessing.Process):
    def __init__(self, input_q, kill_e, flags):
        multiprocessing.Process.__init__(self)
        
        self.input_q = input_q
        self.kill_e = kill_e
        self.flags = flags # don't use

        self.http2 = False
        
        
    # Create proxy for the client side (aka browser side)
    def _create_client_side(self, ip, port):

        if self.http2:
            print("Creating HTTP/2 proxy")

            # setup ssl
            ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            ctx.options = ssl.OP_ALL | ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3
            ctx.load_cert_chain(
                './web/cert/server.crt', './web/cert/server.key', password="1234")

            server = nghttp2.HTTP2Server((ip,port), NGHTTP2Handler, ctx)
            
        else:
            print("Creating HTTP/1.1 proxy")

            coro = self.loop.create_server(HTTP11Protcol, ip, port)
            server = self.loop.run_until_complete(coro)

        return

        
    # Create proxy for the server side (aka youtube side)
    def _create_server_side(self, ip, port):
        print("Creating data consumer")
        asyncio.async(ClientShim(self.input_q))
        
        return
        

    def run(self):

        # get loop
        # do this in run and not init so we get the child process's loop
        self.loop = asyncio.get_event_loop()
    
        # setup
        self._create_client_side(h2ip, h2port)
        self._create_server_side(shimip, shimport)

        # run
        print("Running proxies")
        self.loop.run_forever()


if __name__=="__main__":
    client = WebClient(None, None, None)
    client.start()
