import socket
import select
import multiprocessing, threading, Queue
from httplib import HTTPResponse, BadStatusLine
import prefetching
import video
import sys
import web_helper_functions as whf
import websocket_helper_functions as wshf
import traceback

# Not used...
endip = "127.0.0.1"
endport = 80

# IP and port used to communicate with Firefox addon
# via websocket
ip = "127.0.0.1"
port = 9998

# Old crap for prefetching
# Not used with the current Ghost appraoch
layer_max = 2

# Number of connection workers running at a time
# 6 because servers have a habit of refusing more requests from a client
# and I haven't programmed checking what servers each client is talking to
# to ensure we stay under 
num_workers = 6

# Compresses and sends back response
class ConnectionWorker(multiprocessing.Process):
    def __init__(self, in_queue, out_queue, killed, service="connectcast", primary=False, proxy_lock=None):
        multiprocessing.Process.__init__(self)
        # Input comes in here. 
        # None to kill
        self.in_queue = in_queue
        # Image out queue
        self.image_queue = out_queue
        # Event that kills it
        self.killed = killed
        # "connectcast" or "youtube"
        self.service = service

    # Main loop
    def run(self):
        import time
        import zlib
        
        # Main loop
        while(True):
            # Let's see if this loop and break allows crashes to get fixed...
            # Want to remove later when WebSocket is handling things well
            while(1):
                if self.killed.is_set():
                    self.end()
                    return
                if self.in_queue.empty():
                    time.sleep(0.1)
                    continue
                ntype, packed = self.in_queue.get()
                break
            
            try:
                if ntype == 0 or ntype == 1:
                    address, status, headers, content = packed 

                    # We're assuming HTTP 1.1 because I don't know how to
                    # get the HTTP version out of Qt.
                    # Also ignoring the status code text for the same reason.
                    response = "HTTP/1.1 {} XXX\r\n{}\r\n\r\n{}".format(status, headers, content)
                    
                    response = zlib.compress(response)
                    message = "1 {} {}".format(address, response)
                elif ntype == 2:
                    url_list = ','.join(packed)
                    address = "list"
                    message = "{} {}".format(ntype, url_list)
                else:
                    print "Unsupported type found in Worker"
                    
                

                data = video.format_data(message, self.service)
                self.image_queue.put(data)
            except Exception as e:
                print "Exception in Worker:", e
                traceback.print_tb(sys.exc_info()[2])
                self.end()
                return
                
    # Clears queue and ends worker
    def end(self):
        while(1):
            try:
                self.in_queue.get(True, timeout=1)
            except:
                # Empty  exception expected...
                print "Worker ended"
                return

# Handles HTTP on the server side
class WebSocket(multiprocessing.Process):
    def __init__(self, image_queue, killed, service, branches):
        multiprocessing.Process.__init__(self)
        self.killed = killed
        # TODO: This will increase in size and never stop...
        self.threads = []
        self.image_queue = image_queue
        self.service = service
        self.addon = branches[1]
        self.rec_queue = branches[2]

        self.proxy_lock = multiprocessing.Lock()
        self.worker_queue = multiprocessing.Queue()
        self.worker_killer = multiprocessing.Event()

        self.socket = None
        
        for i in range(num_workers):
            ConnectionWorker(
                    self.worker_queue, self.image_queue, self.worker_killer,
                    self.service, False, self.proxy_lock).start()

    # Handles WebSocket handshake
    def handshake(self):
        # Handshake strings
        handshake_start = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "
        handshake_end = b"\r\nSec-WebSocket-Protocol: chat\r\n\r\n"
        
        request = b""
        
        # Get the client's handshake
        while(True):
            r,w,x = select.select([self.socket],[],[],0)
            if len(r) > 0:
                request += self.socket.recv(2**22)
                if request[-4:] == b"\r\n\r\n":
                    break
            if self.killed.is_set():
                return -1
        # Find the client's key
        key = wshf.get_key(request)
        if key == None:
            return -1
        # Formulate correct response key
        res_key = wshf.response_key(key)
        # Format response
        handshake = handshake_start + res_key + handshake_end
        # Send Server handshake
        self.socket.send(handshake)
        return 1
    
  
    # Starts the WebSocket and listens for connection
    def get_websocket(self):
        temp = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
        temp.bind((ip,port))
        temp.listen(1)
        while(True):
            r,w,x = select.select([temp],[],[],1)
            if r:
                self.socket, addr = temp.accept()
                self.connected = True
                break
            if self.killed.is_set():
                temp.shutdown(socket.SHUT_RDWR)
                temp.close()
                return -1
        return 1
    
        
    # Does the work
    def run(self):
        import time

        try:
            if not self.addon:
                # Setup websocket
                ret = self.get_websocket()
                if ret == -1:
                    print "Error connecting to WebSocket"
                    self.end()
                    return
            
                # Do handshake
                ret = self.handshake()
                if ret == -1:
                    print "Error with handshake"
                    self.end()
                    return
                print "Websocket Opened"
            
                # Listen Loop
                data = b""
                req = b""
                while(True):
                    r,w,x = select.select([self.socket],[],[],1)
                    if r:
                        # Get and decode the data from the WebSocket
                        data += self.socket.recv(2**22)
                        if data == "":
                            continue
                        if len(data) == 8 and ord(data[0]) == 136 and ord(data[1]) == 130:
                          print "Websocket closed"
                          self.socket.close()
                          break
                        print "Got data"
                        decoded = wshf.decode_ws(data)
                        print decoded
                        # If the data's all there, add it to the request
                        if decoded != None:
                            req += decoded
                            print ord(req[-4]), ord(req[-3]), ord(req[-2]), ord(req[-1])
                            if ord(req[-1]) == 32:
                                req = req[:-1]
                            # If we reach the end of the request, send it
                            if req[-4:] == b"\r\n\r\n":
                                print "break"
                                ret = self.handle_decoded(req)
                                if ret == -1:
                                    print "Error in handler"
                                req = b""
                            # just comment of "None" to reset the add-on
                            if req == b"None":
                              req = b""
                            data = b""
                    if self.killed.is_set():
                        self.end()
                        return
            else:
                data = b""
                with open("request.txt","rb") as f:
                    data = f.read()
                self.handle_decoded(data)
                while(True):
                    if self.killed.is_set():
                        self.end()
                        return
                    time.sleep(1)

        except Exception as e:
            print "Crash found in serverweb"
            print e
            traceback.print_tb(sys.exc_info()[2])
            self.end()
            
    # Handles decoded requests
    def handle_decoded(self, decoded):
        # We might have multiple requests
        # So split them up
        for request in decoded.split('\r\n\r\n'):
            if request == "":
                break
                
            # Start new thread
            if(1):
                k = multiprocessing.Event()
                newthread = ConnectionThread(
                    None, request, self.image_queue, 
                    self.worker_queue, k, self.service, 
                    self.proxy_lock, self.rec_queue)
                newthread.start()
                self.threads.append(k)
            print "\nNew thread created", id
    
    # Ends and cleans up thread
    def end(self):
        print "Websocket end called"
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            except Exception as e:
                print e
                traceback.print_tb(sys.exc_info()[2])
        # don't know if this'll work...
        for thread in self.threads:
            thread.set()

        self.worker_killer.set()
        return
        


