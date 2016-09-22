import socket
import select
import hashlib
import base64
import multiprocessing, threading
import uuid
import Queue

ip = "127.0.0.1"
port = 8080

endip = "127.0.0.1"
endport = 9997

timeout = 60

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

# Handlee an individual connection with the client
# Let's them open one and not much more
class FakeConnectionThread(threading.Thread):
    def __init__(self, socket, urls):
        threading.Thread.__init__(self)
        self.socket = socket
        self.urls = urls
        
    # Get initial request
    def get_initial_request(self):
        request = ""
        
        while(True):
            r,w,x = select.select([self.socket],[],[],0)
            if len(r) > 0:
                request += self.socket.recv(2**22)
                # TODO: We're ignoring the possibility of the 
                # break occuring on the message body. So fix it
                if request[-4:] == "\r\n\r\n":
                    break
            if self.killed:
                return -1
                
        self.request = request
        
        if self.request.lower().startswith("connect "):
            print "CONNECT request found. Quitting"
            self.socket.sendall("HTTP/1.0 404 Not Found\r\n\r\n")
            return -1
            
        for header in self.request.split('\r\n'):
            if header.lower().startswith("referer:"):
                self.has_ref = True
                break
        
        # Add self and url to the thread list
        self.url = fixurl(self.request.split()[1])
        
        return 0
        
    # Runs
    def run(self):
        import urllib
        import zlib
        import time
        
        # Get the request
        if self.get_initial_request() == -1:
            return
            
        if self.url in self.urls:
            print "pre"
            time.sleep(1)
            print self.url, "hit"
            file = self.urls[self.url]
            with open(file,'rb') as f:
                data = f.read()
            self.socket.sendall(data)   
        else:
            print self.url, "NO hit"
            self.socket.sendall("")
            
        self.socket.close()

# Fakes the CovertCast client and returns presaved files
# urls is dictionary of urls to files to return 
class FakeWebClient(threading.Thread):
    def __init__(self, urls):
        threading.Thread.__init__(self)
        self.urls = urls

    def run(self):
        
        # Create socket for browser
        insocket = socket.socket(socket.AF_INET,type=socket.SOCK_STREAM)
        insocket.bind((ip, port))
        insocket.listen(1)
        
        while(1):
            try:
                # Process requests from browser
                r ,_ ,_ = select.select([insocket],[],[],0)
                if len(r):
                    # Get the socket
                    remote, addr = insocket.accept()
                    
                    newthread = FakeConnectionThread(remote, self.urls)
                    newthread.start()
            except:
                break
            
                
                
                
                
                
