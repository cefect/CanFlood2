'''
Created on Mar 11, 2025

@author: cef

helper functions for working with tutorial data in the tests
'''

import os, logging, sys, hashlib
import pytest
import pandas as pd

from qgis.core import (
    QgsApplication, QgsProject, Qgis, QgsLogger, QgsMessageLog,
    QgsRasterLayer, QgsVectorLayer, QgsProject,
    )

from pytest_qgis.utils import clean_qgis_layer

from canflood2.assertions import assert_eventMeta_df

from canflood2.parameters import src_dir, project_db_schema_d

#===============================================================================
# parameters
#===============================================================================
test_data_dir = os.path.join(src_dir, 'tests', 'data')

widget_settings_d = {
    #model config dialog widget data related to specific tutorials
    'cf1_tutorial_02': {
        'comboBox_AI_elevType':'ground',
        'mFieldComboBox_cid':'xid',
        'mFieldComboBox_AI_01_scale':'f0_scale',
        'mFieldComboBox_AI_01_elev':'f0_elev',
        'mFieldComboBox_AI_01_tag':'f0_tag',
        'mFieldComboBox_AI_01_cap':'f0_cap',    
    },
    }


#===============================================================================
# functions
#===============================================================================
def get_test_data_filepaths_for_tutorials(
        search_dirs = ['cf1_tutorial_01', 'cf1_tutorial_02'],
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
                    
                elif file.startswith('vfunc'):
                    assert file.endswith('.xls'), f'bad file: {file}'
                    d['vfunc'] = os.path.join(root, file)
                    
                else:
                    raise IOError(f'unrecognized file: {file}')
                    
            data_lib[tutorial_name] = d
            
    return data_lib

tutorial_data_lib = get_test_data_filepaths_for_tutorials()

#===============================================================================
# FIXTURES
#===============================================================================
@pytest.fixture
def tutorial_name(request):
    return getattr(request, "param", None)


@pytest.fixture
def dem_fp(tutorial_name):
    if tutorial_name is None:
        return None
    return tutorial_data_lib[tutorial_name]['dem']

@pytest.fixture
def aoi_fp(tutorial_name):
    if tutorial_name is None:
        return None
    return tutorial_data_lib[tutorial_name]['aoi']

@pytest.fixture
def finv_fp(tutorial_name):
    if tutorial_name is None:
        return None
    return tutorial_data_lib[tutorial_name]['finv']

@pytest.fixture
def haz_fp_d(tutorial_name):
    if tutorial_name is None:
        return None
    return tutorial_data_lib[tutorial_name]['haz']

@pytest.fixture
def eventMeta_fp(tutorial_name):
    if tutorial_name is None:
        return None
    return tutorial_data_lib[tutorial_name]['eventMeta']



@pytest.fixture(scope='function')
@clean_qgis_layer
def dem_rlay(dem_fp):
    if dem_fp is None:
        return None
    layer = QgsRasterLayer(dem_fp, 'dem_rlay')
    QgsProject.instance().addMapLayer(layer)
    return layer

@pytest.fixture(scope='function')
@clean_qgis_layer
def aoi_vlay(aoi_fp):
    if aoi_fp is None:
        return None
    assert os.path.exists(aoi_fp), f'bad filepath on aoi_vlay fixture:\n    {aoi_fp}'
    layer = QgsVectorLayer(aoi_fp, 'aoi_vlay', 'ogr')
    assert isinstance(layer, QgsVectorLayer)
    QgsProject.instance().addMapLayer(layer)
    return layer

@pytest.fixture(scope='function')
@clean_qgis_layer
def finv_vlay(finv_fp):
    if finv_fp is None:
        return None
    assert os.path.exists(finv_fp), f'bad filepath on finv_vlay fixture:\n    {finv_fp}'
    layer = QgsVectorLayer(finv_fp, 'finv_vlay', 'ogr')
    assert isinstance(layer, QgsVectorLayer)
    QgsProject.instance().addMapLayer(layer)
    return layer

@pytest.fixture(scope='function')
@clean_qgis_layer
def haz_rlay_d(haz_fp_d):
    if haz_fp_d is None:
        return None
    d = {}
    for ari, fp in haz_fp_d.items():
        layer = QgsRasterLayer(fp, os.path.basename(fp).split('.')[0])
        QgsProject.instance().addMapLayer(layer)
        d[layer.name()] = layer
    return d

@pytest.fixture(scope='function')
def eventMeta_df(eventMeta_fp, haz_rlay_d):
    if eventMeta_fp is None:
        return None
    print(f'loading eventMeta_df from {eventMeta_fp}')   
    df = pd.read_csv(eventMeta_fp, dtype=project_db_schema_d['05_haz_events'].dtypes.to_dict())
    
    # Map layer IDs and file paths from haz_rlay_d.
    df['layer_id'] = df.iloc[:, 0].map(pd.Series({k: v.id() for k, v in haz_rlay_d.items()}))
    df['layer_fp'] = df.iloc[:, 0].map(pd.Series({k: v.source() for k, v in haz_rlay_d.items()}))
    
    assert_eventMeta_df(df)
    return df