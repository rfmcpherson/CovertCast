from collections import namedtuple

Resource = namedtuple("Resource", ["url", "status", "data"])

Request = namedtuple('Request', ['url', 'method', 'headers', 'body'])
Request.__new__.__defaults__ = (None, None, {}, b'')

Response = namedtuple('Response', ['status', 'headers', 'body'])
Response.__new__.__defaults__ = (200, {}, b'')