# Handles individual sockets from the browser
class ConnectionThread(multiprocessing.Process):
    def __init__(self, id, request, image_queue, worker_queue, killed, service, proxy_lock, rec_queue):
        multiprocessing.Process.__init__(self)
        
        self.image_queue = image_queue
        self.worker_queue = worker_queue
        self.id = id
        self.killed = killed
        self.request = request
        self.service = service
        self.proxy_lock = proxy_lock
        self.rec_queue = rec_queue
        self.socket = None

    # Given a request, it fufills it
    def run(self):
        print "running"
        print len(self.request)
        # Request of format "method address http\r\n\r\n"
        method = self.request.split()[0].lower() 
        if method != "get" and method != "post":
            print "Wrong method type:", method
            return
            
        address = self.request.split()[1]
        
        cookies = self.request.split('\r\n')[1].strip()
        print cookies
        post = self.request.split('\r\n')[2].strip()

        # Use ghost for the html request to cut down
        # on php giving different links...

        if(0): # no search
          blocks = prefetching.inner_content_links_ghost(method, address, cookies, post, self.rec_queue)
          for block in blocks:
            if self.killed.is_set():
              self.end()
              return
            self.worker_queue.put(block)
        else: # search
          blocks, extra = prefetching.inner_content_links_search(method, address, cookies, post, self.rec_queue)
          print "extra:", extra
          for block in blocks:
            if self.killed.is_set():
              self.end()
              return
            self.worker_queue.put(block)
          count = 0
          for i in range(len(extra)):
            print "search prefetch url:", extra[i]
            if extra[i].lower().startswith('https'):
              continue
            blocks, _ = prefetching.inner_content_links_search("get", extra[i], cookies, "", self.rec_queue)
            for block in blocks:
              if self.killed.is_set():
                self.end()
                return
              self.worker_queue.put(block)
            count += 1
            if count == 5:
              break
        return
 
    # Closes the socket
    def end(self):
        print "Connection Thread ended"
        try:
          if self.socket:
              self.socket.close()
        except:
            traceback.print_tb(sys.exc_info()[2])
        
        return

    
def main():
    import websocket
    import time
    
    # TODO: This code is leaving some processing running when force
    # quitted on Linux

    q = multiprocessing.Queue()

    ws_server = WebSocket(q, "connectcast", False)
    ws_server.start()

    # hack to get websocket server ready
    time.sleep(1)
    
    ws_client = websocket.create_connection("ws://localhost:9998")
    
    with open("request.txt","rb") as f:
        data = f.read()
    ws_client.send(data)
    
    ws_server.join()
    

if __name__ == "__main__":
    main()
