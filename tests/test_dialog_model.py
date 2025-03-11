'''
Created on Mar 6, 2025

@author: cef
'''


#===============================================================================
# IMPORTS----------
#===============================================================================
import pytest, time, sys, inspect, os


from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt, QApplication, QPoint
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem,
    QComboBox,
    )
from qgis.PyQt import QtWidgets

from canflood2.hp.qt import set_widget_value, get_widget_value
from canflood2.assertions import assert_vfunc_fp

from canflood2.dialog_model import Model_config_dialog

from .test_dialog_main import dialog as dialog_main
from .test_dialog_main import oj as oj_main
#need to import the fixture from dialog_main
from .test_dialog_main import widget_data_d

import tests.conftest as conftest
from .conftest import (
    conftest_logger, assert_intersecting_values_match_verbose,
    result_write_filename_prep, click
    )

#===============================================================================
# DATA--------
#===============================================================================
test_data_dir = os.path.join(conftest.test_data_dir, 'test_dialog_model')
os.makedirs(test_data_dir, exist_ok=True)

#===============================================================================
# HELPERS----------
#===============================================================================
def oj(*args):
    return os.path.join(test_data_dir, *args)

def oj_out(test_name, result):
    return oj(result_write_filename_prep(test_name), os.path.basename(result))
 
#===============================================================================
# FIXTURES------
#===============================================================================

#===============================================================================
# dialog setup
#===============================================================================
@pytest.fixture
def dialog(dialog_main, model,
           #turtorial data
           finv_vlay, vfunc_fp, 
           widget_modelConfig_data_d, 
           
           #control
           save_dialog,
           qtbot, monkeypatch):
    """
    Fixture to launch the model configuration dialog in a non-blocking way.
    Instead of calling the normal modal exec_() (which blocks until closed),
    we monkeypatch exec_() to automatically simulate a click on the OK button
    (or otherwise close the dialog) and return Accepted.
    """
    # Retrieve the model from the main dialog and the button that launches the config dialog.
 
    
    dlg = dialog_main.Model_config_dialog

    # Override exec_() so it shows the dialog and returns immediately.
    def non_blocking_exec():
        dlg.show()
        return QtWidgets.QDialog.Rejected  # dummy return value
    monkeypatch.setattr(dlg, "exec_", non_blocking_exec)
    
    
    

    #===========================================================================
    # # Launch the dialog by clicking the widget that opens it.
    #===========================================================================
    widget = model.widget_d['pushButton_mod_config']['widget']
    click(widget)
    qtbot.waitExposed(dlg)  # wait until the dialog is visible
    
    
    #===========================================================================
    # post launch setup
    #===========================================================================
    if finv_vlay is not None:
        dlg.comboBox_finv_vlay.setLayer(finv_vlay)
        
    if widget_modelConfig_data_d is not None:
        for k,v in widget_modelConfig_data_d.items():
            widget = getattr(dlg, k)
            set_widget_value(widget, v)
            
    if vfunc_fp is not None:
        assert_vfunc_fp(vfunc_fp)
        
        #monkeypatch the browse button (pushButton_SScurves)
        
 
        

    #===========================================================================
    # # Yield the live dialog instance for test interaction.
    #===========================================================================
    yield dlg

    #===========================================================================
    # # Teardown: simulate a click on the OK button to close the dialog.
    #===========================================================================
    print(f"Closing model configuration dialog w/ save_dialog={save_dialog}")
    if save_dialog:
        
        qtbot.mouseClick(dlg.pushButton_ok, Qt.LeftButton)
    else:
        qtbot.mouseClick(dlg.pushButton_close, Qt.LeftButton)
    qtbot.waitSignal(dlg.finished, timeout=5000)
    return dialog


@pytest.fixture
def model(dialog_main, consequence_category, modelid):
    return dialog_main.model_index_d[consequence_category][modelid]

#dummy fixtures
@pytest.fixture
def widget_modelConfig_data_d(request):
    return getattr(request, "param", None)

#===============================================================================
# TESTS------
#===============================================================================




@pytest.mark.parametrize("projDB_fp", [oj_main('04_MS_createTemplates_cf1_0ade0c', 'projDB.canflood2')])
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
@pytest.mark.parametrize("save_dialog", [False]) #teardown behavior
def test_dial_model_01_launch_config(dialog,model):
    """simple launching and closing of the model configuration dialog
    
    handled by the fixture
    """     
    assert dialog.model==model
    


@pytest.mark.dev
@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02', oj_main('04_MS_createTemplates_cf1_0ade0c', 'projDB.canflood2'))
])
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
@pytest.mark.parametrize("save_dialog", [True])
@pytest.mark.parametrize("widget_modelConfig_data_d", [
{
    'comboBox_expoLevel':'binary (L1)',    
    'mFieldComboBox_cid':'xid',
     }
])
def test_dial_model_02_save(dialog,model):
    """add some data to the dialog then click save/OK
    """     
    assert dialog.model==model

 
 


    

 