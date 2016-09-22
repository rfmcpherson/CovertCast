import configparser
import logging
from util import StandardPath

configList = {}
configList['test']=1

def load_config(fname):
    global configList
    #configList = {}
    parser = configparser.ConfigParser()
    parser.read(fname)
    log = parser.get("Logging","log")
    if log == 'warning':
        log = logging.WARNING
    elif log == 'error':
        log = logging.ERROR
    elif log == 'info':
        log = logging.INFO
    elif log == 'debug':
        log = logging.DEBUG
    else:
        print("Unknown logging level %s. defaulting to warning" % (log))
        log = logging.WARNING
    configList['logging'] = log
    configList['proxy'] = {'ip' : parser.get('Proxy','ip') , 'port' : parser.getint('Proxy','port')}

    container = parser.get("Storage","container")
    configList['container'] = StandardPath(container ,False)
    #print configList['container']
    containerImg1 = parser.get("Storage","containerImg1")
    configList['containerImg1'] = StandardPath(containerImg1 ,False)
    containerImg2 = parser.get("Storage","containerImg2")
    configList['containerImg2'] = StandardPath(containerImg2 ,False)
    cache = parser.get("Storage","cache")
    configList['cache'] = StandardPath(cache ,False)
    
#from libcloud.storage.types import Provider, ContainerDoesNotExistError
#from libcloud.storage.providers import get_driver

def get_container():
    #global configList 
    container = configList['container']
    return container
def get_containerImg1():
    global configImg1 
    configImg1 = configList['containerImg1']
    return configImg1
def get_containerImg2():
    global configImg2 
    configImg2 = configList['containerImg2']
    return configImg2
