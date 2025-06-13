'''
Created on Mar 5, 2025

@author: cef
'''


#===============================================================================
# IMPORTS----------
#===============================================================================
import pytest, time, sys, inspect, os, shutil, hashlib, copy
from contextlib import contextmanager
from pytest_qgis.utils import clean_qgis_layer
import pandas as pd
from pandas.testing import assert_frame_equal

from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt, QApplication #needed for itneractive
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem,
    QComboBox,
    )
from PyQt5.QtCore import QTimer


from qgis.PyQt import QtWidgets


import tests.conftest as conftest
from tests.conftest import (
    conftest_logger,
    result_write_filename_prep, click
    )



from canflood2.assertions import assert_projDB_fp, assert_hazDB_fp, assert_series_match

from canflood2.dialog_main import Main_dialog
from canflood2.parameters import fileDialog_filter_str, eventMeta_control_d, consequence_category_d


from canflood2.hp.basic import view_web_df as view
from canflood2.hp.qt import set_widget_value

#===============================================================================
# DATA--------
#===============================================================================
test_data_dir = os.path.join(conftest.test_data_dir, 'dialog_main')
os.makedirs(test_data_dir, exist_ok=True)

from canflood2.tutorials.tutorial_data_builder import tutorial_lib

tut_names = list(tutorial_lib.keys())

#===============================================================================
# HELPERS=========---------
#===============================================================================
overwrite_testdata=False #udpate test pickles
def write_projDB(dialog_main, test_name):
 
    projDB_fp = dialog_main.get_projDB_fp()
    ofp = oj_out(test_name, projDB_fp)
 
    if overwrite_testdata:
        os.makedirs(os.path.dirname(ofp), exist_ok=True)
        
        #copy over the .sqlite file
        shutil.copyfile(projDB_fp, ofp)  
        conftest_logger.info(f'wrote result to \n    {ofp}')
        


def oj(*args):
    return os.path.join(test_data_dir, *args)

def oj_out(test_name, result):
    return oj(result_write_filename_prep(test_name), os.path.basename(result))


 


def dialog_create_new_projDB(monkeypatch, dialog, tmpdir):
    """wrapper to patch and click Create New ProjDB"""
    print('setting up Create New ProjDB')
    dummy_file = tmpdir.join(f'projDB.canflood2').strpath
    monkeypatch.setattr(
        QFileDialog, 
        "getSaveFileName", 
        lambda*args, **kwargs:(dummy_file, "sqlite database files (*.canflood2)"))
    # Simulate clicking the new project database button.
    click(dialog.pushButton_PS_projDB_new)
    return dummy_file
 
def dialog_launch_modelConfig(dialog, consequence_category, modelid):
    #===========================================================================
    # #create the model suite templates
    #===========================================================================
    """these should be loaded with the projDB
    
    QTest.mouseClick(dialog.pushButton_MS_createTemplates, Qt.LeftButton) #Main_dialog._create_model_templates()
    
    """
    #check they have been added to the dialog index
    assert set(dialog.model_index_d.keys()) == set(consequence_category_d.keys())
    #===========================================================================
    # launch config window on first model
    #===========================================================================
    #schedule dialog to close
    model_config_dialog = dialog.Model_config_dialog
    QTimer.singleShot(200, lambda:click(model_config_dialog.pushButton_ok))
    
    #retrieve the widget
    model = dialog.model_index_d[consequence_category][modelid]
    widget = model.widget_d['pushButton_mod_config']['widget']
    click(widget)
    
    return model
 
#===============================================================================
# FIXTURES: MAIN DIALOG------
#===============================================================================

#===============================================================================
# dialog setup
#===============================================================================
"""need to handle:
    different scenarios for user inputs (e.g., paramerterize populated fields on UI)
    partial (for individual run) and complete (for full run) parameterization
    
use fixtures to parameterize in blocks
    load the dialog, assign some variables
    only need to call the fixture (and the dialog) in the test (don't need to use)
"""
 
    
@pytest.fixture(scope='function') 
def dialog_main(qgis_iface, qgis_new_project, logger, tmpdir,monkeypatch,
        
           ):
    """dialog_main fixture.
    
    setup should be handled by calling fixtures from within your test        
    """
    
    #===========================================================================
    # init  
    #===========================================================================
    dialog_main =  Main_dialog(parent=None, 
                          iface=qgis_iface,
                          debug_logger=logger, #connect python logger for rtests 
                          )
 
 
    print(f'\n\n{"=" * 80}\nDIALOG fixture setup complete\n{"=" * 80}\n\n')
    return dialog_main

