'''
Created on Mar 21, 2025

@author: cef

testing tutorial data loading
    made this a separate module as these tests depend on all the tests
    these dependencies (and workflow) are different from rest of the main dialog
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

from tests.test_01_dialog_main import dialog_main #get the main dialog tests


from canflood2.assertions import assert_projDB_fp, assert_hazDB_fp, assert_series_match
from canflood2.parameters import fileDialog_filter_str, eventMeta_control_d, consequence_category_d

from canflood2.tutorials.tutorial_data_builder import tutorial_fancy_names_d

from canflood2.hp.qt import set_widget_value



#===============================================================================
# TESTS=======--------
#===============================================================================
@pytest.mark.dev
@pytest.mark.parametrize("tutorial_name", ['cf1_tutorial_02'])
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

 
""" 
dialog.show()
QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
sys.exit(QApp.exec_()) #wrap
"""