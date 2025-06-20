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

get_fn = lambda x: os.path.splitext(os.path.basename(x))[0]
#===============================================================================
# FIXTURES---------------
#===============================================================================
@pytest.fixture
def tutorial_name(request):
    return getattr(request, "param", None)

#===============================================================================
# MAIN===================------------
#===============================================================================
#container retrival helpers
_get_MD_lib = lambda tut_name: copy.deepcopy(tutorial_lib[tut_name]['Main_dialog'])


_get_MD_fp = lambda tutorial_name, data_key: _get_MD_lib(tutorial_name)['data'].get(data_key, None)



# Refactored fixtures
@pytest.fixture
def dem_fp(tutorial_name):
    return _get_MD_fp(tutorial_name, 'dem')

@pytest.fixture
def aoi_fp(tutorial_name):
    return _get_MD_fp(tutorial_name, 'aoi')

@pytest.fixture
def haz_fp_d(tutorial_name):
    return _get_MD_fp(tutorial_name, 'haz')

@pytest.fixture
def eventMeta_fp(tutorial_name):
    return _get_MD_fp(tutorial_name, 'eventMeta')




#===============================================================================
# Main_Dialog.layers--------
#===============================================================================


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
def haz_rlay_d(haz_fp_d):
    if haz_fp_d is None:
        raise ValueError('haz_fp_d fixture requires a dictionary of file paths')
    
    d = {}
    for ari, fp in haz_fp_d.items():
        layer = QgsRasterLayer(fp, get_fn(fp))
        
        #check that a layer with the same name does not already exist on the project
        existing_layer = QgsProject.instance().mapLayersByName(layer.name())
        if len(existing_layer) > 0:
            raise IOError(f'A layer with the same name {layer.name()} already exists in the project. ')
        
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



#===============================================================================
# Main_Dialog.widget---------
#===============================================================================

_get_MD_widget = lambda tut_name: copy.deepcopy(tutorial_lib[tut_name]['Main_dialog']['widget'])


@pytest.fixture(scope='function')
def widget_Main_dialog_data_d(tutorial_name): 
    return _get_MD_widget(tutorial_name)

@pytest.fixture(scope='function')
def probability_type(tutorial_name):
    return _get_MD_widget(tutorial_name)['radioButton_ELari']

 



#===============================================================================
# MODELS============----------
#===============================================================================
def _get_model_lib(tut_name, consequence_category,  modelid): 
    return copy.deepcopy(tutorial_lib[tut_name]['models'][consequence_category][modelid])


#===============================================================================
# models.data--------
#===============================================================================
def _get_model_fp(tut_name, consequence_category, modelid, data_key):
    return _get_model_lib(tut_name, consequence_category, modelid)['data'].get(data_key, None)

@pytest.fixture(scope='function')
def finv_fp(tutorial_name, consequence_category, modelid):
    return _get_model_fp(tutorial_name, consequence_category, modelid, 'finv')


@pytest.fixture
def vfunc_fp(tutorial_name, consequence_category, modelid, tmpdir):
    fp = _get_model_fp(tutorial_name, consequence_category, modelid, 'vfunc')
 
    if fp is None:
        return None
    # Copy over to the testing directory for relative pathing
    return shutil.copyfile(fp, os.path.join(tmpdir, os.path.basename(fp)))


@pytest.fixture(scope='function')
@clean_qgis_layer
def finv_vlay(finv_fp):
    if finv_fp is None:
        return None
    assert os.path.exists(finv_fp), f'bad filepath on finv_vlay fixture:\n    {finv_fp}'
    layer =  QgsVectorLayer(finv_fp, get_fn(finv_fp), 'ogr')

    assert isinstance(layer, QgsVectorLayer)
    QgsProject.instance().addMapLayer(layer)
    return layer






#===============================================================================
# Models.widgets------
#===============================================================================

@pytest.fixture
def widget_modelConfig_data_d(tutorial_name, consequence_category, modelid):
    #if tutorial_name is None:        return None
    return _get_model_lib(tutorial_name, consequence_category, modelid)['widget'] 



@pytest.fixture
def widget_FunctionGroup_t(tutorial_name, consequence_category, modelid):
    d = _get_model_lib(tutorial_name, consequence_category, modelid)
    if 'FunctionGroup' not in d:
        return None
    else:
        assert isinstance(d['FunctionGroup'], tuple), \
            f"Expected 'FunctionGroup' to be a tuple, got {type(d['FunctionGroup'])}"
        return copy.deepcopy(d['FunctionGroup'])
 









