'''
Created on Mar 5, 2025

@author: cef
'''


#===============================================================================
# IMPORTS----------
#===============================================================================
import pytest, time, sys, inspect, os, shutil
from pytest_qgis.utils import clean_qgis_layer
import pandas as pd

from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt, QApplication, QPoint
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem,
    QComboBox,
    )


from qgis.PyQt import QtWidgets


import tests.conftest as conftest
from tests.conftest import conftest_logger, assert_intersecting_values_match_verbose

from canflood2.assertions import assert_proj_db_fp, assert_haz_db_fp

from canflood2.dialog_main import Main_dialog
from canflood2.parameters import fileDialog_filter_str, eventMeta_control_d

from canflood2.hp.basic import sanitize_filename
from canflood2.hp.basic import view_web_df as view

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
        
def prep_filename(test_name, char_max=30):
    """cleaning up the pytest names to use for auto result writing"""
    
    test_name1 = sanitize_filename(test_name)
    
    test_name1 = test_name1.replace('test_dial_main_', '')
    
    return test_name1[:char_max]
        
 

def oj(*args):
    return os.path.join(test_data_dir, *args)

def oj_out(test_name, result):
    return oj(prep_filename(test_name), os.path.basename(result))


def _dialog_preloader(dialog,  
                      tmpdir=None,
                      projDB_fp=None, hazDB_fp=None,
                      aoi_vlay=None, dem_rlay=None,
                      widget_data_d = None,
                      haz_rlay_d=None,
                      eventMeta_df=None,
                      ):
    """
    Helper to preload the dialog with some data.

    All arguments other than `dialog` are optional. Data is attached only if
    the corresponding argument is provided.

 

    Returns:
        dict: A dictionary summarizing the attached data.
    """
    # Dictionary to store info about the applied settings.
    applied_data = {}

    if projDB_fp is not None:
        projDB_fp = shutil.copyfile(projDB_fp, os.path.join(tmpdir, os.path.basename(projDB_fp)))
        assert_proj_db_fp(projDB_fp)
        dialog.lineEdit_PS_projDB_fp.setText(projDB_fp)
        dialog.pushButton_save.setEnabled(True)
        applied_data['projDB_fp'] = projDB_fp
        
    if hazDB_fp is not None:
        #copy over the test data to a temporary directory
        hazDB_fp = shutil.copyfile(hazDB_fp, os.path.join(tmpdir, os.path.basename(hazDB_fp)))
        assert_haz_db_fp(hazDB_fp)
        dialog.lineEdit_HZ_hazDB_fp.setText(hazDB_fp)
        dialog.pushButton_save.setEnabled(True)
        applied_data['hazDB_fp'] = hazDB_fp

    # Add some default text to specific line edits.
    if widget_data_d is not None:
        for widget_name, text in widget_data_d.items():
            widget = getattr(dialog, widget_name, None)
            if widget is not None:
                widget.setText(text)
                applied_data[widget_name] = text
        applied_data['widget_data_d'] = widget_data_d

    # Load and attach layers only if provided.
    if aoi_vlay is not None:
        combo_aoi = getattr(dialog, 'comboBox_aoi', None)
        if combo_aoi is not None:
            combo_aoi.setLayer(aoi_vlay)
            applied_data['comboBox_aoi'] = aoi_vlay.id() if hasattr(aoi_vlay, 'id') else None

    if dem_rlay is not None:
        combo_dem = getattr(dialog, 'comboBox_dem', None)
        if combo_dem is not None:
            combo_dem.setLayer(dem_rlay)
            applied_data['comboBox_dem'] = dem_rlay.id() if hasattr(dem_rlay, 'id') else None
            
    if haz_rlay_d is not None:
        #select all of these layers in listView_HZ_hrlay
        dialog.listView_HZ_hrlay.populate_layers()
        dialog.listView_HZ_hrlay.check_byName([layer.name() for layer in haz_rlay_d.values()])
        
        #load into the event metadata
        QTest.mouseClick(dialog.pushButton_HZ_hrlay_load, Qt.LeftButton)
        
    #===========================================================================
    # event values in tableWidget_HZ_eventMeta
    #===========================================================================
    if eventMeta_df is not None:
        assert not haz_rlay_d is None, 'must provide haz_rlay_d to load eval_d'
        #check the keys match
        assert set(eventMeta_df.iloc[:,0]) == set(haz_rlay_d.keys()), 'eval_d keys do not match haz_rlay_d keys'

        """just ignoring what is set above        
        #populate hte new event meta data
        eventMeta_df = dialog.tableWidget_HZ_eventMeta.get_df_from_QTableWidget()
        eventMeta_df[eventMeta_df.columns[1]] = eventMeta_df.iloc[:, 0].map(pd.Series(eval_d))
        """
        
        #eventMeta_df.to_csv(r'l:\09_REPOS\04_TOOLS\CanFlood2\tests\data\cf1_tutorial_02\eventMeta_df.csv', index=False)
        #set the updated on the widget

        dialog.tableWidget_HZ_eventMeta.set_df_to_QTableWidget_spinbox(
            eventMeta_df,widget_type_d=eventMeta_control_d)        
 
        

    return applied_data
 