@pytest.fixture
def dialog_loaded(dialog_main,  
                aoi_vlay,dem_rlay, #instancing loads to project. dialog_projDB_load loads to UI
                haz_rlay_d, #load to project. _load_projDB_to_ui checks for name match
                projDB_fp, 
                monkeypatch,tmpdir,
                ):
    """setup the project and load the dialog from the projDB
    
    TODO: rename this as a projDB fixture?
    
    """
    
    #===========================================================================
    # load maplayers onto project
    #===========================================================================
    """done by fixtures"""
    
    dialog_main.lineEdit_R_outdir.setText(str(tmpdir))
    
    #===========================================================================
    # load ui from projDB
    #===========================================================================
    #patch and click load projDB
    assert os.path.exists(projDB_fp), f'projDB_fp does not exist: {projDB_fp}'
    projDB_fp = shutil.copyfile(projDB_fp, os.path.join(tmpdir, os.path.basename(projDB_fp))) #assert_projDB_fp(projDB_fp)
    #patch the load button
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda*args, **kwargs:(projDB_fp, ''))
    #load the project database
    click(dialog_main.pushButton_PS_projDB_load) #Main_dialog._load_projDB_to_ui()
    
    return dialog_main
    
""" 
dialog_main.show()
QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
sys.exit(QApp.exec_()) #wrap
"""
 
 
@pytest.fixture
def widget_data_d(dialog_main, widget_Main_dialog_data_d):
    """calling this fixture attaches it to the dialog"""
 
    print('setting widget data')
    for widget_name, v in widget_Main_dialog_data_d.items():
        widget = getattr(dialog_main, widget_name, None)
        if widget is not None:
            set_widget_value(widget, v)
            
    return  copy.deepcopy(widget_Main_dialog_data_d)


@pytest.fixture
def aoi_vlay_set(aoi_vlay, dialog_main):
    """set the aoi_vlay on teh combobox"""
    dialog_main.comboBox_aoi.setLayer(aoi_vlay)
    return True


@pytest.fixture
def dem_rlay_set(dem_rlay, dialog_main):
    """set the dem_rlay on teh combobox"""
    dialog_main.comboBox_dem.setLayer(dem_rlay)
    return True

    
@pytest.fixture
def event_meta_set(eventMeta_df, dialog_main, haz_rlay_d, probability_type,
                   qtbot):
    """set the eventMeta_df onto the dialog
    
    this shortcuts selecting, loading, and entering in the values
        see test_dial_main_02_load_to_eventMeta_widget 
    """
    print(f'loading {eventMeta_df.shape} eventMeta_df')
    """this will overwrite click(dialog.pushButton_HZ_hrlay_load)"""
    assert not haz_rlay_d is None, 'must provide haz_rlay_d to load eval_d'
    #check the keys match
    assert set(eventMeta_df.iloc[:,0]) == set(haz_rlay_d.keys()), 'eval_d keys do not match haz_rlay_d keys'
 

    dialog_main.tableWidget_HZ_eventMeta.set_df_to_QTableWidget_spinbox(eventMeta_df)
    
    #===========================================================================
    # #set the probability type
    #===========================================================================
    if probability_type == '1':
        #click(dialog_main.radioButton_ELari)
        dialog_main.radioButton_ELari.setChecked(True)
        assert dialog_main.radioButton_ELari.isChecked(), 'ARI not checked' 
    elif probability_type == '0':
 
        dialog_main.radioButton_ELaep.setChecked(True)        
        assert dialog_main.radioButton_ELaep.isChecked(), 'AEP not checked'
        assert not dialog_main.radioButton_ELari.isChecked(), 'ARI checked'
        
    else:
        raise ValueError(f'unknown probability type: {probability_type}')

 
    return True
 
 
 
#===============================================================================
# TESTS------
#===============================================================================
""" 
dialog.show()
QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
sys.exit(QApp.exec_()) #wrap
"""


def test_dial_main_00_init(dialog_main,): 
    assert hasattr(dialog_main, 'logger')
    
    
def test_dial_main_00_launch_QGIS_LOG_FILE(dialog_main):
    """test that the QGIS log file is created"""
    
    click(dialog_main.pushButton_debugLog)

 
def test_dial_main_01_create_new_projDB(monkeypatch, dialog_main, tmpdir, test_name):
    """create new projDB
    
    note this is redundant with test_dial_main_02_save_ui_to_project_database
    """
    dialog_create_new_projDB(monkeypatch, dialog_main, tmpdir)
 
    
    #===========================================================================
    # post
    #===========================================================================
    result = dialog_main.get_projDB_fp()
    assert_projDB_fp(result, check_consistency=True)
    
    #write_projDB(dialog_main, test_name)
     
     
    
 

