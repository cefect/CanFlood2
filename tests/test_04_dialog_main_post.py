'''
Created on Mar 21, 2025

@author: cef

main dialog, post model config/run tests
    for clenear test sequence and depenency management, made this separate
'''

#===============================================================================
# IMPORTS----------
#===============================================================================
import pytest, time, sys, inspect, os, shutil, hashlib, copy

from pandas.testing import assert_frame_equal
from PyQt5.Qt import Qt, QApplication


from tests.conftest import (
    conftest_logger,
    result_write_filename_prep, click
    )

from tests.test_01_dialog_main import dialog_main, dialog_loaded #get the main dialog tests
from tests.test_02_dialog_model import oj as oj_model #get the core


from canflood2.assertions import assert_projDB_fp, assert_hazDB_fp, assert_series_match
from canflood2.parameters import fileDialog_filter_str, eventMeta_control_d, consequence_category_d

from canflood2.tutorials.tutorial_data_builder import tutorial_fancy_names_d

from canflood2.hp.qt import set_widget_value



#===============================================================================
# TESTS=======--------
#===============================================================================
 
@pytest.mark.parametrize("tutorial_name", ['cf1_tutorial_02', 
       pytest.param('cf1_tutorial_01', 
                    marks=pytest.mark.xfail(raises=IOError, reason='this tutorial is not setup yet'),
                    )
                                           ])
def test_dial_main_dev_01_W_load_tutorial_data(dialog_main, tutorial_name, test_name,
 
                                           ):
    """test loading tutorial data"""
    dialog = dialog_main
    #set the combo box
    set_widget_value(dialog.comboBox_tut_names, tutorial_fancy_names_d[tutorial_name])
 
    
    click(dialog.pushButton_tut_load) #Main_dialog._load_tutorial_to_ui()
    
    #===========================================================================
    # check
    #===========================================================================
    print(f'\n\n{"=" * 80}\nchecking loaded data\n{"=" * 80}\n\n')
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
    


@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02',oj_model('test_05_run_c1-0-cf1_tuto_3fc21f', 'projDB.canflood2'))
     ])
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


@pytest.mark.dev
@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02',oj_model('test_05_run_c1-0-cf1_tuto_3fc21f', 'projDB.canflood2'))
     ])
def test_dial_main_03_report_risk_curve(dialog_loaded, test_name,
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
    click(dialog.pushButton_R_riskCurve) #Main_dialog._run_selected_models()
    
    
 
 
""" 


dialog.show()
QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
sys.exit(QApp.exec_()) #wrap


"""