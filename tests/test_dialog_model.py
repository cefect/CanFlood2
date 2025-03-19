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
from canflood2.hp.vfunc import load_vfunc_to_df_d

from canflood2.assertions import assert_vfunc_fp, assert_series_match

from canflood2.dialog_model import Model_config_dialog
from canflood2.core import ModelNotReadyError

from .test_dialog_main import dialog as dialog_main
from .test_dialog_main import oj as oj_main
#need to import the fixture from dialog_main
from .test_dialog_main import widget_data_d

import tests.conftest as conftest
from .conftest import (
    conftest_logger, 
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
           finv_vlay, 
 
           widget_modelConfig_data_d, #tests.data.tutorial_data_builder.widget_settings_d
           
           #control
 
           qtbot, monkeypatch,
           #backend init
           qgis_processing
           ):
    """
    Fixture to launch the model configuration dialog in a non-blocking way.
    Instead of calling the normal modal exec_() (which blocks until closed),
    we monkeypatch exec_() to automatically simulate a click on the OK button
    (or otherwise close the dialog) and return Accepted.
    
    
    not using modelstate stored in projDB here
        tests are more focused on replicating user input
        projDB model state is handled by teest_dialog_main
        
    using subsequent fixtures to handle more complex setups
    
    NOTE:
        click tests seem to erase the pydev pyunit output capture
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
            
 
    """ 
    dlg.show()
    QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
    sys.exit(QApp.exec_()) #wrap
    """
 
        
    return dlg


@pytest.fixture
def model(dialog_main, consequence_category, modelid):
    return dialog_main.model_index_d[consequence_category][modelid]


@pytest.fixture
def vfunc(dialog, vfunc_fp, monkeypatch):
    
    assert_vfunc_fp(vfunc_fp)
    
    #patch the file dialog
    """over-writes the monkeypatch from teh main dialog test?"""
    monkeypatch.setattr(QFileDialog,"getOpenFileName",lambda *args, **kwargs: (vfunc_fp, ''))
    
    click(dialog.pushButton_V_vfunc_load) #Model_config_dialog._vfunc_load_from_file()
    
    return vfunc_fp



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
                            widget_modelConfig_data_d, 
                            test_name, qtbot):
    """basic dialog prep then click save/OK
    """     
    #assert dialog.model==model
    #===========================================================================
    # load parameters
    #===========================================================================
    """done by fixture"""
    #===========================================================================
    # resolve dialog
    #===========================================================================
    #click(dialog.pushButton_ok)
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
        
 

        
    #===========================================================================
    # write------
    #===========================================================================
    write_projDB(dialog, test_name)
 




@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02', oj_main('04_MS_createTemplates_cf1_0ade0c', 'projDB.canflood2'))
])
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_03_save_vfunc(dialog, model,                                  
                            vfunc,
                            test_name, qtbot):
    """basic + vfunc loading
    
    WARNING: pydev + pyunit capture is reset by the click tests
    """     
    #assert dialog.model==model
    #===========================================================================
    # load parameters
    #===========================================================================
    """done by dialog fixture"""
    
    #===========================================================================
    # load vfuncs
    #===========================================================================
    """done by vfunc fixture"""
 
    #===========================================================================
    # resolve dialog
    #===========================================================================
    click(dialog.pushButton_ok)
    #qtbot.mouseClick(dialog.pushButton_ok, Qt.LeftButton) #Model_config_dialog._save_and_close()
    
    #===========================================================================
    # check---------
    #===========================================================================
    print(f'\n\nchecking dialog\n{"="*80}')
    
 
    vfunc_fp = vfunc
    df_d = load_vfunc_to_df_d(vfunc_fp)
    assert len(df_d)==int(dialog.label_V_functionCount.text()), f'vfunc count failed to set'
    
    #check the vfunc index 
    vfunc_index_df = dialog.parent.projDB_get_tables(['06_vfunc_index'])[0]
 
    
    #check the keys match
    assert set(df_d.keys())==set(vfunc_index_df.index), 'vfunc keys do not match the index'

        
    #===========================================================================
    # write------
    #===========================================================================
    write_projDB(dialog, test_name)



@pytest.mark.dev
@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    pytest.param(
        'cf1_tutorial_02',oj('03_save_vfunc_c1-0-cf1_tu_3f2fee', 'projDB.canflood2'),
            #doesnt work with the qt dialog
            #marks=pytest.mark.xfail(strict=True, raises=ModelNotReadyError, reason="missing ui entries")
    )
])
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_04_compile(dialog, model,
                           test_name, 
                           ):
    """Test compile sequence"""
    
    #===========================================================================
    # load parameters
    #===========================================================================
    """done by fixture"""
    
    #===========================================================================
    # load vfuncs
    #===========================================================================
    """included in projDB"""    
    #===========================================================================
    # execute
    #===========================================================================
    """this is part of the run call"""
    skwargs = dict(logger=dialog.logger, model=model)
    
    dialog._set_ui_to_table_parameters(**skwargs)
    dialog.compile_model(**skwargs)
    #click(dialog.pushButton_run) #Model_config_dialog._run_model()
    
    
    #===========================================================================
    # check
    #===========================================================================
    print(f'\n\nchecking dialog\n{"="*80}')
    
    df_d = model.get_tables(model.compile_model_tables, result_as_dict=True)
    for table_name, df in df_d.items(): 
        assert len(df)>0, f'got empty table \'{table_name}\''
        
    
    
    #===========================================================================
    # write------
    #===========================================================================
    write_projDB(dialog, test_name)




@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    pytest.param(
        'cf1_tutorial_02',oj('04_compile_c1-0-cf1_tutor_de8ebb', 'projDB.canflood2'),
    )
])
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_05_run(dialog, model,
                           test_name, 
                           ):
    """Test run (post compile)"""
    
    #===========================================================================
    # load parameters
    #===========================================================================
    """done by fixture"""
    
    #===========================================================================
    # load vfuncs
    #===========================================================================
    """included in projDB""" 
    
    #===========================================================================
    # compile model tables
    #===========================================================================
    """included in projDB"""
    df_d = model.get_tables(model.compile_model_tables, result_as_dict=True)
    for table_name, df in df_d.items(): 
        assert len(df)>0, f'got empty table \'{table_name}\''
    
    #===========================================================================
    # trigger run sequence
    #===========================================================================
    dialog._run_model(compile_model=False)
    
    #===========================================================================
    # check
    #===========================================================================
    print(f'\n\nchecking dialog\n{"="*80}')
    
    
    for table_name in model.compile_model_tables:
        df = model.get_tables(table_name)
        assert len(df)>0, f'got empty table \'{table_name}\''
        
    
    
    #===========================================================================
    # write------
    #===========================================================================
    write_projDB(dialog, test_name)
    














     

 