#===============================================================================
# FIXTURES------
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
def dialog(qgis_iface, qgis_new_project, logger):
    """dialog fixture.
    for interactive tests, see 'test_init' (uncomment block)"""
    
    #indirect parameters    
    dialog =  Main_dialog(parent=None, 
                          iface=qgis_iface,
                          debug_logger=logger, #connect python logger for rtests 
                          )
 
    #post configuration
    
    
    return dialog


 
    
    
 
#===============================================================================
# TESTS------
#===============================================================================
""" 
dialog.show()
QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
sys.exit(QApp.exec_()) #wrap
"""

 
def test_dial_main_00_init(dialog,):
    
    
    #===========================================================================
    # """uncomment the below to use pytest to launch the dialog interactively"""
    # dialog.show()
    # QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
    # sys.exit(QApp.exec_()) #wrap
    #===========================================================================
 
    assert hasattr(dialog, 'logger')
    
    
#===============================================================================
# def test_01_pushButton_PS_projDB_load(dialog):
#     """test loading a project database"""
#     
#     #click the button
#     w = dialog.pushButton_PS_projDB_load    
#     QTest.mouseClick(w, Qt.LeftButton)
#===============================================================================


def test_dial_main_01_create_new_projDB(monkeypatch, dialog, tmpdir, test_name):
    """Test that clicking the 'create new project database' button sets the lineEdit with the dummy file path.
 
 
    """
    dummy_file = tmpdir.join(f'projDB.canflood2').strpath
    
    
    
    monkeypatch.setattr(
        QFileDialog, 
        "getSaveFileName", 
        lambda *args, **kwargs: (dummy_file, "sqlite database files (*.canflood2)")
    )
 
    # Simulate clicking the new project database button.
    QTest.mouseClick(dialog.pushButton_PS_projDB_new, Qt.LeftButton)
    
    #===========================================================================
    # post
    #===========================================================================
    result = dialog.lineEdit_PS_projDB_fp.text()
    write_sqlite(result, oj_out(test_name, result))
     
    # Verify that the lineEdit now contains the dummy file path.
    assert_proj_db_fp(result)
    assert  dialog.lineEdit_PS_projDB_fp.text()== dummy_file
    
 

    
 






@pytest.mark.parametrize("projDB_fp", [oj('01_create_new_projDB', 'projDB.canflood2')])
@pytest.mark.parametrize('tutorial_name', ['cf1_tutorial_02'])
#===============================================================================
# @pytest.mark.parametrize("aoi_fp", [
#     os.path.join(conftest.test_data_dir, 'cf1_tutorial_02', 'aoi_vlay.geojson')
#     ])
# @pytest.mark.parametrize("dem_fp", [
#     os.path.join(conftest.test_data_dir, 'cf1_tutorial_02',  'dem_rlay.tif')]
#     )
#===============================================================================
@pytest.mark.parametrize("widget_data_d", [{'studyAreaLineEdit': 'test_study_area', 'userLineEdit': 'test_user'}])
def test_dial_main_02_save_ui_to_project_database(dialog, projDB_fp,
                                                  aoi_vlay, dem_rlay, widget_data_d, tmpdir):
    """Test that clicking the 'save' button saves the UI to the project database.
 
    """
    #===========================================================================
    # prep
    #===========================================================================
 
    _ = _dialog_preloader(dialog, projDB_fp=projDB_fp, aoi_vlay=aoi_vlay, dem_rlay=dem_rlay,
                          widget_data_d=widget_data_d,
                          tmpdir=tmpdir)
 
    
 
    #===========================================================================
    # execute
    #===========================================================================
    # Simulate clicking the save button.
    QTest.mouseClick(dialog.pushButton_save, Qt.LeftButton) #Main_dialog._save_ui_to_project_database()
    
    
    #===========================================================================
    # test
    #===========================================================================
    # Verify that the project database file path is saved.
    assert_proj_db_fp(projDB_fp)
    
    #load parmeters table
    df = dialog.projDB_get_tables('02_project_parameters')
    
    test_d = df.loc[:, ['widgetName', 'value']].set_index('widgetName').to_dict()['value']
    
    #check against test data
    for widgetName,v in widget_data_d.items():
        assert test_d[widgetName] == v, f'failed to set {widgetName}'
 
 
    
