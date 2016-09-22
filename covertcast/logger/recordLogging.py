import multiprocessing

def make_file(file):
    import os
    try: 
        os.makedirs(file)
    except OSError:
        if not os.path.isdir(file):
            raise
    return

class RecordListener(multiprocessing.Process):
    def __init__(self, queue, log_location, cache=True):
        multiprocessing.Process.__init__(self)
        self.configure(log_location, cache)
        self.queue = queue

        
    def configure(self, log_location, cache):
        make_file(log_location)
        
        if log_location[-1] != "/" or log_location[-1] != "\\":
            log_location += "/"

        if cache:
            make_file(log_location + "cache/")
            
        self.requests = log_location+"Requests.log" 
        self.whitelists = log_location+"WhiteLists.log"
        self.responses = log_location+"Responses.log"
        self.general = log_location+"General.log"
        self.server = log_location+"Server.log"
        
    def run(self):
        while True:
            try:
                record = self.queue.get()
                if record is None: # We send this to tell the listener to quit.
                    break
                
                rec_type = record[0]
                rec_data = record[1]
                
                if rec_type.lower() == "request":
                    with open(self.requests, 'ab') as f:
                        f.write(rec_data)
                elif rec_type.lower() == "whitelist":
                    with open(self.whitelists, 'ab') as f:
                        f.write(rec_data)
                elif rec_type.lower() == "response":
                    with open(self.responses, 'ab') as f:
                        f.write(rec_data)
                elif rec_type.lower() == "general":
                    with open(self.general, 'ab') as f:
                        f.write(rec_data)
                elif rec_type.lower() == "server":
                    with open(self.server, 'ab') as f:
                        f.write(rec_data)
                else:
                    print "Bad rec type:", rec_type

            except Exception as e:
                print e


