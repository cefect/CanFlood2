'''
Created on Jun 20, 2025

@author: cef

hadnling building/configuring of multi-model suites

Most testing should be in test_02_dialog_model.py and test_03_core.
    here, we focus on building multi-model suites for test_05_dialog_main_post
'''


import pytest, time, sys, inspect, os, shutil, copy
import pprint


from qgis.PyQt import QtWidgets

from qgis.core import (
    QgsApplication, QgsProject, Qgis, QgsLogger, QgsMessageLog,
    QgsRasterLayer, QgsVectorLayer, QgsProject,
    )

from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem, QComboBox,
    )


from canflood2.hp.qt import set_widget_value, get_widget_value
from canflood2.hp.basic import view_web_df as view


import tests.conftest as conftest
from .conftest import (
    conftest_logger, 
    result_write_filename_prep, click
    )




from tests.test_01_dialog_main import dialog_loaded, dialog_main
from tests.test_01_dialog_main import _04_MS_args, _04_MS_args_d

from tests.data.tutorial_fixtures import _get_model_fp, _get_model_lib, tutorial_lib



#===============================================================================
# params-----
#===============================================================================
interactive = False #interactive dialogs for tests
#overwrite_testdata_plugin=True 
overwrite_testdata=True #write test result projDB

#===============================================================================
# DATA--------
#===============================================================================
test_data_dir = os.path.join(conftest.test_data_dir, 'dialog_model_multi')
os.makedirs(test_data_dir, exist_ok=True)


#===============================================================================
# HELPERS-----
#===============================================================================
get_fn = lambda x: os.path.splitext(os.path.basename(x))[0]

def oj(*args):
    return os.path.join(test_data_dir, *args)

gfp = lambda x:oj(x, 'projDB.canflood2')

def oj_out(test_name, result):
    return oj(result_write_filename_prep(test_name, clear_str='dialog_model_multi_'), os.path.basename(result))
 
 


def write_projDB(dialog_main, test_name): 
    projDB_fp = dialog_main.get_projDB_fp()
    ofp = oj_out(test_name, projDB_fp)
 
    if overwrite_testdata:
        print(f'\n\nwriting projDB to \n    {test_name}\n{"="*80}')
        os.makedirs(os.path.dirname(ofp), exist_ok=True)
        
        #copy over the .sqlite file
        shutil.copyfile(projDB_fp, ofp) 
 
        conftest_logger.info(f'wrote result to \n    {ofp}')
        
        
        

 
#===============================================================================
# FIXTURES--------
#===============================================================================
@pytest.fixture
def dialog_main_loaded_multi(
                tutorial_name,
        dialog_loaded, model_keys,  
                #control fixtures        
        qtbot, monkeypatch,
        #backend init
        qgis_processing
        ):
    """prep the main dialog for multi-model tests"""
    
    

    
    #===========================================================================
    # prep
    #===========================================================================
    mc_dialog = dialog_loaded.Model_config_dialog
    # Override exec_() so it shows the dialog and returns immediately.
    def non_blocking_exec():
        mc_dialog.show()
        return QtWidgets.QDialog.Rejected  # dummy return value
    monkeypatch.setattr(mc_dialog, "exec_", non_blocking_exec)
    
    return dialog_loaded

@pytest.fixture
def finv_loaded_d(model_keys, tutorial_name):
    #===========================================================================
    # load all the model data to the project
    #===========================================================================
    data_d = dict()
    for (consequence_category, modelid) in model_keys:
        if not consequence_category in tutorial_lib[tutorial_name]['models']:
            raise KeyError(f'consequence_category {consequence_category} not found in tutorial {tutorial_name}')
        data_d[consequence_category] = {}
        
        #=======================================================================
        # finv
        #=======================================================================
        finv_fp = _get_model_fp(tutorial_name, consequence_category, modelid, 'finv')
        
        layer =  QgsVectorLayer(finv_fp, get_fn(finv_fp), 'ogr')
        
        assert isinstance(layer, QgsVectorLayer)
        QgsProject.instance().addMapLayer(layer)
        
        data_d[consequence_category][modelid] = layer
        
    print(f"\n\nloaded finv layers for {tutorial_name}:\n{pprint.pformat(data_d)}\n{'='*80}")
        
    return data_d

#===============================================================================
# TESTS---------
#===============================================================================
_get_MS_args = lambda x: (x, _04_MS_args_d[x]) #return the tutorial_name and projDB_fp




@pytest.mark.parametrize(
    "tutorial_name, projDB_fp, model_keys",
    [
        #pytest.param(*_get_MS_args('cf1_tutorial_01'), [('c1', 0)]),
        pytest.param('cf1_tutorial_02e', _04_MS_args_d['cf1_tutorial_02'], [('c1', 0), ('c2', 0)]),
        ])
