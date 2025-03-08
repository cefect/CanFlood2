'''
Created on Mar 5, 2025

@author: cef
'''


#===============================================================================
# IMPORTS----------
#===============================================================================
import pytest, time, sys, inspect, os, shutil
from pytest_qgis.utils import clean_qgis_layer

from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt, QApplication, QPoint
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem,
    QComboBox,
    )


from qgis.PyQt import QtWidgets


import tests.conftest as conftest
from tests.conftest import conftest_logger

from canflood2.assertions import assert_proj_db_fp

from canflood2.dialog_main import Main_dialog

#===============================================================================
# DATA--------
#===============================================================================
test_data_dir = os.path.join(conftest.test_data_dir, 'test_dialog_main')
os.makedirs(test_data_dir, exist_ok=True)

 

#===============================================================================
# HELPERS---------
#===============================================================================
overwrite_testdata=True
def write_projDB(result, ofp, write=overwrite_testdata):
    if write:
        os.makedirs(os.path.dirname(ofp), exist_ok=True)
        
        #copy over the .sqlite file
        shutil.copyfile(result, ofp) 
 
        conftest_logger.info(f'wrote result to \n    {ofp}')

def oj(*args):
    return os.path.join(test_data_dir, *args)
 
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


def test_dial_main_01_create_new_project_database(monkeypatch, dialog, tmpdir, test_name):
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
    write_projDB(result, os.path.join(test_data_dir, test_name, os.path.basename(result)))
     
    # Verify that the lineEdit now contains the dummy file path.
    assert_proj_db_fp(result)
    assert  dialog.lineEdit_PS_projDB_fp.text()== dummy_file
    
 

    
 


@pytest.mark.dev
@pytest.mark.parametrize("projDB_fp", [oj('test_dial_main_01_create_new_project_database', 'projDB.canflood2')])
@pytest.mark.parametrize("aoi_fp", [
    os.path.join(conftest.test_data_dir, 'cf1_tutorial_02', 'aoi_vlay.geojson')
    ])
@pytest.mark.parametrize("dem_fp", [
    os.path.join(conftest.test_data_dir, 'cf1_tutorial_02',  'dem_rlay.tif')]
    )
def test_dial_main_02_save_ui_to_project_database(dialog, projDB_fp,
                                                  aoi_vlay, dem_rlay):
    """Test that clicking the 'save' button saves the UI to the project database.
 
    """
    #===========================================================================
    # prep
    #===========================================================================
    assert_proj_db_fp(projDB_fp)
 
    # Set the project database file path.
    dialog.lineEdit_PS_projDB_fp.setText(projDB_fp)
    #enable the save button
    dialog.pushButton_save.setEnabled(True)
    
    #add some random info
    d = {'studyAreaLineEdit':'test_study_area','userLineEdit':'test_user'}
    for k,v in d.items():
        w = getattr(dialog, k)
        w.setText(v)
        
    #load the layers to the project using pytest-qgis and then add them to the comboxes
    for layer, widgetName in zip([aoi_vlay, dem_rlay], ['comboBox_aoi', 'comboBox_dem']):
        w = getattr(dialog, widgetName)
        w.setLayer(layer)
        d[widgetName] = layer.id()
 
    
 
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
    df = dialog._projDB_get_tables('02_project_parameters')
    
    test_d = df.loc[:, ['widgetName', 'value']].set_index('widgetName').to_dict()['value']
    
    #check against test data
    for widgetName,v in d.items():
        assert test_d[widgetName] == v, f'failed to set {widgetName}'
 
 
    
@pytest.mark.parametrize("projDB_fp", [oj('test_dial_main_01_create_new_project_database', 'projDB.canflood2')])
def test_dial_main_03_load_project_database(dialog, projDB_fp, monkeypatch):
    """Test that clicking the 'load project database' button sets the lineEdit with the dummy file path.
 
    """
    assert_proj_db_fp(projDB_fp)
 
     
    #dummy_file = "dummy_path_load.db"
    monkeypatch.setattr(
        QFileDialog, 
        "getOpenFileName", 
        lambda *args, **kwargs: (projDB_fp, "sqlite database files (*.canflood2)")
    )

    # Simulate clicking the load project database button.
    QTest.mouseClick(dialog.pushButton_PS_projDB_load, Qt.LeftButton)
    
    
    
    
    
    
    
    
    