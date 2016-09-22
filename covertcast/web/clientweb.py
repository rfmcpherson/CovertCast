import socket
import select
import hashlib
import base64
import multiprocessing, threading
import Queue
import sys
import traceback

ip = "127.0.0.1"
port = 8080

endip = "127.0.0.1"
endport = 9997

timeout = 60

# Returns correctly parsed URL
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

# Class that handles client-side WebSocket connection
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
        request = ""
        # Get the client's handshake
        while(True):
            r,w,x = select.select([self.websocket],[],[],0)
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
        temp = socket.socket(socket.AF_INET,type=socket.SOCK_STREAM)
        temp.bind((endip,endport))
        temp.listen(1)
        while(True):
            r,w,x = select.select([temp],[],[],0)
            if len(r) > 0:
                self.websocket, addr = temp.accept()
                self.connected = True
                break
            if self.killed:
                return -1
        return 1
        
    # Connects to WebSocket and runs the handshake
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
    
    # Encodes and sends a message to the WebSocket
    def send(self, message):
        if not self.connected:
            return -1
        else:
            self.websocket.sendall(self.encode_ws(message))
            return 1
            
    # Attempts to close connection
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

# Handles an individual request/response from the client        
class ConnectionThread(threading.Thread):
    import time
    
    def __init__(self, socket, websocket, new_thread_queue, addon, rec_queue):
        threading.Thread.__init__(self)
        self.socket = socket
        self.websocket = websocket
        self.new_thread_queue = new_thread_queue
        self.addon = addon
        self.rec_queue = rec_queue
        
        self.killed = False
        self.request = None
        self.has_ref = False
        self.response_queue = Queue.Queue()
        self.req_event = threading.Event()
        self.res_event = threading.Event()
        
    def kill(self):
        self.killed = True
        
    # Get initial request
    def get_initial_request(self):    
        import web_helper_functions as whf

        request = ""
        
        while(True):
            r,w,x = select.select([self.socket],[],[],1)
            if len(r) > 0:
                request += self.socket.recv(2**22)
                # TODO: We're ignoring the possibility of the 
                # break occuring on the message body. So fix it
                if whf.request_done(request):
                    break
            if self.killed:
                return -1
                
        self.request = request
        if self.rec_queue:
            self.rec_queue.put(["request","{}:\n{}".format(self.time.strftime("%m/%d/%y %H:%M:%S"), request)])
        
        self.url = fixurl(self.request.split()[1])
        
        if self.request.lower().startswith("connect "):
            print "CONNECT request found. Quitting"
            self.socket.sendall("HTTP/1.0 404 Not Found\r\n\r\n")
            return -1
            
        for header in self.request.split('\r\n'):
            if header.lower().startswith("referer:"):
                self.has_ref = True
                break
            if header.lower().startswith("cookie:"):
                pass
            if header == "":
                break
        
        # Add self and url to the thread list
        self.new_thread_queue.put([self.url, self])
        
        return 0

    # Formats response for sending over WebSocket
    def format_request(self):
        first = self.request.split("\r\n")[0]
        method, url, _ =  first.split()
        
        cookies = " "
        for header in self.request.split("\r\n"):
            if header.lower().startswith("cookie:"):
                cookies = header[8:] + " "
        
        post = " "
        if self.request.lower().startswith("post"):
            index = self.request.index("\r\n\r\n")
            post = self.request[index+4:]
            
        return "{} {}\r\n{}\r\n{}\r\n\r\n".format(method, url, cookies, post)
        
    # Runs
    def run(self):
        import urllib
        import time
        
        # Get the request
        if self.get_initial_request() == -1:
            self.end()
            return
        
        # Wait on the event
        self.req_event.wait()
        
        # Kill it if needed
        if self.killed:
            self.end()
            return
        
        # See if we got a response already
        if self.res_event.is_set():
            self.handle_response("Cached")
            return
        
        # Craft message ("id method address HTTP\r\n\r\n")
        # Double \r\n used only to conform to current add-on. Can be changed later
        message = self.format_request()
        print message
        
        # Save request or send to websocket
        if(self.addon):
            with open("request.txt","wb") as f:
                f.write(message)
        else:
            self.websocket.send(message)
        
        # Wait for the response
        self.res_event.wait()
        if self.killed:
            self.end()
            return

        self.handle_response("Not_cached")
        
        self.end()
        return
            
    # Sends a response to the client
    def handle_response(self, ref):
        response = self.response_queue.get()
        self.response_queue.task_done()
        
        if self.rec_queue:
            headers = response.split('\r\n\r\n')[0]
            self.rec_queue.put(["response","{}:\n{} {}\n{}\n\n".format(self.time.strftime("%m/%d/%y %H:%M:%S"), ref, self.url, headers)])
                
        print "pre send"
        try:
            self.socket.sendall(response)
        except Exception as e:
            print e
            print traceback.print_tb(sys.exc_info()[2])
        print "post send"
        self.end()
        
    # Adds a response to the response queue
    def put(self, str):
        if self.killed:
            self.res_event.set()
            return
        self.response_queue.put(str)
        self.res_event.set()
        if not self.req_event.is_set():
            self.req_event.set()
        return
        
    # ???
    def set_req_event(self):
        self.req_event.set()
        
    # ???
    def no_ref(self):
        return not self.has_ref
        
    # Adds 404 to response queue
    def no_op(self):
        self.put("HTTP/1.1 404 Not Found\r\n\r\n")
                
    # Closes connections empties queues
    def end(self):
        if self.url:
            print "Connection thread ending {}".format(self.url)
        else:
            print "Connection thread ending"
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()    
        except:
            print "Couldn't close socket"
        while not self.response_queue.empty():
            self.response_queue.get()
            self.response_queue.task_done()
        return
          

