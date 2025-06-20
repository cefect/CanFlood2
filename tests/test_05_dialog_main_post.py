'''
Created on Mar 21, 2025

@author: cef

main dialog, post model config/run tests
    for clenear test sequence and depenency management, made this separate
'''

#===============================================================================
# IMPORTS----------
#===============================================================================
import pytest, time, sys, inspect, os, shutil, hashlib, copy, pprint

from pandas.testing import assert_frame_equal
from PyQt5.Qt import Qt, QApplication

from qgis.core import QgsProject


import tests.conftest as conftest
from tests.conftest import (
    conftest_logger,
    result_write_filename_prep, click
    )

from tests.test_01_dialog_main import dialog_main, dialog_loaded #get the main dialog tests
from tests.test_02_dialog_model import oj as oj_model #get the core
from tests.test_02_dialog_model import _20_run_args as DM_run_args 
from tests.test_04_dialog_model_multi import _01_save_args as DM_save_args


from canflood2.assertions import assert_projDB_fp, assert_hazDB_fp, assert_series_match
from canflood2.parameters import fileDialog_filter_str, eventMeta_control_d, consequence_category_d

from canflood2.tutorials.tutorial_data_builder import tutorial_fancy_names_d, tutorial_lib

from canflood2.hp.qt import set_widget_value


#===============================================================================
# params-----
#===============================================================================
interactive = False #interactive dialogs for tests
overwrite_testdata_plugin=True 
overwrite_testdata=True #write test result projDB


#===============================================================================
# DATA--------
#===============================================================================
test_data_dir = os.path.join(conftest.test_data_dir, 'dialog_main_post')
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
# TESTS=======--------
#===============================================================================

@pytest.mark.parametrize("tutorial_name", [
    #'cf1_tutorial_01',
    'cf1_tutorial_02', 
    'cf1_tutorial_02b',
    'cf1_tutorial_02c',
 
                                           ])
def test_dial_main_dev_01_W_load_tutorial_data(dialog_main, tutorial_name, test_name,
                                               
                                               #load layers to project
                                               #aoi_vlay,dem_rlay,haz_rlay_d, #load to project. _load_projDB_to_ui checks for name match
 
                                           ):
    """test loading tutorial data
    
    NOTE: for major changes, need to rebuild the tutorials/data/projDBs
        with test_02_dialog_model:
            overwrite_testdata_plugin=True
            test_dial_model_20_run()
            
         """
    dialog = dialog_main
    #===========================================================================
    # load layers to project
    #===========================================================================
    """done by pushButton_tut_load"""
    
    
    
    #===========================================================================
    # setup the dialog
    #===========================================================================
    #set the combo box
    set_widget_value(dialog.comboBox_tut_names, 
                     #tutorial_fancy_names_d[tutorial_name],
                     tutorial_lib[tutorial_name]['fancy_name'],)
 
    
    #===========================================================================
    # execute
    #===========================================================================
    """
    all_layers_d = QgsProject.instance().mapLayers()
 
    
    #print all names
    for layer_id, layer in all_layers_d.items():
        print(f"{layer.name()}: ({type(layer)})")
    
    """
    click(dialog.pushButton_tut_load) #Main_dialog._load_tutorial_to_ui()
    
    #===========================================================================
    # check
    #===========================================================================
    print(f'\n\n{"=" * 80}\nchecking loaded data\n{"=" * 80}\n\n')
    
    _get_MD_lib = lambda tut_name: copy.deepcopy(tutorial_lib[tut_name]['Main_dialog'])
    tut_data = _get_MD_lib(tutorial_name)['data']
    """
    pprint.pprint(tut_data)
    """
    
    #projfDB
    #not all tutorials have a projDB
    if 'projDB' in tut_data.keys():
        result = dialog.get_projDB_fp()
        if result is None:
            raise IOError(f'failed to load any projDB_fp')
        assert_projDB_fp(result, check_consistency=True)
    
    #check that the aoi_vlay is on comboBox_aoi
    assert not dialog.comboBox_aoi.currentLayer() is None, 'failed to set aoi_vlay' 
     
    #check hte dem_rlay is on comboBox_dem
    assert not dialog.comboBox_dem.currentLayer() is None, 'failed to set dem_rlay'
    
    #check the eventMeta_df
    check_df = dialog.get_haz_events_df()
    assert len(check_df) > 0, 'failed to load eventMeta_df'    
    
    #check they have been added to the dialog index
    assert set(dialog.model_index_d.keys()) == set(consequence_category_d.keys())
    
    #===========================================================================
    # try clicking again
    #===========================================================================
    """this always fails
    click(dialog.pushButton_tut_load)"""
    


