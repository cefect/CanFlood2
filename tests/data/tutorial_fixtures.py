'''
Created on Mar 11, 2025

@author: cef

helper functions for working with tutorial data in the tests
'''

import os, logging, sys, hashlib, shutil, copy
import pytest
import pandas as pd

from qgis.core import (
    QgsApplication, QgsProject, Qgis, QgsLogger, QgsMessageLog,
    QgsRasterLayer, QgsVectorLayer, QgsProject,
    )

from pytest_qgis.utils import clean_qgis_layer

 
from canflood2.assertions import assert_df_matches_projDB_schema
from canflood2.parameters import src_dir, project_db_schema_d
from canflood2.tutorials.tutorial_data_builder import tutorial_lib

#===============================================================================
# helpers
#===============================================================================
# Define the common helper function
def _get_data_fp(tutorial_name, data_key):
    if tutorial_name is None:
        return None
    if data_key not in tutorial_lib[tutorial_name]['data']:
        return None
    return tutorial_lib[tutorial_name]['data'][data_key]


#===============================================================================
# FIXTURES---------------
#===============================================================================
@pytest.fixture
def tutorial_name(request):
    return getattr(request, "param", None)

#===============================================================================
# FIXTURES:FILEPATHS------------
#===============================================================================




# Refactored fixtures
@pytest.fixture
def dem_fp(tutorial_name):
    return _get_data_fp(tutorial_name, 'dem')

@pytest.fixture
def aoi_fp(tutorial_name):
    return _get_data_fp(tutorial_name, 'aoi')

@pytest.fixture
def finv_fp(tutorial_name):
    return _get_data_fp(tutorial_name, 'finv')

@pytest.fixture
def haz_fp_d(tutorial_name):
    return _get_data_fp(tutorial_name, 'haz')

@pytest.fixture
def eventMeta_fp(tutorial_name):
    return _get_data_fp(tutorial_name, 'eventMeta')

@pytest.fixture
def vfunc_fp(tutorial_name, tmpdir):
    fp = _get_data_fp(tutorial_name, 'vfunc')
    if fp is None:
        return None
    # Copy over to the testing directory for relative pathing
    return shutil.copyfile(fp, os.path.join(tmpdir, os.path.basename(fp)))


#===============================================================================
# FIXTURES:OBJECTS------------
#===============================================================================
get_fn = lambda x: os.path.splitext(os.path.basename(x))[0]

@pytest.fixture(scope='function')
@clean_qgis_layer
def dem_rlay(dem_fp, tutorial_name):
    
    if dem_fp is None:return None
    layer = QgsRasterLayer(dem_fp, get_fn(dem_fp))
    QgsProject.instance().addMapLayer(layer)
    print(f'dem_rlay fixture instantiated from {dem_fp}')
    return layer

@pytest.fixture(scope='function')
@clean_qgis_layer
def aoi_vlay(aoi_fp, tutorial_name):
    if aoi_fp is None: return None
 
    assert os.path.exists(aoi_fp), f'bad filepath on aoi_vlay fixture:\n    {aoi_fp}'
    layer = QgsVectorLayer(aoi_fp, get_fn(aoi_fp), 'ogr')
    assert isinstance(layer, QgsVectorLayer)
    QgsProject.instance().addMapLayer(layer)
    print(f'aoi_vlay fixture instantiated from {aoi_fp}')
    return layer

@pytest.fixture(scope='function')
@clean_qgis_layer
def finv_vlay(finv_fp, tutorial_name):
    if finv_fp is None:
        return None
    assert os.path.exists(finv_fp), f'bad filepath on finv_vlay fixture:\n    {finv_fp}'
    layer =  QgsVectorLayer(finv_fp, get_fn(finv_fp), 'ogr')

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
        layer = QgsRasterLayer(fp, get_fn(fp))
        QgsProject.instance().addMapLayer(layer)
        d[layer.name()] = layer
        
    print(f'haz_rlay_d fixture instantiated w/ {len(d)} layers')
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
    
    assert_df_matches_projDB_schema('05_haz_events', df)
 
    return df


@pytest.fixture(scope='function')
def probability_type(tutorial_name):
    return tutorial_lib[tutorial_name]['widget']['Main_dialog']['radioButton_ELari']


 
@pytest.fixture
def widget_modelConfig_data_d(tutorial_name):
    #if tutorial_name is None:        return None
    return copy.deepcopy(tutorial_lib[tutorial_name]['widget']['Model_config_dialog'])

@pytest.fixture
def widget_Main_dialog_data_d(tutorial_name): 
    return copy.deepcopy(tutorial_lib[tutorial_name]['widget']['Main_dialog'])


@pytest.fixture
def widget_FunctionGroup_t(tutorial_name):
    d = tutorial_lib[tutorial_name]['widget']
    if 'FunctionGroup' not in d:
        return None
    else:
        assert isinstance(d['FunctionGroup'], tuple), \
            f"Expected 'FunctionGroup' to be a tuple, got {type(d['FunctionGroup'])}"
        return copy.deepcopy(d['FunctionGroup'])
 









