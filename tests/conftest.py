'''
Created on Apr. 16, 2024

@author: cef
'''
 
import os, logging, sys
import pytest
 

from qgis.core import QgsApplication, QgsProject, Qgis, QgsLogger, QgsMessageLog
from canflood2.hp.logr import get_log_stream

from canflood2.parameters import src_dir
 
 
#===============================================================================
# data
#===============================================================================
test_data_dir = os.path.join(src_dir, 'tests', 'data')


#===============================================================================
# configure QGIS loggers for testing
#===============================================================================
conftest_logger = get_log_stream(name='pytest', level = logging.DEBUG) #special name to not conflict with fixture
 
def log_to_python(message, tag, level):
    """build action to connect to QgsMessageLog
    
    NOTE: Qgis.Critical seems to be printed twice. 
    """
    # Map QgsMessageLog level to Python logging level
    level_map = {
        #note there is no Debug level in QgsMessageLog
        Qgis.Info: logging.INFO,
        Qgis.Warning: logging.WARNING,
        Qgis.Critical: logging.ERROR,
    } 
 
    # Log the message using Python's logging module
    conftest_logger.log(level_map.get(level, logging.DEBUG), "[%s] %s", tag, message)
  


#===============================================================================
# pytest custom config
#===============================================================================
 

def pytest_runtest_teardown(item, nextitem):
    """custom teardown message"""
    test_name = item.name
    print(f"\n{'='*20} Test completed: {test_name} {'='*20}\n\n\n")
    
def pytest_report_header(config):
    """modifies the pytest header to show all of the arguments"""
    return f"pytest arguments: {' '.join(config.invocation_params.args)}"


#===============================================================================
# fixtrues--------
#===============================================================================



@pytest.fixture(scope='session')
def logger():    
    """fixture for QGIS indepednetn logger
    
    """
    
    #connect to QgsApplication/QgsMessageLog
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

 