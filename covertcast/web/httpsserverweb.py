import socket
import select
import multiprocessing, threading, Queue
from httplib import HTTPResponse, BadStatusLine
import sys
import web_helper_functions as whf
import websocket_helper_functions as wshf
import traceback
import base64

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
num_workers = 1


# Compresses and sends back response
class ConnectionWorker(multiprocessing.Process):
  def __init__(self, in_queue, out_queue, killed, service="connectcast", primary=False, proxy_lock=None):
    multiprocessing.Process.__init__(self)
    # input comes in here. 
    # None is poison pill
    self.in_queue = in_queue
    # image out queue
    self.image_queue = out_queue
    # event that kills it
    self.killed = killed
    # "connectcast" or "youtube"
    self.service = service

  # Main loop
  def run(self):
    import time
    import zlib
    import video
    
    # main loop
    while(True):
      # let's see if this loop and break allows crashes to get fixed...
      # want to remove later when WebSocket is handling things well
      while(1):
        if self.killed.is_set():
          self.end()
          return
        if self.in_queue.empty():
          time.sleep(0.1)
          continue
        response = self.in_queue.get()
        break
      
      try:
        response = zlib.compress(response)
        data = video.format_data(response, self.service)
        self.image_queue.put(data)
      except Exception as e:
        print "Exception in Worker:", e
        traceback.print_tb(sys.exc_info()[2])
        self.end()
        return

  # Clears the queue and kills the worker
  def end(self):
    while(1):
      try:
        self.in_queue.get(True, timeout=1)
      except:
        # Empty  exception expected...
        print "Worker ended"
        return


# Handles HTTPS on the server side
class HTTPSWebSocket(multiprocessing.Process):
  def __init__(self, image_queue, killed, service, branches):
    multiprocessing.Process.__init__(self)
    self.killed = killed
    # TODO: This will increase in size and never stop...
    self.thread_killers = []
    self.image_queue = image_queue
    self.service = service
    self.skip_addon = branches[1]
    self.rec_queue = branches[2]
    
    self.socket = None
    self.thread_uid_d = {}

    # ConnectionWorker stuff
    self.proxy_lock = multiprocessing.Lock()
    self.worker_queue = multiprocessing.Queue()
    self.worker_killer = multiprocessing.Event()
    for i in range(num_workers):
      ConnectionWorker(
              self.worker_queue, self.image_queue, self.worker_killer,
              self.service, False, self.proxy_lock).start()

  # handles WebSocket handshake
  def handshake(self):
    timeout = 0.5

    # handshake strings
    handshake_start = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "
    handshake_end = b"\r\nSec-WebSocket-Protocol: chat\r\n\r\n"
    
    request = b""
    
    # get the client's handshake
    while(True):
      r,w,x = select.select([self.socket],[],[],timeout)
      if len(r) > 0:
        request += self.socket.recv(2**22)
        if request[-4:] == b"\r\n\r\n":
          break
      if self.killed.is_set():
          return -1
    # find the client's key
    key = wshf.get_key(request)
    if key == None:
        return -1
    # formulate correct response key
    res_key = wshf.response_key(key)
    # format response
    handshake = handshake_start + res_key + handshake_end
    # send server handshake
    self.socket.send(handshake)
    return 1

  # starts the websocket and listens for connection
  def get_websocket(self):
    timeout = 0.5

    temp = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    temp.bind((ip,port))
    temp.listen(1)
    while(True):
      r,w,x = select.select([temp],[],[],timeout)
      if r:
        self.socket, addr = temp.accept()
        self.connected = True
        break
      if self.killed.is_set():
        temp.shutdown(socket.SHUT_RDWR)
        temp.close()
        return -1
    return 1
  
  def decode(self, data):
    dec = wshf.decode_ws(data)
    return dec

  # does the work
  def run(self):
    import time

    timeout = 0.5

    if self.skip_addon:
      with open("request.txt","rb") as f:
        data = f.read()
      self.handle_decoded(data)
      while(not self.killed.is_set):
        time.sleep(1)
        self.end()
        return

    try:
      # setup websocket
      ret = self.get_websocket()
      if ret == -1:
        print "Error connecting to WebSocket"
        self.end()
        return
  
      # do handshake
      ret = self.handshake()
      if ret == -1:
        print "Error with handshake"
        self.end()
        return
      print "Server Websocket Opened"
  
      # listen loop
      data = b""
      req_dirty = b""
      while(True):
        r,w,x = select.select([self.socket],[],[],timeout)
        if r:
          # get and decode the data from the WebSocket
          data += self.socket.recv(2**22)
          if data == b"":
            continue
          if len(data) == 8 and ord(data[0]) == 136 and ord(data[1]) == 130:
            print "Websocket closed"
            self.socket.close()
            break
          decoded = self.decode(data)
          # if the data's all there, add it to the request
          if decoded != None:
            data = b""
            req_dirty += decoded
            if req_dirty[-1] != b"#":
              continue
            try:
              req_ascii = req_dirty.encode('ascii',errors='ignore')
              req = base64.b64decode(req_ascii[:-1])
            except Exception as e:
              print e
              continue
            print "Request: {}".format(req)
            # if we reach the end of the request, send it
            ret = self.handle_decoded(req)
            if ret == -1:
              print "Error in handler"
            req_dirty = b""
            # just comment of "None" to reset the add-on
            if req == b"None":
              req = b""
            data = b""
        if self.killed.is_set():
            self.end()
            return
    except Exception as e:
      print "Crash found in serverweb"
      print e
      traceback.print_tb(sys.exc_info()[2])
      self.end()
          
  def handle_decoded(self, decoded):
    # we might have multiple requests in a decoded
    # but I don't think so...
        
    # get the UUID
    uid = decoded[:16]
    request = decoded[16:]
    
    # start new thread
    if not uid in self.thread_uid_d:
      request_queue = multiprocessing.Queue()
      request_queue.put(request)
      killer = multiprocessing.Event()
      
      newthread = ConnectionThread(
          uid, request_queue, 
          self.worker_queue, killer,  
          self.proxy_lock, self.rec_queue)
      newthread.start()
      self.thread_killers.append(killer)
      self.thread_uid_d[uid] = request_queue
      print "New thread created: {}".format(uid)
    else:
      request_queue = self.thread_uid_d[uid]
      request_queue.put(request)

  # ends and cleans up thread
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
    for kill in self.thread_killers:
      kill.set()

    self.worker_killer.set()
    return
  