# Handles HTTP on the client side          
class WebClient(threading.Thread):
    # TODO: Add event to turn off connection threads.
    # The current version works, but holds things up when
    # the code is killed before completing
    # what I'm saying is that calling .kill() doesn't work for threads...
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
        
        # Queue where the threads go when they've received their entire
        # request
        self.new_thread_queue = Queue.Queue()
        # Dictionary threads waiting on response
        # key is their url
        self.thread_urls = {}
        # Threads to be sent
        self.to_send = {}
        # List of ok urls 
        self.url_list = []
        # Debug prints
        self.debug = 1
        self.test = 1

    # Run
    def run(self):
        import zlib
        import time
        import datetime
        cache_list = []
        
        # Create WebSocket
        ws = WebSocket()
        ws.start()
        if self.debug:
          print "Websocket Opened"

        # Create socket for browser
        insocket = socket.socket(socket.AF_INET,type=socket.SOCK_STREAM)
        insocket.bind((ip, port))
        insocket.listen(1)
    
        first = True
        while(True):
          try:
            # Process requests from browser
            r,w,x = select.select([insocket],[],[],0)
            if len(r):
                # Get the socket
                remote, addr = insocket.accept()
                # Make the new ConnectioThread
                newthread = ConnectionThread(
                                remote, ws, self.new_thread_queue, 
                                self.addon, self.rec_queue)
                newthread.start()
                
                # If it's the first thread, we can go ahead and send it
                # Probably don't need this anymore...
                if first:
                    if self.record_delay:
                        now = datetime.datetime.now()
                        time_str = now.strftime("%H:%M:%S.%f")
                        print "First request at {}".format(time_str)
                    newthread.set_req_event()
                    if self.debug:
                      print "Set first"
                    first = False
            
            # If a new thread is ready
            if not self.new_thread_queue.empty():
                url, thread = self.new_thread_queue.get()
                self.new_thread_queue.task_done()
                hash = hashlib.md5(url).hexdigest()
                # If it's cached, send it
                if url in cache_list:
                    data = ""
                    try:
                        with open(self.cache + hash, "rb") as f:
                            data = f.read()
                        data = zlib.decompress(data)
                    except Exception as e:
                        print "Error reading from cache:\n\t{}\n\t{}".format(url, hash)
                        print e
                        traceback.print_tb(sys.exc_info()[2])
                    thread.put(data)
                    if self.debug:
                        print "Read from cache:\n\t{}\n\t{}".format(url, hash)
                else:
                    # What if there are multiple requests waiting?
                    if url in self.thread_urls:
                      self.thread_urls[url].append(thread)
                    else:
                      self.thread_urls[url] = [thread]
                    
                    if url in self.to_send:
                      self.to_send[url].append(thread)
                    else:
                      self.to_send[url] = [thread]  
                      
                    if self.debug:
                      print "Added to thread list:\n\t{}\n\t{}".format(url, hash)
                
            # If we get data from images
            if not self.image_queue.empty():
                data = self.image_queue.get()
                                
                # get the type
                type = data[0]
                data = data[2:]
                index = data.find(" ")
                
                # Normal response
                # TODO: Fix unicode urls
                # TODO: We're no longer using ids
                if int(type) == 0:
                    pass
                # Prefetch response
                elif int(type) == 1:
                    url = data[:index]
                    data = data[index+1:]
                    # if thread exists
                    if url in self.thread_urls:
                        # send to thread
                        
                        # Save it anyway for testing
                        hash = hashlib.md5(url).hexdigest()
                        with open(self.cache + hash,'wb') as f:
                            f.write(data)
                        
                        try:
                            data = zlib.decompress(data)
                        except Exception as e:
                          print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                          print e
                          traceback.print_tb(sys.exc_info()[2])
                        
                        cache_list.append(url)
                        
                        threads = self.thread_urls[url]
                        del self.thread_urls[url]
                        
                        for thread in threads:
                            thread.put(data)
                            if self.debug:
                                print "Sent to thread:\n\t{}".format(url)
                                                        
                        if url in self.to_send:
                            del self.to_send[url]
                    
                    # If it doesn't exist yet, save the data to disk
                    else:
                        hash = hashlib.md5(url).hexdigest()
                        if self.debug:
                          print "Saved to cache:\n\t{}\n\t{}".format(url, hash)
                        with open(self.cache + hash,'wb') as f:
                            f.write(data)
                        cache_list.append(url)
                        
                        if self.rec_queue:
                            self.rec_queue.put(["response", "{}:\nCaching {} {}\n\n".format(time.strftime("%m/%d/%y %H:%M:%S"),url,hash)])
                        
                elif int(type) == 2:
                    if self.debug:
                      print "url_list"
                    self.url_list.extend(data.split(','))

                    
                    temp = "\n".join(map(str,self.url_list))
                    if self.rec_queue:
                        self.rec_queue.put(["whitelist","{}:\n{}\n".format(time.strftime("%m/%d/%y %H:%M:%S"), temp)])
                    
                else:
                    print "BAD TYPE FOUND!"
            
            # If we get the send signal
            if self.send_v2i.is_set() and self.send_d2r.is_set():
                # clientvideo handles both setting and clearing now
                temp = []
                if len(self.url_list) != 0:
                    for url in self.to_send:
                        for thread in self.to_send[url]:
                            # If it's a link on the current page, send it
                            # If it doesn't have a refer-header, that's ok too 
                            if url in self.url_list:
                                thread.set_req_event()
                                if self.debug:
                                  print "OK request sent: {}".format(url)
                                if self.rec_queue:
                                    temp_str = "{}:\nSent White {}\r\n\r\n".format(time.strftime("%m/%d/%y %H:%M:%S"),url)
                                    self.rec_queue.put(["request",temp_str])
                            elif thread.no_ref():
                                # reset the url list
                                self.url_list = []
                                if self.test:
                                    print "TESTING CLEARING CACHE ON NO REF REQUEST"
                                    cache_list = []
                                thread.set_req_event()
                                if self.debug:
                                  print "No ref request sent: {}".format(url)
                                if self.rec_queue:
                                    temp_str = "{}:\nSent No_ref {}\r\n\r\n".format(time.strftime("%m/%d/%y %H:%M:%S"),url)
                                    self.rec_queue.put(["request",temp_str])
                            # Otherwise, we consider it junk and return a no-op
                            else:
                                thread.no_op()
                                if url in self.thread_urls:
                                    del self.thread_urls[url]
                                if self.debug:
                                    print "Request killed: {}".format(url)
                                if self.rec_queue:
                                    temp_str = "{}:\nBlocked {}\r\n\r\n".format(time.strftime("%m/%d/%y %H:%M:%S"),url)
                                    self.rec_queue.put(["request",temp_str])
                            
                            # Add to list to be removed
                            # can't remove while iterating through dict
                            if not url in temp:
                                temp.append(url)
                    
                    # And remove it
                    for url in temp:
                        del self.to_send[url]
                        
            
            # If we get the kill signal
            # TODO: Clear queue?
            if self.killed.is_set():
                print "ClientThread ending"
                insocket.close()
                ws.kill()
                for threads in self.thread_urls.values():
                    for thread in threads:
                        if thread.url:
                           print "url:", thread.url
                        else:
                           print "Thread has no URL"
                        thread.kill()
                        thread.set_req_event()
                        thread.no_op()
                        print "done"
                return
          except Exception as e:
            print "Exception in clientweb main thing"
            print e
            print traceback.print_tb(sys.exc_info()[2])
            
      
# Opens a WebSocket connection and sends a message
def main():
    import time
    message = "HELLO"
    ws = WebSocket()
    ws.start() 
    time.sleep(60)
    print "ok"
    print ws.send(message)
          
if __name__ == '__main__':
    main()
                
