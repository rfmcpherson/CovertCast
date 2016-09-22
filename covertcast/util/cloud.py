#from libcloud.storage.types import Provider, ContainerDoesNotExistError, ObjectDoesNotExistError

def StandardPath(OutDirectory,CreateIfNotExist):
    """
    Convert path to standard format.
    """
    from os import path,makedirs,name

    if(name == 'nt'): 
        print("\nStandardPath() not currently working in Windows." )
        print("Make sure " + OutDirectory + " exists.\n")
    else:
        OutDirectory=path.expanduser(OutDirectory)
        OutDirectory=path.abspath(OutDirectory)
        if not OutDirectory[-1]=='/': OutDirectory=OutDirectory+'/'     
        if not path.isdir(OutDirectory):
            if CreateIfNotExist:
                print("Creating image directory")
                makedirs(OutDirectory)
            else:
                print("Directory does not exist")      
    return OutDirectory
    
def file_exists(container,key):
    """
    Check if a file exists in the cloud storage
    Arugments:
    container - directory of the storage
    key - name in the storage
    """
    from os.path import isfile
    return isfile(container+key)


def fetch_and_del(container,key):
    """
    fetch the contents of a file from the cloud and delete the file
    Arugments:
    container - directory container for the storage
    key - name in the storage
    """
    from os import remove
    if file_exists(container,key)==True:
        with open(container+key,'rb') as r:
            message = r.read()
        remove(container+key)
        #print "Read file. Length:", len(message)
        return message
    else:
        return None
    """
    try:
        obj = container.get_object(key)
        message = b''.join(obj.as_stream())
        if not obj.delete():
            logging.error("Error deleting object from the cloud!")
        return message
    except ObjectDoesNotExistError:
        return None
    """
def delete_if_present(container,key):
    """
    Delete the file 'key' from the container if it is present. If it is not present do nothing
    """
    from os import remove
    if file_exists(container,key):    
        remove(container+key)
    

    """
    try:
        obj = container.get_object(key)
        obj.delete()
    except ObjectDoesNotExistError:
        pass
    """
    
    
    
" TODO: remove this, dont need it"    
def container_alive(container):
    """
    Check if the container is still usable, sometimes the container's SSL connection dies out from under us
    Arugments:
    container - libcloud container for the storage
    """
    try:
        container.get_object("running")
        return True
    except:
        return False
