# Some Video Testing Code
# Called from client.py

#from . import functions
from . import modulate
from . import video_helper_functions as vhf

# python client -time
def function_speeds(service):
    modulate.modulation_speeds(service)

def modulation_test(service):
    print("Testing modulation/demodulation")
    if modulate.test(service):
        print("PASS\n")
    else:
        print("FAIL\n")
        
def vhf_test():
    print("Testing video help functions")
    vhf.test()
        
# python client -test
def test(service):
    modulation_test(service)
    vhf_test()

# python client -imtest location
def image_test(service, image_location):
    modulate.image_test(service, image_location)