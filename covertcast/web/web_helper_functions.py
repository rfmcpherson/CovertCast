# Returns host, port, and path from URL
def decode_url(url):
    doubleSlash = url.find("//")
    if doubleSlash != -1:
        url = url[doubleSlash+2:]
        
    colon = url.find(":")
    slash = url.find("/")
    if slash != -1 and colon > slash:
        colon = -1
    question = url.find("?")
    if colon == -1:
        port = 80
        if slash != -1:
            host = url[:slash]
            path = url[slash:]
        elif question != -1:
            host = url[:question]
            path = url[question:]
        else:
            host = url
            path = "/"
    else:
        host = url[:colon]
        if slash != -1:
            port = url[colon+1:slash]
            path = url[slash:]
        elif question != -1:
            port = url[colon+1:question]
            path = url[question:]
        else:
            port = url[colon+1:]
            path = "/"
    
    return host, port, path

# Currently unused
def create_request(host, port, path):
    # TODO: Make this dynamically change with initial request
    method = "GET "
    http = " HTTP/1.1\r\nHost: "
    rest = "\r\nUser-Agent: Mozilla/5.0 (Linux; Android 4.0.4; Galaxy Nexus Build/IMM76B) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.133 Mobile Safari/535.19\r\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Encoding: gzip, deflate\r\nConnection: keep-alive\r\n\r\n"
    request = method + path
    if port != 80:
        request += ":" + str(port)
    request += http + host + rest
    return request
        
# Formats requests
# TODO: This is ugly as can be. Fix that.
def format_request(request):    
    headers = request.split()
    address = headers[1]
    host, port, path = decode_url(address)
    request = request.replace(headers[1],path)
    headers = request.split('\r\n')
    for header in headers:
        if header == "":
            break
        if header.lower().startswith("accept-encoding"):
            request = request.replace(header+"\r\n","")
            break
    # TODO: format requests with "Connection: close"
    return request, address
    
# Returns host and port from request
def host_from_request(request):
    headers = request.lower().split()
    if "host:" in headers:
        host = headers[headers.index("host:")+1].strip()
    # TODO: See if "hosts" are ever different
    if host:
        _, port, _ = decode_url(headers[1])
    else:
        host, port, _ = decode_url(headers[1])
    return host, int(port)
    
# Find the request type
def method_type(request):
    methods = ["get","head","post","put","delete","trace","connect"]
    for method in methods:
        if request.lower().startswith(method):
            return method
    # TODO: Exception
    print "No method found!"
    return -1
    
# Connect
def connect(host, port):
    import socket
    # TODO: throw errors
    try:
        sock = socket.create_connection((host, port))
    except socket.timeout:
        print "End connection timed out", host
        sock.close()
        return -1
    except socket.error:
        print "End connection timed out", host
        try:
            sock.close() 
        except Exception as e:
            pass
        return -1
    except socket.gaierror:
        print "End connection timed out", host
        sock.close()
        return -1
    return sock

def request_done(request):
    # If it doesn't have "\r\n\r\n", then it's not done
    if not "\r\n\r\n" in request:
        return False
    index = request.index("\r\n\r\n")
    headers = request[:index]
    body = request[index+4:]
    
    # If it has a Content-Length header,
    # check if the body is all there
    for header in headers.split("\r\n"):
        if header.lower().startswith("content-length:"):
            length = int(header.split(" ")[1])
            if len(body) == length:
                return True
            else:
                return False
    # If it doesn't have a Content-Length header:
    # see if we're at the end 
    # (it shouldn't be possible to return False if
    # the request is well formed)
    if request[-4:] == "\r\n\r\n":
        return True
    else:
        return False
        