@pytest.mark.parametrize('tutorial_name', tut_names)
def test_dial_main_02_load_to_eventMeta_widget(dialog_main, tutorial_name, test_name,
                                               haz_rlay_d, #loads to project
                                               #eventMeta_df,
                                               ):
    """on the hazard tab, loading the rasters, setting the probabilities, and loading back the table"""
 
    
    #===========================================================================
    # select ahd load the hazard layers onto the event meta table
    #===========================================================================
    print(f'populating on {len(haz_rlay_d)} hazard layers')
    #select all of these layers in listView_HZ_hrlay
    dialog_main.listView_HZ_hrlay.populate_layers()
    dialog_main.listView_HZ_hrlay.check_byName([layer.name() for layer in haz_rlay_d.values()])
    
    #load into the event metadata
    click(dialog_main.pushButton_HZ_hrlay_load) #load_selected_rasters_to_eventMeta_widget()
    
    
    #===========================================================================
    # add some numbers
    #===========================================================================
    event_df = dialog_main.tableWidget_HZ_eventMeta.get_df_from_QTableWidget()
 
    #add some dummy probabilities
    event_df.loc[:,'Probability'] = pd.Series([50, 100, 200, 1000], dtype=float)
    event_df.loc[:,event_df.columns[2]] = test_name
    
    #remap column names to widget expectation
    event_df = event_df.rename(
                columns={v['label']:k for k,v in eventMeta_control_d.items()}
                ).astype({'prob':float})
    #set back onto the widget
    dialog_main.tableWidget_HZ_eventMeta.set_df_to_QTableWidget_spinbox(event_df.copy())
    
    print(f'\n\nfinished setting {event_df.shape} event data\n{"=" * 80}\n\n ')
    #===========================================================================
    # check
    #===========================================================================
    """here we use the builtin loaders to check them and the setting functions"""
    test_event_df = dialog_main.get_haz_events_df()
    
 
    assert_frame_equal(event_df, test_event_df)
    
    #===========================================================================
    # clear
    #===========================================================================
    click(dialog_main.pushButton_HZ_populate_clear)  
 



 
#===============================================================================
# @pytest.mark.parametrize('tutorial_name', [
#     #'cf1_tutorial_01',
#     #'cf1_tutorial_02b', #AEP instead of ARI
#     'cf1_tutorial_02c', #datum
#     ])
#===============================================================================

@pytest.mark.parametrize("tutorial_name", tut_names)
def test_dial_main_02_save_ui_to_project_database(dialog_main,tmpdir, test_name, monkeypatch, 
                          widget_data_d, #widget values set during instance
                          aoi_vlay_set, dem_rlay_set, #combobox set during instance
                          event_meta_set, #eventMeta_df set during instance, loads haz_rlay_d
                          
                          #for testing
                          aoi_vlay, dem_rlay, eventMeta_df,
                                                  ):
    """
    load tutorial and other data onto dialog
    Create New ProjDB
    test saving the projDB
    
    
 
    """
    #===========================================================================
    # populate UI
    #===========================================================================
    """instanced by fixture
    
    widget_data_d
    aoi_vlay
    dem_vlay
    eventMeta_df
    
    """
 
    #===========================================================================
    # #create a new projDB
    #===========================================================================
    """ 
    dialog_main.show()
    QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
    sys.exit(QApp.exec_()) #wrap
    """


    dialog_create_new_projDB(monkeypatch, dialog_main, tmpdir)
 
 
 
    #===========================================================================
    # execute
    #===========================================================================
 
    # Simulate clicking the save button.
    click(dialog_main.pushButton_save) #Main_dialog._save_ui_to_projDB()
 
    
    
    #===========================================================================
    # test
    #===========================================================================
    # Verify that the project database file path is saved.
    result = dialog_main.get_projDB_fp()
    assert_projDB_fp(result, check_consistency=True)
    
    #load parmeters table
    df = dialog_main.projDB_get_tables(['02_project_parameters'])[0]
    
    test_d = df.loc[:, ['widgetName', 'value']].set_index('widgetName').to_dict()['value']
    
    #check against test data
    for widgetName,v in widget_data_d.items():
        assert test_d[widgetName] == v, f'failed to set {widgetName}'
        
    
    #check that the aoi_vlay is on comboBox_aoi
    assert dialog_main.comboBox_aoi.currentLayer() == aoi_vlay
     
    #check hte dem_rlay is on comboBox_dem
    assert dialog_main.comboBox_dem.currentLayer() == dem_rlay
        
    
    assert_frame_equal(dialog_main.get_haz_events_df(), eventMeta_df)
    #===========================================================================
    # write
    #===========================================================================
    write_projDB(dialog_main, test_name)
 
 





