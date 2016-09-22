import ssl
import os
import urllib
import asyncio
import io

import nghttp2

@asyncio.coroutine
def get_http_header(handler, url):
    url = urllib.parse.urlsplit(url)
    ssl = url.scheme == 'https'
    if url.port == None:
        if url.scheme == 'https':
            port = 443
        else:
            port = 80
    else:
        port = url.port

    connect = asyncio.open_connection(url.hostname, port, ssl=ssl)
    reader, writer = yield from connect
    req = 'GET {path} HTTP/1.0\r\n\r\n'.format(path=url.path or '/')
    writer.write(req.encode('utf-8'))
    # skip response header fields
    while True:
        line = yield from reader.readline()
        line = line.rstrip()
        if not line:
            break
    # read body
    while True:
        b = yield from reader.read(4096)
        if not b:
            break
        handler.buf.write(b)
    writer.close()
    handler.buf.seek(0)
    handler.eof = True
    handler.resume()

class Body:
    def __init__(self, handler):
        self.handler = handler
        self.handler.eof = False
        self.handler.buf = io.BytesIO()

    def generate(self, n):
        buf = self.handler.buf
        data = buf.read1(n)
        if not data and not self.handler.eof:
            return None, nghttp2.DATA_DEFERRED
        return data, nghttp2.DATA_EOF if self.handler.eof else nghttp2.DATA_OK

class Handler(nghttp2.BaseRequestHandler):

    def on_headers(self):
        body = Body(self)
        asyncio.async(get_http_header(
            self, 'http://localhost' + self.path.decode('utf-8')))
        self.send_response(status=200, body=body.generate)

ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
ctx.options = ssl.OP_ALL | ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3
ctx.load_cert_chain('../cert/server.crt', '../cert/server.key')

server = nghttp2.HTTP2Server(('localhost', 8080), Handler, ssl=ctx)
server.serve_forever()