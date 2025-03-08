'''
Created on Apr. 16, 2024

@author: cef
'''
 
import os, logging, sys
import pytest
from pytest_qgis.utils import clean_qgis_layer
 

from qgis.core import (
    QgsApplication, QgsProject, Qgis, QgsLogger, QgsMessageLog,
    QgsRasterLayer, QgsVectorLayer, QgsProject,
    )
 

from canflood2.hp.logr import get_log_stream

from canflood2.parameters import src_dir
 
 
#===============================================================================
# data
#===============================================================================
test_data_dir = os.path.join(src_dir, 'tests', 'data')

def get_test_data_filepaths_for_tutorials(
        search_dirs = ['cf1_tutorial_01', 'cf1_tutorial_02']
        ):
    """for each tutorial, build a hierarchiceal dicationary of filepaths
    search the contents and assign based on filename"""
    
    data_lib = dict()
    for tutorial_name in search_dirs:
        tutorial_dir = os.path.join(test_data_dir, tutorial_name)
        assert os.path.exists(tutorial_dir), f'bad tutorial_dir: {tutorial_dir}'
        
        #build the dictionary
        d = dict()
        for root, dirs, files in os.walk(tutorial_dir):
            for file in files:
                #only include tif and geojson
                if file.endswith(('.tif', '.geojson')):
                    pass
                else:
                    continue
                
                
                #collect hazard rasters as a diicttionary keyed by the ARI
                if file.startswith('haz'):
                    assert file.endswith('.tif'), f'bad file: {file}'
                    if not 'haz' in d:
                        d['haz'] = dict()
                    ari = int(file.split('_')[1].split('.')[0])
                    d['haz'][ari] = os.path.join(root, file)
                    
                #collect the dem
                elif file.startswith('dem'):
                    assert file.endswith('.tif'), f'bad file: {file}'
                    d['dem'] = os.path.join(root, file)
                    
                #collect the aoi
                elif file.startswith('aoi'):
                    assert file.endswith('.geojson'), f'bad file: {file}'
                    d['aoi'] = os.path.join(root, file)
                    
                #collect the asset inventory (finv) layer
                elif file.startswith('finv'):
                    assert file.endswith('.geojson'), f'bad file: {file}'
                    d['finv'] = os.path.join(root, file)
                    
            data_lib[tutorial_name] = d
            
    return data_lib
 
tutorial_data_lib = get_test_data_filepaths_for_tutorials()

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

#===============================================================================
# tutorial data
#===============================================================================
@pytest.fixture
def dem_fp(tutorial_name):
    return tutorial_data_lib[tutorial_name]['dem']

@pytest.fixture
def aoi_fp(tutorial_name):
    return tutorial_data_lib[tutorial_name]['aoi']

@pytest.fixture
def haz_fp_d(tutorial_name):
    return tutorial_data_lib[tutorial_name]['haz']



@pytest.fixture(scope='function')
@clean_qgis_layer
def dem_rlay(dem_fp):
    layer = QgsRasterLayer(dem_fp, 'dem_rlay')
    #qgis_new_project.addMapLayer(layer)
    QgsProject.instance().addMapLayer(layer) 
    return layer

@pytest.fixture(scope='function')
@clean_qgis_layer
def aoi_vlay(aoi_fp):
    assert os.path.exists(aoi_fp), f'bad filepath on aoi_vlay fixture:\n    {aoi_fp}'
    layer =  QgsVectorLayer(aoi_fp, 'aoi_vlay', 'ogr')
    assert isinstance(layer, QgsVectorLayer)
    QgsProject.instance().addMapLayer(layer)
    return layer 

@pytest.fixture(scope='function')
@clean_qgis_layer
def haz_rlay_d(haz_fp_d):
    d = dict()
    for ari, fp in haz_fp_d.items():
        layer = QgsRasterLayer(fp, f'haz_rlay_{ari}')
        QgsProject.instance().addMapLayer(layer)
        d[ari] = layer
    return d

 