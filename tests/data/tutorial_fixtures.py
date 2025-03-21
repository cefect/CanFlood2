'''
Created on Mar 11, 2025

@author: cef

helper functions for working with tutorial data in the tests
'''

import os, logging, sys, hashlib, shutil
import pytest
import pandas as pd

from qgis.core import (
    QgsApplication, QgsProject, Qgis, QgsLogger, QgsMessageLog,
    QgsRasterLayer, QgsVectorLayer, QgsProject,
    )

from pytest_qgis.utils import clean_qgis_layer

 
from canflood2.assertions import assert_df_matches_projDB_schema
from canflood2.parameters import src_dir, project_db_schema_d
from canflood2.tutorials.tutorial_data_builder import tutorial_data_lib, widget_values_lib


#===============================================================================
# FIXTURES---------------
#===============================================================================
@pytest.fixture
def tutorial_name(request):
    return getattr(request, "param", None)

#===============================================================================
# FIXTURES:FILEPATHS------------
#===============================================================================

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

@pytest.fixture
def vfunc_fp(tutorial_name, tmpdir):
    if tutorial_name is None:
        return None
    
    #copy over to the testin directory for relative pathing
    fp = tutorial_data_lib[tutorial_name]['vfunc']

    return shutil.copyfile(fp, os.path.join(tmpdir, os.path.basename(fp)))

#===============================================================================
# FIXTURES:OBJECTS------------
#===============================================================================
@pytest.fixture(scope='function')
@clean_qgis_layer
def dem_rlay(dem_fp):
    #if dem_fp is None:return None
    layer = QgsRasterLayer(dem_fp, 'dem_rlay')
    QgsProject.instance().addMapLayer(layer)
    print(f'dem_rlay fixture instantiated from {dem_fp}')
    return layer

@pytest.fixture(scope='function')
@clean_qgis_layer
def aoi_vlay(aoi_fp):
    #if aoi_fp is None:return None
    assert os.path.exists(aoi_fp), f'bad filepath on aoi_vlay fixture:\n    {aoi_fp}'
    layer = QgsVectorLayer(aoi_fp, 'aoi_vlay', 'ogr')
    assert isinstance(layer, QgsVectorLayer)
    QgsProject.instance().addMapLayer(layer)
    print(f'aoi_vlay fixture instantiated from {aoi_fp}')
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
    
    assert_df_matches_projDB_schema('05_haz_events', df)
 
    return df


 
@pytest.fixture
def widget_modelConfig_data_d(tutorial_name):
    #if tutorial_name is None:        return None
    return widget_values_lib[tutorial_name]['Model_config_dialog']

@pytest.fixture
def widget_Main_dialog_data_d(tutorial_name):
 
    return widget_values_lib[tutorial_name]['Main_dialog']









