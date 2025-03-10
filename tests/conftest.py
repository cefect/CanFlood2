'''
Created on Apr. 16, 2024

@author: cef
'''
 
import os, logging, sys, hashlib
import pytest
import pandas as pd
from pytest_qgis.utils import clean_qgis_layer
 

from qgis.core import (
    QgsApplication, QgsProject, Qgis, QgsLogger, QgsMessageLog,
    QgsRasterLayer, QgsVectorLayer, QgsProject,
    )
 

from canflood2.hp.logr import get_log_stream
from canflood2.hp.basic import sanitize_filename

from canflood2.parameters import src_dir, hazDB_schema_d

from canflood2.assertions import assert_eventMeta_df
 
 
#===============================================================================
# data----------
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
                if file.endswith(('.tif', '.geojson', '.csv')):
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
                    
                #evals from CanFloodf1
                elif file.startswith('eventMeta'):
                    assert file.endswith('.csv'), f'bad file: {file}'
                    d['eventMeta'] = os.path.join(root, file)
                    
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
def finv_fp(tutorial_name):
    return tutorial_data_lib[tutorial_name]['finv']

@pytest.fixture
def haz_fp_d(tutorial_name):
    return tutorial_data_lib[tutorial_name]['haz']

@pytest.fixture
def eventMeta_fp(tutorial_name):
    return tutorial_data_lib[tutorial_name]['eventMeta']


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
def finv_vlay(finv_fp):
    assert os.path.exists(finv_fp), f'bad filepath on finv_vlay fixture:\n    {finv_fp}'
    layer =  QgsVectorLayer(finv_fp, 'finv_vlay', 'ogr')
    assert isinstance(layer, QgsVectorLayer)
    QgsProject.instance().addMapLayer(layer)
    return layer

@pytest.fixture(scope='function')
@clean_qgis_layer
def haz_rlay_d(haz_fp_d):
    d = dict()
    for ari, fp in haz_fp_d.items():
        layer = QgsRasterLayer(fp, os.path.basename(fp).split('.')[0])
        QgsProject.instance().addMapLayer(layer)
        d[layer.name()] = layer
    return d

@pytest.fixture(scope='function')
def eventMeta_df(eventMeta_fp, haz_rlay_d):    
    df =  pd.read_csv(eventMeta_fp, dtype=hazDB_schema_d['05_haz_events'].dtypes.to_dict())
    
    #set the layer_ids
    df['layer_id'] = df.iloc[:,0].map(pd.Series({k:v.id() for k,v in haz_rlay_d.items()}))
    df['layer_fp'] = df.iloc[:,0].map(pd.Series({k:v.source() for k,v in haz_rlay_d.items()}))
    
    assert_eventMeta_df(df)
    
    return df
 
 
    

#===============================================================================
# HERLPERS---------
#===============================================================================

 

def test_result_write_filename_prep(test_name, char_max=25):
    """cleaning up the pytest names to use for auto result writing"""

    test_name1 = sanitize_filename(test_name)
    test_name1 = test_name1.replace('test_dial_main_', '').replace('__', '_')

    if len(test_name1) > char_max:
        # Generate a 6-digit hash of the raw test_name
        hash_suffix = hashlib.md5(test_name.encode()).hexdigest()[:6]
        return f"{test_name1[:char_max]}_{hash_suffix}"
    else:
        return test_name1[:char_max]


def assert_intersecting_values_match_verbose(expected_series, actual_series):
    # Determine the intersecting indexes.
    common_index = expected_series.index.intersection(actual_series.index)
    assert len(common_index) > 0, 'no common indexes found'
# Subset both series to only include intersecting keys.
    filtered_expected_series = expected_series.loc[common_index]
    filtered_actual_series = actual_series.loc[common_index]
# Compare the filtered series using pandas' compare().
    diff = filtered_expected_series.compare(filtered_actual_series, result_names=("expected", "actual"))
    if not diff.empty:
        raise AssertionError("Value mismatches found for common keys:\n" + diff.to_string())
 