def test_dialog_model_multi_01_configSave(
        tutorial_name,  model_keys, test_name,
        dialog_main_loaded_multi,
        
        #data loading fixtures
        finv_loaded_d,
 
        
        
        #control fixtures
        qtbot, tmpdir, monkeypatch
 
        ):
    """configuring all models in suite and saving the projDB"""
    
    #remaps
    dialog_main= dialog_main_loaded_multi
    dialog_model = dialog_main.Model_config_dialog

        
    
    #===========================================================================
    # #loop through each model and populate the widget
    #===========================================================================
    for (consequence_category, modelid) in model_keys:
        """NOTE: this mimics what the fixtures do in test_02_dialog_model.py"""
        
        model = dialog_main.model_index_d[consequence_category][modelid]
        print(f"\n\nlaunching model configuration dialog for \'{tutorial_name}\' {model.name}\n{'='*80}")
        
        #===========================================================================
        # # Launch the dialog by clicking the widget that opens it.
        #===========================================================================
        widget = model.widget_d['pushButton_mod_config']['widget']
        click(widget)
        if not interactive: 
            qtbot.waitExposed(dialog_model)  # wait until the dialog is visible
            
            
        #===========================================================================
        # post launch setup-----
        #===========================================================================
        model_lib = _get_model_lib(tutorial_name, consequence_category, modelid)
        #=======================================================================
        # #finv
        #=======================================================================
        finv_vlay = finv_loaded_d[consequence_category][modelid]
        dialog_model.comboBox_finv_vlay.setLayer(finv_vlay)
        
        #=======================================================================
        # #widget data
        #=======================================================================
        widget_modelConfig_data_d =  model_lib['widget']
        
        for k,v in widget_modelConfig_data_d.items():
            widget = getattr(dialog_model, k)
            try:
                set_widget_value(widget, v)
            except Exception as e:
                raise IOError(f'failed to set widget \'{k}\' to value \'{v}\' w/\n    {e}')
        print(f'set {len(widget_modelConfig_data_d)} widget values for model {modelid} in {consequence_category}')
     
        #=======================================================================
        # #vfunc
        #=======================================================================
        vfunc_fp = _get_model_fp(tutorial_name, consequence_category, modelid, 'vfunc')
        
        if vfunc_fp is not None:
            vfunc_fp = shutil.copyfile(vfunc_fp, os.path.join(tmpdir, os.path.basename(vfunc_fp)))
                    
            #patch the file dialog
            """over-writes the monkeypatch from teh main dialog test?"""
            monkeypatch.setattr(QFileDialog,"getOpenFileName",lambda *args, **kwargs: (vfunc_fp, ''))
            
            click(dialog_model.pushButton_V_vfunc_load) #Model_config_dialog._vfunc_load_from_file()
            
            print(f'loaded vfunc from \n    {vfunc_fp}')
        else:
            print(f'no vfunc for model {modelid} in {consequence_category}, skipping')

            
        #=======================================================================
        # functionGroups
        #=======================================================================
 
        widget_FunctionGroup_t = model_lib.get('functionGroups', None)
        if widget_FunctionGroup_t is not None:
            #print(f'{len(widget_FunctionGroup_t)} functionGroups for {modelid} in {consequence_category}')
            result_d=dict()
            cnt=0
            for i, test_d in enumerate(widget_FunctionGroup_t):
                #add the group
                fg_index, widget, widget_d = dialog_model._add_function_group()
                
                result_d[fg_index] = dict()
                
                #set the values
                for name, d_i in widget_d.items():
                    if d_i['tag'] is not None:
                        target_fieldName = test_d[d_i['tag']]
     
                        
                        #check this is in the layer
                        assert target_fieldName in finv_vlay.fields().names(), 'bad field name'
                        
                        #select it with the widget
                        d_i['widget'].setField(target_fieldName)
                        cnt+=1
                        
                        result_d[fg_index][d_i['tag']] = target_fieldName
                        
            print(f'set {cnt} function group fields')
        
        
        else:
            print(f'no functionGroups for model {modelid} in {consequence_category}, skipping')
            
        print(f'\n\nfinished configuring {tutorial_name}.{consequence_category}.{modelid} in \n{"="*80}')
        #=======================================================================
        # SAVE-------
        #=======================================================================
        click(dialog_model.pushButton_save) #Model_config_dialog._save()
        
        #close this dialog
        click(dialog_model.pushButton_close) #Model_config_dialog.close()
        
        #=======================================================================
        # wrap
        #=======================================================================
        print(f'finished configuring {tutorial_name}.{consequence_category}.{modelid} in \n{"="*80}')
        
    #===========================================================================
    # check
    #===========================================================================
    print(f'\n\nfinished configuring all models in suite \'{tutorial_name}\'\n{"="*80}')
    
    #table names
    """
    pprint.pprint(dialog_main.projDB_get_table_names_all())
    """
    
    #against model index
    model_dx = dialog_main.projDB_get_tables(['03_model_suite_index'])[0]
    
    assert model_dx['result_ead'].isna().all(), f'expected no results yete'
    
    for (consequence_category, modelid) in model_keys:
        s = model_dx.loc[(consequence_category, modelid), :]
        
        assert s.loc[['asset_label', 'table_parameters', 'table_finv', 'table_expos']].notna().all()
    
        assert s.loc[['table_impacts', 'table_impacts_prob']].isna().all()
        
    #===========================================================================
    # write
    #===========================================================================
    write_projDB(dialog_main, test_name)
    
    """
    view(model_dx)
    """
 
#add this to the list of saved tests
from tests.test_02_dialog_model import _10_save_args 
_01_save_args = copy.deepcopy(_10_save_args)

_01_save_args[1].append(
    ('cf1_tutorial_02e', oj('test_01_configSave_cf1_tu_850cd3', 'projDB.canflood2'))
    )






