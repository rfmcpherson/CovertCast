import socket
import select
import hashlib
import base64
import multiprocessing, threading
import Queue
import sys
import time
import traceback

ip = "127.0.0.1"
port = 8080

endip = "127.0.0.1"
endport = 9997

timeout = 60

# use dummy version of websocket
dummy = False

# Method to turn string to unicode URL
def fixurl(url):
  import urlparse, urllib
  # turn string into unicode
  if not isinstance(url,unicode):
      url = url.decode('utf8')

  # parse it
  parsed = urlparse.urlsplit(url)

  # divide the netloc further
  userpass,at,hostport = parsed.netloc.rpartition('@')
  user,colon1,pass_ = userpass.partition(':')
  host,colon2,port = hostport.partition(':')

  # encode each component
  scheme = parsed.scheme.encode('utf8')
  user = urllib.quote(user.encode('utf8'))
  colon1 = colon1.encode('utf8')
  pass_ = urllib.quote(pass_.encode('utf8'))
  at = at.encode('utf8')
  host = host.encode('idna')
  colon2 = colon2.encode('utf8')
  port = port.encode('utf8')
  path = '/'.join(  # could be encoded slashes!
      urllib.quote(urllib.unquote(pce).encode('utf8'),'')
      for pce in parsed.path.split('/')
  )
  query = urllib.quote(urllib.unquote(parsed.query).encode('utf8'),'=&?/')
  fragment = urllib.quote(urllib.unquote(parsed.fragment).encode('utf8'))

  # put it back together
  netloc = ''.join((user,colon1,pass_,at,host,colon2,port))
  return urlparse.urlunsplit((scheme,netloc,path,query,fragment))

