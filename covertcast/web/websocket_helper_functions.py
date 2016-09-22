# Finds the client's key
def get_key(data):
	headers = data.split()
	if not b'Sec-WebSocket-Key:' in headers:
		# TODO: throw exception
		print "cannot find key!"
		return None
	return headers[headers.index(b'Sec-WebSocket-Key:')+1] 
    
# Generates server's response key
def response_key(key):
    import hashlib
    import base64
    key = key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    sha1 = hashlib.sha1()
    sha1.update(key)
    hash = sha1.digest()
    res_key = base64.b64encode(hash)
    return res_key
    
# Decodes the data from the WebSocket    
def decode_ws(data):
    data = [ord(x) for x in data] 
    if(data[0] == 136):
        return None
    if(data[0] != 129):
        # TODO: better
        print ord(data[0])
        print "NOT TEXT ENCODED! OH GOD, WHAT DO I DO?!"
        return None
    data_len = data[1] & 127
    start = 2
    if data_len == 126:
        data_len = data[2] << 8
        data_len = data_len | data[3]
        start = 4
    elif int(data_len) == 127:
        data_len = data[2] << 8
        data_len = (data_len | data[3]) << 8
        data_len = (data_len | data[4]) << 8
        data_len = (data_len | data[5]) << 8
        data_len = (data_len | data[6]) << 8
        data_len = (data_len | data[7]) << 8
        data_len = (data_len | data[8]) << 8
        data_len = (data_len | data[9])
        start = 10
    start = start + 4
    if len(data) <= data_len - start:
        return None

    mask = data[start-4:start]
    decoded = unicode("")
    j = 0
    for i in range(start, data_len + start):
        xor = data[i] ^ mask[j]
        try:
          decoded += unichr(data[i] ^ mask[j])
        except:
          pass
        j = (j + 1) % 4

    return decoded