@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_01', oj('02_save_ui_to_project_dat_62b9e2', 'projDB.canflood2')),
    #('cf1_tutorial_02', oj('02_save_ui_to_project_dat_85ad36', 'projDB.canflood2')),
    ('cf1_tutorial_02b', oj('02_save_ui_to_project_dat_b33feb', 'projDB.canflood2'))
])
def test_dial_main_03_load_projDB(dialog_loaded,
                                  
                                  #for testing
                                  aoi_vlay, dem_rlay, eventMeta_df,                                  
                                             ):
    """Test that clicking the 'load project database' button sets the lineEdit with the dummy file path.
    
    no model suite yet?
 
    """
 
    #===========================================================================
    # execute
    #===========================================================================
    """see dialog_loaded fixture"""

    
    #===========================================================================
    # check
    #===========================================================================
    print(f'\n\n{"=" * 80}\nchecking loaded data\n{"=" * 80}\n\n')
    result = dialog_loaded.get_projDB_fp()
    assert_projDB_fp(result, check_consistency=True)
    
    #check that the aoi_vlay is on comboBox_aoi
    assert dialog_loaded.comboBox_aoi.currentLayer() == aoi_vlay
     
    #check hte dem_rlay is on comboBox_dem
    assert dialog_loaded.comboBox_dem.currentLayer() == dem_rlay
    
    #check the eventMeta_df
    check_df = dialog_loaded.get_haz_events_df()
    assert_frame_equal(check_df.drop('layer_id', axis=1), eventMeta_df.drop('layer_id', axis=1))
    
    
 

    
 

 



@pytest.mark.dev
@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_01', oj('02_save_ui_to_project_dat_62b9e2', 'projDB.canflood2')),
   ('cf1_tutorial_02', oj('02_save_ui_to_project_dat_85ad36', 'projDB.canflood2')),
   ('cf1_tutorial_02b', oj('02_save_ui_to_project_dat_b33feb', 'projDB.canflood2')), 
   ('cf1_tutorial_02c', oj('02_save_ui_to_project_dat_7b3a19', 'projDB.canflood2')),
])
def test_dial_main_04_MS_createTemplates(dialog_loaded, test_name,
                                         tutorial_name,
                                         ):
    """test creation and clearing of the model suite"""
    
 
    #===========================================================================
    # load database
    #===========================================================================
    """
    dialog_loaded:
        loads data from test_dial_main_02_save_ui_to_project_database:
            parameters (widget data)
            aoi_vlay
            dem_rlay
            haz_rlay_d
            eventMeta_df
    """

    
    #===========================================================================
    # #create the model suite templates
    #===========================================================================
    dialog=dialog_loaded
    click(dialog.pushButton_MS_createTemplates) #Main_dialog._connect_slots_modelSuite()
 
    
    #check they have been added to the dialog index
    assert set(dialog.model_index_d.keys()) == set(consequence_category_d.keys())
    
    #===========================================================================
    # clear the model suite
    #===========================================================================

    click(dialog.pushButton_MS_clear)  #Main_dialog._clear_model_suite()
    
    #check they have been removed
    assert len(dialog.model_index_d) == 0
    
    #===========================================================================
    # #create the model suite templates
    #===========================================================================
    
    """creating a second time as an additional test.. also gives us the result data"""
    
    click(dialog.pushButton_MS_createTemplates)  #Main_dialog._create_model_templates()
    
    #===========================================================================
    # check
    #===========================================================================
    #check they have been added to the dialog index
    assert set(dialog.model_index_d.keys()) == set(consequence_category_d.keys())
    
    
    #===========================================================================
    # post
    #===========================================================================3
    write_projDB(dialog, test_name)
    

 

_04_MS_args = ("tutorial_name, projDB_fp", [
    #('cf1_tutorial_01', oj('04_MS_createTemplates_cf1_4b9cc3', 'projDB.canflood2')), #L1 not implemented
    ('cf1_tutorial_02', oj('04_MS_createTemplates_cf1_f72317', 'projDB.canflood2')),
    #('cf1_tutorial_02b', oj('04_MS_createTemplates_cf1_ea97b3', 'projDB.canflood2')),
    #('cf1_tutorial_02c', oj('04_MS_createTemplates_cf1_1ae7e8', 'projDB.canflood2')),
])
    

#===============================================================================
# TESTS: POST MODEL CONFIG----------
#===============================================================================
"""
see test_04_dialog_main_post.py
"""
    
    
    
    
    
    
    
    
    
    