@pytest.mark.parametrize("projDB_fp", [oj('01_create_new_projDB', 'projDB.canflood2')])
def test_dial_main_03_load_project_database(dialog, projDB_fp, monkeypatch):
    """Test that clicking the 'load project database' button sets the lineEdit with the dummy file path.
 
    """
    assert_proj_db_fp(projDB_fp)
 
     
    #dummy_file = "dummy_path_load.db"
    monkeypatch.setattr(
        QFileDialog, 
        "getOpenFileName", 
        lambda *args, **kwargs: (projDB_fp, fileDialog_filter_str)
    )

    # Simulate clicking the load project database button.
    QTest.mouseClick(dialog.pushButton_PS_projDB_load, Qt.LeftButton)
    
    
    
 
@pytest.mark.parametrize("projDB_fp", [
    None, oj('01_create_new_projDB', 'projDB.canflood2')
    ])
def test_dial_main_04_create_new_hazDB(monkeypatch, dialog, test_name, projDB_fp, tmpdir):
    """test the 'create new hazard database' button"""
    
    #setup the Create New hazard database    
    dummy_file = tmpdir.join(f'hazDB.db').strpath    
    
    monkeypatch.setattr(
        QFileDialog, 
        "getSaveFileName", 
        lambda *args, **kwargs: (dummy_file, "sqlite database files (*.db)")
    )
    
    #preload with some data
    if not projDB_fp is None:
        _dialog_preloader(dialog, projDB_fp=projDB_fp, tmpdir=tmpdir)
 
    #===========================================================================
    # execute
    #===========================================================================
    # Simulate clicking the new project database button.
    QTest.mouseClick(dialog.pushButton_HZ_hazDB_new, Qt.LeftButton) #Main_dialog._create_new_hazDB()
    
    #===========================================================================
    # post
    #===========================================================================3
    result = dialog.lineEdit_HZ_hazDB_fp.text()
    assert  result== dummy_file 
    assert_haz_db_fp(result)
    
    #write test data
    if not projDB_fp is None:
        write_sqlite(result, oj_out(test_name, result))








@pytest.mark.parametrize("projDB_fp", [
    oj('01_create_new_projDB', 'projDB.canflood2')
    ])
@pytest.mark.parametrize("hazDB_fp", [oj('04_create_new_hazDB_L___09_REP', 'hazDB.db')])
@pytest.mark.parametrize("widget_data_d", [
    {'scenarioNameLineEdit': 'some scenario', 'climateStateLineEdit': 'some climate', 'hazardTypeLineEdit': 'some hazard'}
    ])
@pytest.mark.parametrize("tutorial_name", ['cf1_tutorial_02']) 
def test_dial_main_05_save_ui_to_hazDB(dialog, projDB_fp, hazDB_fp, haz_rlay_d, eventMeta_df, widget_data_d, tmpdir):
    """test entering in some data and saving to an existing hazDB"""
    
    _dialog_preloader(dialog, 
                      projDB_fp=projDB_fp, hazDB_fp=hazDB_fp,
                      haz_rlay_d=haz_rlay_d,eventMeta_df=eventMeta_df,
                      widget_data_d=widget_data_d, tmpdir=tmpdir)
    
    #===========================================================================
    # execute
    #===========================================================================
    QTest.mouseClick(dialog.pushButton_save, Qt.LeftButton) #Main_dialog._save_ui_to_DBs()
    
    #===========================================================================
    # check
    #===========================================================================
 

    # Retrieve the table from the database.
    df = dialog._hazDB_get_tables('04_haz_meta')
    # view(df)
 
    # Build the expected and actual series.
    expected_series = pd.Series(widget_data_d)
    actual_series = df.set_index('widgetName')['value']
    
    assert_intersecting_values_match_verbose(expected_series, actual_series)
    
    
@pytest.mark.dev 
@pytest.mark.parametrize("projDB_fp", [
    oj('01_create_new_projDB', 'projDB.canflood2')
    ])
@pytest.mark.parametrize("hazDB_fp", [oj('04_create_new_hazDB_L___09_REP', 'hazDB.db')])
@pytest.mark.parametrize("tutorial_name", ['cf1_tutorial_02']) 
def test_dial_main_06_model_configure(dialog, projDB_fp, hazDB_fp, haz_rlay_d, eventMeta_df, tmpdir):
    """test launching the model configuration dialog"""
    
    _dialog_preloader(dialog, projDB_fp=projDB_fp, hazDB_fp=hazDB_fp, haz_rlay_d=haz_rlay_d, eventMeta_df=eventMeta_df,
                      tmpdir=tmpdir)
    
    #get the first model
    model_wrkr = dialog.model_index_d['c1'][0]
    
    #click the button on the associated widget
    QTest.mouseClick(model_wrkr.widget_suite.pushButton_mod_config, Qt.LeftButton) #Model.launch_config_ui
 
    


    
    
    
    
    
    
    
    
    
    