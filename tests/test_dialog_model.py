'''
Created on Mar 6, 2025

@author: cef
'''


#===============================================================================
# IMPORTS----------
#===============================================================================
import pytest, time, sys, inspect, os, shutil


from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt, QApplication, QPoint
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem,
    QComboBox,
    )
from qgis.PyQt import QtWidgets

from canflood2.hp.qt import set_widget_value, get_widget_value
from canflood2.assertions import assert_vfunc_fp
from canflood2.parameters import load_vfunc_to_df_d
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


overwrite_testdata=True
def write_projDB(dialog, test_name):
 
    projDB_fp = dialog.parent.get_projDB_fp()
    ofp = oj_out(test_name, projDB_fp)
 
    if overwrite_testdata:
        os.makedirs(os.path.dirname(ofp), exist_ok=True)
        
        #copy over the .sqlite file
        shutil.copyfile(projDB_fp, ofp) 
 
        conftest_logger.info(f'wrote result to \n    {ofp}')
        

def oj(*args):
    return os.path.join(test_data_dir, *args)

def oj_out(test_name, result):
    return oj(result_write_filename_prep(test_name, clear_str='test_dial_model_'), os.path.basename(result))
 
#===============================================================================
# FIXTURES------
#===============================================================================

#===============================================================================
# dialog setup
#===============================================================================
interactive = False
@pytest.fixture
def dialog(dialog_main, model,
           #turtorial data
           finv_vlay, vfunc_fp, 
           widget_modelConfig_data_d, 
           
           #control
 
           qtbot, monkeypatch):
    """
    Fixture to launch the model configuration dialog in a non-blocking way.
    Instead of calling the normal modal exec_() (which blocks until closed),
    we monkeypatch exec_() to automatically simulate a click on the OK button
    (or otherwise close the dialog) and return Accepted.
    """
    # Retrieve the model from the main dialog and the button that launches the config dialog.
 
    
    dlg = dialog_main.Model_config_dialog
    



    
    
    print(f"\n\nlaunching model configuration dialog for model \'{model.name}\'\n{'='*80}")
    
    #===========================================================================
    # # Launch the dialog by clicking the widget that opens it.
    #===========================================================================
    # Override exec_() so it shows the dialog and returns immediately.
    def non_blocking_exec():
        dlg.show()
        return QtWidgets.QDialog.Rejected  # dummy return value
    monkeypatch.setattr(dlg, "exec_", non_blocking_exec)
    
    
    widget = model.widget_d['pushButton_mod_config']['widget']
    click(widget)
    if not interactive: qtbot.waitExposed(dlg)  # wait until the dialog is visible
    
    

    #===========================================================================
    # post launch setup
    #===========================================================================
    if finv_vlay is not None:
        dlg.comboBox_finv_vlay.setLayer(finv_vlay)
        
    if widget_modelConfig_data_d is not None:
        for k,v in widget_modelConfig_data_d.items():
            widget = getattr(dlg, k)
            try:
                set_widget_value(widget, v)
            except Exception as e:
                raise IOError(f'failed to set widget \'{k}\' to value \'{v}\' w/\n    {e}')
            
    if vfunc_fp is not None:
        assert_vfunc_fp(vfunc_fp)
        
        #patch the file dialog
        """over-writes the monkeypatch from teh main dialog test?"""
        monkeypatch.setattr(QFileDialog,"getOpenFileName",lambda *args, **kwargs: (vfunc_fp, ''))
        
        click(dlg.pushButton_SScurves)
        
        
 
    """ 
    dlg.show()
    QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
    sys.exit(QApp.exec_()) #wrap
    """
 
        
    return dlg


@pytest.fixture
def model(dialog_main, consequence_category, modelid):
    return dialog_main.model_index_d[consequence_category][modelid]



#===============================================================================
# TESTS------
#===============================================================================




@pytest.mark.parametrize("projDB_fp", [oj_main('04_MS_createTemplates_cf1_0ade0c', 'projDB.canflood2')])
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_01_launch_config(dialog,model, qtbot):
    """simple launching and closing of the model configuration dialog
    
    handled by the fixture
    """     
    #assert dialog.model==model
    
    #===========================================================================
    # close
    #===========================================================================
    qtbot.mouseClick(dialog.pushButton_close, Qt.LeftButton)
    



@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02', oj_main('04_MS_createTemplates_cf1_0ade0c', 'projDB.canflood2'))
])
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_02_save(dialog,
                            model, 
                            widget_modelConfig_data_d, vfunc_fp,
                            test_name, qtbot):
    """add some data to the dialog then click save/OK
    """     
    #assert dialog.model==model
    #===========================================================================
    # load parameters
    #===========================================================================
    """done by fixture"""
    #===========================================================================
    # resolve dialog
    #===========================================================================
    qtbot.mouseClick(dialog.pushButton_ok, Qt.LeftButton)
    
    #===========================================================================
    # check---------
    #===========================================================================
    print(f'\n\nchecking dialog\n{"="*80}')
    
    #against testing parameters
    for k,v in widget_modelConfig_data_d.items():
        #print(f'checking \'{k}\'==\'{v}\'')
        widget = getattr(dialog, k)
        assert get_widget_value(widget)==v, f'for \'{k}\' got bad value \'{get_widget_value(widget)}\''
        
    #against set projeft Database
    param_df = model.get_table_parameters().set_index('varName')
    
    ##param_df = param_df.set_index('varName').loc[:, ['widgetName', 'value']]
    param_d = param_df.dropna(subset=['widgetName']).set_index('widgetName')['value'].dropna().to_dict()
    assert len(param_d)>0, f'no parameters found for model \'{model.name}\''
    #checkc that the keys match
    assert set(widget_modelConfig_data_d.keys()).issubset(param_d.keys()), 'parameter keys do not match the widget data keys'
    
    
    #loop and check each
    for k,v in widget_modelConfig_data_d.items():
        assert v==param_d[k], f'for \'{k}\' got bad value \'{v}\''
        
    #check vfunc status
    if not vfunc_fp is None:
        df_d = load_vfunc_to_df_d(vfunc_fp)
        assert len(df_d)==int(dialog.label_V_functionCount.text()), f'vfunc count failed to set'
        assert param_df.loc['vfunc_fp', 'value']==vfunc_fp, f'vfunc_fp failed to set'
        
    #===========================================================================
    # write------
    #===========================================================================
    write_projDB(dialog, test_name)
 
 

@pytest.mark.dev
@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02', oj('02_save_c1-0-cf1_tutorial_04e68f', 'projDB.canflood2'))
])
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_03_run(dialog, model,
                           test_name, qtbot,
                           ):
    
    #===========================================================================
    # load parameters
    #===========================================================================
    """done by fixture"""
    
    #===========================================================================
    # execute
    #===========================================================================
    click(dialog.pushButton_run)
    
    
    #===========================================================================
    # check
    #===========================================================================
    print(f'\n\nchecking dialog\n{"="*80}')















     

 