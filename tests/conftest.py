'''
Created on Apr. 16, 2024

@author: cef
'''
 
import os, logging, sys, hashlib
import pytest
import pandas as pd
from pytest_qgis.utils import clean_qgis_layer
 
from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt 

from qgis.core import (
    QgsApplication, QgsProject, Qgis, QgsLogger, QgsMessageLog,
    QgsRasterLayer, QgsVectorLayer, QgsProject,
    )
 

from canflood2.hp.logr import get_log_stream
from canflood2.hp.basic import sanitize_filename

from canflood2.parameters import src_dir, hazDB_schema_d


 
 
#===============================================================================
# data----------
#===============================================================================
test_data_dir = os.path.join(src_dir, 'tests', 'data')

from .data.tutorial_data_builder import *
 


#===============================================================================
# configure QGIS loggers for testing
#===============================================================================
conftest_logger = get_log_stream(name='pt', level = logging.DEBUG) #special name to not conflict with fixture
 
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
# FIXTURES--------
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


@pytest.fixture
def projDB_fp(request):
    return getattr(request, "param", None)

 
    

#===============================================================================
# HERLPERS---------
#===============================================================================
def fake_getOpenFileName(parent, caption, directory, filter, **kwargs):
    if caption == "Select Vulnerability Function Set":
        # Return a specific fake file path for this call.
        return ("/path/to/fake_vfunc.xlsx", "")
    # For other dialogs, you can either provide different return values or
    # delegate to the original function if needed.
    return ("", "")


def click(widget):
    widgetname = widget.objectName() if widget.objectName() else str(widget)
    
    #check that the widget is enabled
    assert widget.isEnabled(), f'widget is not enabled: {widgetname}'
    sys.stdout.flush()
    print(f"\n\nclicking: \'{widgetname}\'\n{'=' * 80}\n\n")
    return QTest.mouseClick(widget, Qt.LeftButton)
 

def result_write_filename_prep(test_name, char_max=25, clear_str='test_dial_main_'):
    """cleaning up the pytest names to use for auto result writing"""

    test_name1 = sanitize_filename(test_name)
    test_name1 = test_name1.replace(clear_str, '').replace('__', '_')

    if len(test_name1) > char_max:
        # Generate a 6-digit hash of the raw test_name
        hash_suffix = hashlib.md5(test_name.encode()).hexdigest()[:6]
        return f"{test_name1[:char_max]}_{hash_suffix}"
    else:
        return test_name1[:char_max]



 