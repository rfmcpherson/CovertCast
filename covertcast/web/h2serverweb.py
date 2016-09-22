import functools
import multiprocessing
import pickle
import socket
import sys
import time
import traceback
import zlib

from . import h2guides

#TODO: Add support for 302s by including the 'Location' header

# Number of formatPackets running at a time
num_workers = 4
    
# The class that handles the HTTP side of the server
# Uses class Guide to pick which URLs to send
class WebServer(multiprocessing.Process):

    def __init__(self, packet_queue, kill_e, next_page_e, flags):
        multiprocessing.Process.__init__(self)

        self.output_q = packet_queue
        self.kill_e = kill_e
        self.next_page_e = next_page_e
        self.skip_vid = flags[0] 
        self.skip_guide = flags[1]
        
        self.count = 0

        if self.skip_guide:
            self.guide = h2guides.RawGuide()
        else:
            #self.guide = h2guides.BBCGuide() 
            #self.guide = h2guides.NYTimesMobileGuide() 
            self.guide = h2guides.USATodayGuide() 
            #self.guide = h2guides.WSJGuide() 
            #self.guide = h2guides.GuardianGuide() 
            #self.guide = h2guides.WPostGuide() 

    
    # content_l is [ [(str) url, (int) status, (bytes) content], ...]
    # converts above to [ b"{len} 1 url status content", ... ]
    def _encode_content_l(self, content_l):
        packets = []
                
        for resource in content_l:

            # craft packet
            packet =  b" " + b'\x01'
            packet += b" " + bytes(resource.url, encoding='utf-8')
            packet += b" " + resource.status.to_bytes(
                length=(resource.status.bit_length() // 8) + 1, byteorder='big')
            packet += b" " + resource.data 

            packets.append(packet)

        return packets

    def _format_packet(self, packet):
        try:

            # compress packet
            packet = zlib.compress(packet)
            
            # add length
            length = len(packet)
            length = length.to_bytes(length=4, byteorder='big')
            packet = length + packet
            
            # add to output queue
            self.output_q.put(packet)
        except Exception as e:
            print("Exception in formatPacket:", e)
            traceback.print_tb(sys.exc_info()[2])
        return


    # send the packets over images
    # packets is a list of structurally agnostic packets
    def _send_packets(self, packets):

        for packet in packets:
            self._format_packet(packet)
        

    def run(self):
        while(not self.kill_e.is_set()):

            # spin on next_page_e
            if not self.next_page_e.wait(1):
                continue
            else:
                self.next_page_e.clear()

            # get next set of data to send
            if self.count <= 3:
                content_l = self.guide.next()
                self.count += 1
            
                # prepare 
                packets = self._encode_content_l(content_l)
                #packets.append(self._encode_url_l(url_l))            
                
                # send packets
                self._send_packets(packets)

        # kill_e set, so end
        self.output_q.cancel_join_thread()
        print("WebSever closed")
        return
    
    
def main():
    kill_e = multiprocessing.Event()
    output_q = multiprocessing.Queue()

    server = WebServer(output_q, kill_e, [None, True, None])
    server.run()
    

if __name__ == "__main__":
    main()