# Handles the client-side WebSocket connection
class WebSocket(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self.connected = False
    self.killed = False
    self.handshake_start = "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "
    self.handshake_end = "\r\nSec-WebSocket-Protocol: chat\r\n\r\n"  
    self.websocket = None
  
  def kill(self):
    self.killed = True
      
  # Given a response, returns the Sec-WebSocket-Key
  def get_key(self,data):
    headers = data.split()
    if not 'Sec-WebSocket-Key:' in headers:
      # TODO: throw exception
      print "cannot find key!"
      return None
    return headers[headers.index('Sec-WebSocket-Key:')+1]                    
  
  # Given the Sec-WebSocket-Key, returns the correct response key
  def response_key(self, key):
    key = key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    sha1 = hashlib.sha1()
    sha1.update(key)
    hash = sha1.digest()
    res_key = base64.b64encode(hash)
    return res_key
  
  # Handles WebSocket handshake  
  def handshake(self):
    timeout = 0.5
    request = ""
    # Get the client's handshake
    while(True):
      r,w,x = select.select([self.websocket],[],[],timeout)
      if len(r) > 0:
        request += self.websocket.recv(2**22)
        if request[-4:] == "\r\n\r\n":
          break
      if self.killed:
        return -1
    key = self.get_key(request)
    if key == None:
      return -1
    res_key = self.response_key(key)
    handshake = self.handshake_start + res_key + self.handshake_end
    self.websocket.send(handshake)
    return 1
      
  # Encodes data to be sent via WebSocket
  def encode_ws(self, data):
    out = chr(129)
    length = len(data)
    if length <= 125:
      out += chr(length)
    elif length <= 65535:
      out += chr(126)
      out += chr((length >> 8) & 255)
      out += chr((length) & 255)
    else:
      out += 127
      out += chr((length >> 56) & 255)
      out += chr((length >> 48) & 255)
      out += chr((length >> 40) & 255)
      out += chr((length >> 32) & 255)
      out += chr((length >> 24) & 255)
      out += chr((length >> 16) & 255)
      out += chr((length >> 8) & 255)
      out += chr((length) & 255)
    out += data
    return out
      
  # Attempts to open a socket
  def get_socket(self):
    timeout = 0.5
    temp = socket.socket(socket.AF_INET,type=socket.SOCK_STREAM)
    temp.bind((endip,endport))
    temp.listen(1)
    while(True):
      r,w,x = select.select([temp],[],[],timeout)
      if len(r) > 0:
        self.websocket, addr = temp.accept()
        self.connected = True
        break
      if self.killed:
        return -1
    return 1
      
  # Connects to the WebSocket and runs the handshake
  def run(self):
    ret = self.get_socket()
    print "Connected to WebSocket"
    if ret == -1:
      print "Error connecting to WebSocket"
      self.end()
      return
    ret = self.handshake()
    if ret == -1:
      print "Error with handshake"
      self.end()
      return
  
  # Sencds a message to the WebSocket
  def send(self, message):
    message = base64.b64encode(message)+"#"
    if not self.connected:
      print "not connected"
      return -1
    else:
      print "sending at {}".format(time.strftime("%m/%d/%y %H:%M:%S"))
      self.websocket.sendall(self.encode_ws(message))
      return 1
          
  # Attempts to close the WebSocket and empty queues
  def end(self):
    print "WebSocket ending"
    if self.websocket:
      try:
        self.websocket.shutdown(socket.SHUT_RDWR)
        self.websocket.close()
      except Exception as e:
        print e
        traceback.print_tb(sys.exc_info()[2])
    return
      
# Dummy WebSocket wrapper class used for testing
class DummyWebSocket(WebSocket):
  def __init__(self):
    WebSocket.__init__(self)
  
  # Nop encoding functions
  def encode_ws(self, message):
    return message
  
  # Connects to the WebSocket
  def get_socket(self):
    self.websocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.websocket.connect(("127.0.0.1",9998))
    self.connected = True
  
  # Nop handshake
  def handshake(self):
    return 1
  
  # Sends the message to the WebSocket
  def send(self, message):
    print "client\n", message.split("\r\n")[0]
    super(DummyWebSocket, self).send(message)
 
# handles individual sockets from the browser 
class ConnectionThread(threading.Thread):
  # TODO: We're ignoring the possibility of the 
  # a request break occurring between the headers and the body
  
  import time
  
  def __init__(self, socket, websocket, uid, new_thread_queue, addon, rec_queue):
    threading.Thread.__init__(self)
    self.socket = socket
    self.websocket = websocket
    self.uid = uid
    self.new_thread_queue = new_thread_queue
    self.addon = addon
    self.rec_queue = rec_queue
    
    self.killed = False
    self.response_queue = Queue.Queue()

  # preps the class for ending
  # shutsdown and closes socket to browser
  # clears the response queue
  def end(self):
    if self.uid:
      print "Connection thread ending {}".format(self.uid)
    else:
      print "Connection thread ending"
    try:
      self.socket.shutdown(socket.SHUT_RDWR)
      #self.socket.shutdown(socket.SHUT_RD)
      self.socket.close()    
    except:
      print "Couldn't close socket"
    while not self.response_queue.empty():
      self.response_queue.get()
      self.response_queue.task_done()
    return
      
  def kill(self):
    self.killed = True
  
  # sends a 404 as a response
  def no_op(self):
    self.put("HTTP/1.1 404 Not Found\r\n\r\n")
    
  # adds a response to the response queue
  def put(self, str):
    if self.killed:
      print "I'm dead bro {}".format(self.uid)
      return
    #print "response: {}".format(str)
    self.response_queue.put(str)
    return
    
  # main loop
  def run(self):
    import urllib
    import select

    timeout = 0.5

    # anything to read?
    while not self.killed:
      # to:   YouTube
      # from: browser
      r, _, _ = select.select([self.socket],[],[],timeout)
      if r:
        try:
          request = self.socket.recv(2**12)
        except:
          request = ""
        self.websocket.send(self.uid + request)
        if request == "":
          break
        
      
      # to:   browser
      # from: YouTube 
      if not self.response_queue.empty():
        response = self.response_queue.get()
        print "got response!"
        self.socket.sendall(response)
        if request == "":
          break
    
    self.end()
    return

# Handles HTTPS on client side
class HTTPSWebClient(threading.Thread):
  def __init__(self, cache, image_queue, killed, send_v2i, send_d2r, branches):
      threading.Thread.__init__(self)
      self.cache = cache
      self.image_queue = image_queue
      self.killed = killed
      self.send_v2i = send_v2i
      self.send_d2r = send_d2r
      self.addon = branches[1]
      self.rec_queue = branches[2]
      self.record_delay = branches[3]
      
      # queue where the threads go when they've received their entire request
      self.new_thread_queue = Queue.Queue()
      # dictionary threads waiting on response key is their uid
      self.thread_uid_d = {}
      # threads to be sent
      self.to_send = {}
      # list of ok urls 
      self.url_list = []
      # debug prints
      self.debug = 1
      self.test = 1

      
  def run(self):
    import zlib
    import time
    import datetime
    cache_list = []
    import uuid

    timeout = 0.5
    
    # create WebSocket
    if dummy:
      ws = DummyWebSocket()
    else:
      ws = WebSocket()
    ws.start()
    if self.debug:
      print "Websocket Opened"

    # create socket for browser
    browsersocket = socket.socket(socket.AF_INET,type=socket.SOCK_STREAM)
    browsersocket.bind((ip, port))
    browsersocket.listen(1)

    while(True):
      try:
        # process new requests from browser
        r,w,x = select.select([browsersocket],[],[],timeout)
        if len(r):
          # Get the socket
          remote, addr = browsersocket.accept()
          uid = uuid.uuid4().hex[:16]
          
          # make the new ConnectioThread
          newthread = ConnectionThread(
                          remote, ws, uid, self.new_thread_queue, 
                          self.addon, self.rec_queue)
          newthread.start()
          self.thread_uid_d[uid] = newthread
            
        # if we get data from images
        if not self.image_queue.empty():
          
          # first 16 is uid
          data = self.image_queue.get()
          try:
            data = zlib.decompress(data)
            uid = data[:16]
            data = data[16:]
            thread = self.thread_uid_d[uid]
            thread.put(data)
          except Exception as e:
            print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
            print e
            traceback.print_tb(sys.exc_info()[2])

          if self.debug:
            print "Sent to thread:\n\t{}".format(uid)
          if self.rec_queue:
            self.rec_queue.put(["response", "{}:\nCaching {}\n\n".format(time.strftime("%m/%d/%y %H:%M:%S"),uid)])
        
        # If we get the kill signal
        if self.killed.is_set():
          print "ClientThread ending"
          
          # close the sockets
          try:
            browsersocket.shutdown(socket.SHUT_RDWR)
            browsersocket.close()
          except Exception as e:
            print "can't kill browsersocket"
            print e
          ws.kill()
          
          # kill the threads
          for thread in self.thread_uid_d.values():
            if thread.uid:
              print "uid:", thread.uid
            else:
              print "Thread has no UID"
            thread.kill()
            print "done"
          
          while 1:
            try:
              self.new_thread_queue.get(False)
            except:
              break
          return
          
      except Exception as e:
        print "Exception in clientweb main thing"
        print e
        print traceback.print_tb(sys.exc_info()[2])
        return
          
      
def main():
  import time
  message = "HELLO"
  ws_client = WebSocket()
  ws_client.start() 
  time.sleep(60)
  print "ok"
  print ws.send(message)
          
if __name__ == '__main__':
    main()
                