#===============================================================================
# @pytest.mark.parametrize("tutorial_name, projDB_fp", [
#     ('cf1_tutorial_02',oj_model('test_05_run_c1-0-cf1_tuto_cdc677', 'projDB.canflood2'))
#      ])
#===============================================================================
@pytest.mark.parametrize(*DM_run_args)
def test_dial_main_02_save_ui_to_project_database(dialog_loaded, tutorial_name, test_name,
                                                  ):
    """load the built main dialog, save it to a new project database
    
    see test_01_dialog_main.test_dial_main_02_save_ui_to_project_database() for pre-run test
    """
    dialog = dialog_loaded
    #===========================================================================
    # setup
    #===========================================================================
    """
    dialog_loaded: configures
        - projDB_fp set and loaded (should load the model suite)
        - aoi, dem, haz layers
    """
    

    
    #===========================================================================
    # execute
    #===========================================================================
 
    # Simulate clicking the save button.
    click(dialog.pushButton_save) #Main_dialog._save_ui_to_projDB()

 

#===============================================================================
# @pytest.mark.parametrize("tutorial_name, projDB_fp", [
#     ('cf1_tutorial_02',oj_model('test_05_run_c1-0-cf1_tuto_cdc677', 'projDB.canflood2'))
#      ])
#===============================================================================
@pytest.mark.parametrize(*DM_save_args)
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_main_03_model_run(dialog_loaded, tutorial_name, test_name,
                                consequence_category, modelid,
                                ):
    """test the run model button on the model widget (not to be confused with the model config dialog)
    """
    #===========================================================================
    # setup
    #===========================================================================
    dialog = dialog_loaded
    
    
    
    #===========================================================================
    # #get a pointer to the run button    
    #===========================================================================
    #check the model exists
    model = dialog.model_index_d[consequence_category][modelid]
    
    
    button = model.widget_suite.pushButton_mod_run
    
    #===========================================================================
    # execute
    #===========================================================================
    click(button)



@pytest.mark.dev
@pytest.mark.parametrize(*DM_save_args)
def test_dial_main_03_model_run_all(dialog_loaded, tutorial_name, test_name,
                                ):
    """test the run all button
    (not to be confused with the model config dialog)
    """
    #===========================================================================
    # setup
    #===========================================================================
    dialog = dialog_loaded
    
    
 
    #===========================================================================
    # execute
    #===========================================================================
    click(dialog.pushButton_MS_runAll)
    
    
    #===========================================================================
    # svae
    #===========================================================================
    write_projDB(dialog, test_name)
    
    



#===============================================================================
# @pytest.mark.parametrize("tutorial_name, projDB_fp", [
#     ('cf1_tutorial_02',oj_model('test_05_run_c1-0-cf1_tuto_cdc677', 'projDB.canflood2'))
#      ])
#===============================================================================
 
@pytest.mark.parametrize(*DM_run_args)
def test_dial_main_04_report_risk_curve(dialog_loaded, test_name,

                                ):
    """run the model"""
    dialog = dialog_loaded
    #===========================================================================
    # setup
    #===========================================================================
    """
    dialog_loaded: configures
        - projDB_fp set and loaded (should load the model suite)
        - aoi, dem, haz layers
    """
    
    #populate the model results selection widget
    click(dialog.pushButton_R_populate) #Main_dialog._populate_results_model_selection(
    
    #select teh first model
    dialog.listView_R_modelSelection.check_byName(['c1_0'])
    
    #===========================================================================
    # execute
    #===========================================================================
    click(dialog.pushButton_R_riskCurve) #Main_dialog._plot_risk_curve()
    
    

@pytest.mark.parametrize(*DM_run_args)
def test_dial_main_04_exportCSV(dialog_loaded, test_name,
                                ):
    """run the model"""
    dialog = dialog_loaded
    
    click(dialog.pushButton_R_exportCSV)
 
""" 


dialog.show()
QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
sys.exit(QApp.exec_()) #wrap


"""