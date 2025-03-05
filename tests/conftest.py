'''
Created on Apr. 16, 2024

@author: cef
'''
import os, logging, sys
import pytest
 



#from canflood2.parameters import plugin_dir

#===============================================================================
# data
#===============================================================================
 


#===============================================================================
# fixtrues--------
#===============================================================================



@pytest.fixture(scope='function')
def logger():
    logging.basicConfig(
                #filename='xCurve.log', #basicConfig can only do file or stream
                force=True, #overwrite root handlers
                stream=sys.stdout, #send to stdout (supports colors)
                level=logging.INFO, #lowest level to display
                format='%(asctime)s %(levelname)s %(name)s: %(message)s',  # Include timestamp
                datefmt='%H:%M:%S'  # Format for timestamp
                )
    
    #get a new logger and lower it to avoid messing with dependencies
    log = logging.getLogger(str(os.getpid()))
    log.setLevel(logging.DEBUG)
    
    
    return log

 