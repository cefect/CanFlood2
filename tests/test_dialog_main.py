'''
Created on Mar 5, 2025

@author: cef
'''


#===============================================================================
# IMPORTS----------
#===============================================================================
import pytest, time, sys, inspect, os, shutil, hashlib
from contextlib import contextmanager
from pytest_qgis.utils import clean_qgis_layer
import pandas as pd

from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt, QApplication
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
test_data_dir = os.path.join(conftest.test_data_dir, 'test_dialog_main')
os.makedirs(test_data_dir, exist_ok=True)

 

#===============================================================================
# HELPERS---------
#===============================================================================
overwrite_testdata=False
def write_sqlite(result, ofp, write=overwrite_testdata):
    if write:
        os.makedirs(os.path.dirname(ofp), exist_ok=True)
        
        #copy over the .sqlite file
        shutil.copyfile(result, ofp) 
 
        conftest_logger.info(f'wrote result to \n    {ofp}')
        

        
 

def oj(*args):
    return os.path.join(test_data_dir, *args)

def oj_out(test_name, result):
    return oj(result_write_filename_prep(test_name), os.path.basename(result))


 


def write_projDB(dialog, test_name):
 
#projDB
    projDB_fp = dialog.get_projDB_fp()
    write_sqlite(projDB_fp, oj_out(test_name, projDB_fp))


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
def dialog(qgis_iface, qgis_new_project, logger, tmpdir,monkeypatch,
           projDB_fp,
           widget_data_d,
           aoi_vlay, dem_rlay, haz_rlay_d, eventMeta_df, #tutorial parameters           
           ):
    """dialog fixture.
    
    custom parameters should all be None if not specifeid
    tutorial parameters are ALL returned if tutorial_name is passed
        
    """
    
    #===========================================================================
    # init  
    #===========================================================================
    dialog =  Main_dialog(parent=None, 
                          iface=qgis_iface,
                          debug_logger=logger, #connect python logger for rtests 
                          )
 
 
    

        
        
    #===========================================================================
    # # Add some default text to specific line edits.
    #===========================================================================
    print(f"post DIALOG fixture setup\n{'=' * 80}\n\n")
    if widget_data_d is not None:
        print('setting widget data')
        for widget_name, v in widget_data_d.items():
            widget = getattr(dialog, widget_name, None)
            if widget is not None:
                set_widget_value(widget, v)
                
    
    #===========================================================================
    # layers
    #===========================================================================
    if aoi_vlay is not None:
        dialog.comboBox_aoi.setLayer(aoi_vlay)
        
    if dem_rlay is not None:
        dialog.comboBox_dem.setLayer(dem_rlay)
        
        
    if haz_rlay_d is not None:
        print(f'loading {len(haz_rlay_d)} hazard layers')
        #select all of these layers in listView_HZ_hrlay
        dialog.listView_HZ_hrlay.populate_layers()
        dialog.listView_HZ_hrlay.check_byName([layer.name() for layer in haz_rlay_d.values()])
        
        #load into the event metadata
        click(dialog.pushButton_HZ_hrlay_load) #load_selected_rasters_to_eventMeta_widget()
        
    #===========================================================================
    # event values in tableWidget_HZ_eventMeta
    #===========================================================================
    if eventMeta_df is not None:
        print(f'loading {eventMeta_df.shape} eventMeta_df')
        """this will overwrite click(dialog.pushButton_HZ_hrlay_load)"""
        assert not haz_rlay_d is None, 'must provide haz_rlay_d to load eval_d'
        #check the keys match
        assert set(eventMeta_df.iloc[:,0]) == set(haz_rlay_d.keys()), 'eval_d keys do not match haz_rlay_d keys'
 

        dialog.tableWidget_HZ_eventMeta.set_df_to_QTableWidget_spinbox(eventMeta_df)  
        
        
    #===========================================================================
    # setup databases
    #===========================================================================
    """this goes last as the Load function expects the layers to be loaded"""
    if projDB_fp is not None:
        print(f'copying projDB_fp \'{projDB_fp}\' to tmpdir')
        projDB_fp = shutil.copyfile(projDB_fp, os.path.join(tmpdir, os.path.basename(projDB_fp)))
        #assert_projDB_fp(projDB_fp)
        
        #patch the load button
        monkeypatch.setattr(QFileDialog,"getOpenFileName",lambda *args, **kwargs: (projDB_fp, ''))
        
        #load the project database
        click(dialog.pushButton_PS_projDB_load)
        
 
    print(f'\n\n{"=" * 80}\nDIALOG fixture setup complete\n{"=" * 80}\n\n')
    return dialog




