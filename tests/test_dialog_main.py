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
def test_init(dialog,):
    
    
    """uncomment the below to use pytest to launch the dialog interactively"""
    dialog.show()
    QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
    sys.exit(QApp.exec_()) #wrap
 
 
    
    assert hasattr(dialog, 'logger')