# Dummy WebSocket wrapper for testing
class DummyWebSocket(HTTPSWebSocket):
  def __init__(self, image_queue, killed, service, branches):
    WebSocket.__init__(self, image_queue, killed, service, branches)
  
  def decode(self, data):
    return data
  
  def handshake(self):
    return 1
      
  def handle_decoded(self, decoded):
    print "server", decoded
    try:
      super(DummyWebSocket, self).handle_decoded(decoded)
    except Exception as e:
      print e
      traceback.print_tb(sys.exc_info()[2])
    

# Handles individual connections
class ConnectionThread(multiprocessing.Process):
  def __init__(self, uid, request_queue, worker_queue, killed, proxy_lock, rec_queue):
    multiprocessing.Process.__init__(self)
    
    self.worker_queue = worker_queue
    self.uid = uid
    self.killed = killed
    self.request_queue = request_queue
    self.proxy_lock = proxy_lock
    self.rec_queue = rec_queue
    
    self.outsocket = None
  
  # Closes connections and ends the thread
  def end(self):
    print "Connection Thread ended: {}".format(self.uid)
    try:
      if self.outsocket:
        self.outsocket.shutdown(socket.SHUT_RDWR)
        self.outsocket.close()
    except:
      traceback.print_tb(sys.exc_info()[2])
    while not self.request_queue.empty():
        self.request_queue.get()
    return

  # Opens socket and runs main loop
  def run(self):
    print "running"
    # get first request
    request = self.request_queue.get()

    self.outsocket = socket.create_connection(("localhost", 8081))
    self.outsocket.sendall(request)

    self.run_common()


  # the request reply loop
  def run_common(self):
    timeout = 0.5

    while(not self.killed.is_set()):
      try:
        # to:   the Internet
        # from: Youtube
        if not self.request_queue.empty():
          request = self.request_queue.get()
          self.outsocket.sendall(request)
          if request == "":
            break
        # to:   YouTube
        # from: the Internet
        r, _, _ = select.select([self.outsocket],[],[],timeout)
        if r:
          response = self.outsocket.recv(4096)
          self.send_response(response)
          if response == "":
            break
      except Exception as e:
        print "Error in connection"
        print e
        print self.uid
        traceback.print_tb(sys.exc_info()[2])
    self.end()
    return

  # Sends a response
  def send_response(self,response):
    uid_response = self.uid+response
    print "responding to {}".format(self.uid)
    self.worker_queue.put(uid_response)
  


def main():
  import websocket
  import time
  
  # TODO: This code don't work...


  uid = "deadbeef12345678"
  request_queue = multiprocessing.Queue()
  request_queue.put("CONNECT mobile.twitter.com:443 HTTP/1.1\r\n\r\n")
  kill = multiprocessing.Event()

  newthread = ConnectionThread(
          uid, request_queue, 
          None, kill,  
          None, None)
  newthread.start()

  newthread.join()
    

if __name__ == "__main__":
    main()