# Default fixtures that return None unless overridden.
 


@pytest.fixture
def widget_data_d(request):
    return getattr(request, "param", None)


    


    
 
 
 
#===============================================================================
# TESTS------
#===============================================================================
""" 
dialog.show()
QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
sys.exit(QApp.exec_()) #wrap
"""


def test_dial_main_00_init(dialog,): 
    assert hasattr(dialog, 'logger')
    
    



 
def test_dial_main_01_create_new_projDB(monkeypatch, dialog, tmpdir, test_name):
    """create new projDB
    
    note this is redundant with test_dial_main_02_save_ui_to_project_database
    """
    dialog_create_new_projDB(monkeypatch, dialog, tmpdir)
 
    
    #===========================================================================
    # post
    #===========================================================================
    result = dialog.get_projDB_fp()
    assert_projDB_fp(result, check_consistency=True)
    
    write_sqlite(result, oj_out(test_name, result))
     
 
@pytest.mark.dev
#@pytest.mark.parametrize("projDB_fp", [oj('01_create_new_projDB', 'projDB.canflood2')])
@pytest.mark.parametrize('tutorial_name', ['cf1_tutorial_02']) 
@pytest.mark.parametrize("widget_data_d", [
    {
        'studyAreaLineEdit': 'test_study_area',
        'userLineEdit': 'test_user',
        'scenarioNameLineEdit': 'some scenario', 
        'climateStateLineEdit': 'some climate', 
        'hazardTypeLineEdit': 'some hazard',
          }])
def test_dial_main_02_save_ui_to_project_database(dialog,tmpdir, test_name, monkeypatch, 
                                                  widget_data_d):
    """
    load tutorial and other data onto dialog
    Create New ProjDB
    test saving the projDB
    
    
 
    """
    #===========================================================================
    # prep
    #===========================================================================
    """by passing """
 
 
    #===========================================================================
    # #create a new projDB
    #===========================================================================
    dialog_create_new_projDB(monkeypatch, dialog, tmpdir)
 
 
 
    #===========================================================================
    # execute
    #===========================================================================
 
    # Simulate clicking the save button.
    click(dialog.pushButton_save) #Main_dialog._save_ui_to_projDB()
 
    
    
    #===========================================================================
    # test
    #===========================================================================
    # Verify that the project database file path is saved.
    result = dialog.get_projDB_fp()
    assert_projDB_fp(result, check_consistency=True)
    
    #load parmeters table
    df = dialog.projDB_get_tables(['02_project_parameters'])[0]
    
    test_d = df.loc[:, ['widgetName', 'value']].set_index('widgetName').to_dict()['value']
    
    #check against test data
    for widgetName,v in widget_data_d.items():
        assert test_d[widgetName] == v, f'failed to set {widgetName}'
        
        
    #===========================================================================
    # write
    #===========================================================================
    write_projDB(dialog, test_name)
 
 


@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02', oj('02_save_ui_to_project_dat_151acb', 'projDB.canflood2'))
])
def test_dial_main_03_load_projDB(dialog,
                                             ):
    """Test that clicking the 'load project database' button sets the lineEdit with the dummy file path.
 
    """
 
    #===========================================================================
    # execute
    #===========================================================================
    """by passing the projDB_fp, the load button is clicked in the dialog fixture"""
    
    #===========================================================================
    # check
    #===========================================================================
    result = dialog.get_projDB_fp()
    assert_projDB_fp(result, check_consistency=True)
 

    
 

 




@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02', oj('02_save_ui_to_project_dat_151acb', 'projDB.canflood2'))
])
def test_dial_main_04_MS_createTemplates(dialog, test_name):
    """test creation and clearing of the model suite"""
    
 
    
    #===========================================================================
    # #create the model suite templates
    #===========================================================================
    click(dialog.pushButton_MS_createTemplates)
 
    
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
    
    #check they have been added to the dialog index
    assert set(dialog.model_index_d.keys()) == set(consequence_category_d.keys())
    
    
    #===========================================================================
    # post
    #===========================================================================3
    write_projDB(dialog, test_name)
    
    
    
    
 
 




    
    
    
    
    
    
    
    
    
    