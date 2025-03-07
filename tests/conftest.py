'''
Created on Apr. 16, 2024

@author: cef
'''
 
import os, logging, sys
import pytest
 

from qgis.core import QgsApplication, QgsProject, Qgis, QgsLogger, QgsMessageLog
from canflood2.hp.logr import get_log_stream

 
#===============================================================================
# data
#===============================================================================



#===============================================================================
# configure QGIS loggers for testing
#===============================================================================
conftest_logger = get_log_stream(name='conftest', level = logging.DEBUG) #special name to not conflict with fixture
 
def log_to_python(message, tag, level):
    """build action to connect to QgsMessageLog"""
    # Map QgsMessageLog level to Python logging level
    level_map = {
        #note there is no Debug level in QgsMessageLog
        Qgis.Info: logging.INFO,
        Qgis.Warning: logging.WARNING,
        Qgis.Critical: logging.ERROR,
    } 
 
    # Log the message using Python's logging module
    conftest_logger.log(level_map.get(level, logging.DEBUG), "[%s] %s", tag, message)
  
# Connect the function to QgsMessageLog
"""seems to only be called when contest is explicitly imported"""
#QgsApplication.messageLog().messageReceived.connect(log_to_python)
 
"""not sure how to capture this
QgsLogger.messageReceived.connect(log_to_python)"""


#===============================================================================
# fixtrues--------
#===============================================================================



@pytest.fixture(scope='function')
def logger():    
    """fixture for QGIS indepednetn logger"""
    
    #connect to QgsApplication
    """redundant in some cases, but seems to be the simplest way to 
    connect the logger for cases where conftest is not imported
    just need to ensure the logger fixture is called"""
    QgsApplication.messageLog().messageReceived.connect(log_to_python)
    
    #===========================================================================
    # logging.basicConfig(
    #             #filename='xCurve.log', #basicConfig can only do file or stream
    #             force=True, #overwrite root handlers
    #             stream=sys.stdout, #send to stdout (supports colors)
    #             level=logging.DEBUG, #lowest level to display
    #             format='%(asctime)s %(levelname)s %(name)s: %(message)s',  # Include timestamp
    #             datefmt='%H:%M:%S'  # Format for timestamp
    #             )
    #===========================================================================
     
    #get a new logger and lower it to avoid messing with dependencies
    #log = logging.getLogger(str(os.getpid()))
    #log = conftest_logger.getChild(str(os.getpid()))
    #log.setLevel(logging.DEBUG)
    
    #===========================================================================
    # # Create a formatter with the desired format string
    # formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt='%M:%S')
    # 
    # # Assuming mod_logger already has handlers, modify the existing handler
    # for handler in mod_logger.handlers:
    #     if isinstance(handler, logging.StreamHandler):
    #         handler.setFormatter(formatter)
    #         break
    #===========================================================================
     
     
    return conftest_logger



@pytest.fixture
def test_name(request):
    return request.node.name

 