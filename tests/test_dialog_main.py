'''
Created on Mar 5, 2025

@author: cef
'''


#===============================================================================
# IMPORTS----------
#===============================================================================
import pytest, time, sys, inspect


from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt, QApplication, QPoint
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem,
    QComboBox,
    )
from qgis.PyQt import QtWidgets




from canflood2.dialog_main import Main_dialog

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
def dialog(qgis_iface, logger):
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



@pytest.mark.dev
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

def test_dial_main_01_load_project_database(monkeypatch, dialog):
    """Test that clicking the 'load project database' button sets the lineEdit with the dummy file path.

    This test overrides QFileDialog.getOpenFileName to return a dummy file path,
    simulates a click on the load button, and then checks that the file path appears in the lineEdit.
    """
    dummy_file = "dummy_path_load.db"
    monkeypatch.setattr(
        QFileDialog, 
        "getOpenFileName", 
        lambda *args, **kwargs: (dummy_file, "sqlite database files (*.db)")
    )

    # Simulate clicking the load project database button.
    QTest.mouseClick(dialog.pushButton_PS_projDB_load, Qt.LeftButton)
    
    # Verify that the lineEdit now contains the dummy file path.
    assert dialog.lineEdit_PS_projDB_fp.text() == dummy_file


 
def test_dial_main_02_create_new_project_database(monkeypatch, dialog):
    """Test that clicking the 'create new project database' button sets the lineEdit with the dummy file path.

    This test overrides QFileDialog.getSaveFileName to return a dummy file path,
    simulates a click on the new project button, and then checks that the file path is displayed in the lineEdit.
    """
    dummy_file = "dummy_path_new.db"
    monkeypatch.setattr(
        QFileDialog, 
        "getSaveFileName", 
        lambda *args, **kwargs: (dummy_file, "sqlite database files (*.db)")
    )

    # Simulate clicking the new project database button.
    QTest.mouseClick(dialog.pushButton_PS_projDB_new, Qt.LeftButton)
    
    # Verify that the lineEdit now contains the dummy file path.
    assert dialog.lineEdit_PS_projDB_fp.text() == dummy_file
    
 
    
    
    
    
    
    
    
    
    
    
    