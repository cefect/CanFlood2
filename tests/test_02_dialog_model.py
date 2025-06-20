'''
Created on Mar 6, 2025

@author: cef
'''


#===============================================================================
# IMPORTS----------
#===============================================================================
import pytest, time, sys, inspect, os, shutil
import pprint


from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt, QApplication, QPoint
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem, QComboBox,
    )

from qgis.PyQt import QtWidgets
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsMapLayerProxyModel,
    QgsWkbTypes, QgsMapLayer, QgsLogger,
    )


from canflood2.hp.qt import set_widget_value, get_widget_value
from canflood2.hp.vfunc import load_vfunc_to_df_d
from canflood2.hp.basic import view_web_df as view

from canflood2.assertions import assert_vfunc_fp, assert_series_match

from canflood2.dialog_model import Model_config_dialog
from canflood2.core import ModelNotReadyError
import canflood2.parameters as parameters

from tests.test_01_dialog_main import widget_data_d, dialog_main, dialog_loaded
#from tests.test_01_dialog_main import oj as oj_main
from tests.test_01_dialog_main import _04_MS_args, _04_MS_args_d
#need to import the fixture from dialog_main


import tests.conftest as conftest
from .conftest import (
    conftest_logger, 
    result_write_filename_prep, click
    )

#===============================================================================
# DATA--------
#===============================================================================
test_data_dir = os.path.join(conftest.test_data_dir, 'dialog_model')
os.makedirs(test_data_dir, exist_ok=True)


#===============================================================================
# PARAMS--------
#===============================================================================
overwrite_testdata=True #for writing tests
interactive = False
#===============================================================================
# HELPERS----------
#===============================================================================
 



def write_projDB(dialog_model, test_name): 
    projDB_fp = dialog_model.parent.get_projDB_fp()
    ofp = oj_out(test_name, projDB_fp)
 
    if overwrite_testdata:
        print(f'\n\nwriting projDB to \n    {test_name}\n{"="*80}')
        os.makedirs(os.path.dirname(ofp), exist_ok=True)
        
        #copy over the .sqlite file
        shutil.copyfile(projDB_fp, ofp) 
 
        conftest_logger.info(f'wrote result to \n    {ofp}')
        

def oj(*args):
    return os.path.join(test_data_dir, *args)

gfp = lambda x:oj(x, 'projDB.canflood2')

def oj_out(test_name, result):
    return oj(result_write_filename_prep(test_name, clear_str='dial_model_'), os.path.basename(result))
 
#===============================================================================
# FIXTURES------
#===============================================================================

#===============================================================================
# dialog_model setup
#===============================================================================

@pytest.fixture
def dialog_model(
        dialog_loaded, #main dialog. loads layers (except finv) and projDB
        model,
 
        
        #turtorial data
        tutorial_name,
        finv_vlay, #needed to instance the projDB
        
        #general modelConfig widget test data
        #widget_modelConfig_data_d, #tests.data.tutorial_fixtures  
        
        #Asset Inventory function group test data
         
        
        #control fixtures        
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
        projDB model state is handled by test_dialog_main
        
    using subsequent fixtures to handle more complex setups
    
    NOTE:
        click tests seem to erase the pydev pyunit output capture
    """
    # Retrieve the model from the main dialog and the button that launches the config dialog.
    dialog_main = dialog_loaded
    
    dlg = dialog_main.Model_config_dialog
    
    
    print(f"\n\nlaunching model configuration dialog for \'{tutorial_name}\' {model.name}\n{'='*80}")
    
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
    #===========================================================================
    # if finv_vlay is not None:
    #     dlg.comboBox_finv_vlay.setLayer(finv_vlay)
    #===========================================================================
        
    #widget data
    """see fixture"""
    
    #function Groups
    """see fixture"""
    
    #vfuncs
    """see fixture"""
        

 
 
    """ 
    dlg.show()
    QApp = QApplication(sys.argv) #initlize a QT appliaction (inplace of Qgis) to manually inspect    
    sys.exit(QApp.exec_()) #wrap
    """
 
    dialog_loaded.logger.info(f'launched model configuration dialog for model \'{tutorial_name}\'')
        
    return dlg


@pytest.fixture
def model(dialog_main, consequence_category, modelid):
    return dialog_main.model_index_d[consequence_category][modelid]

@pytest.fixture
def finv_vlay_loaded(dialog_model, finv_vlay):
    """loads the finv_vlay into the dialog main
    
    NOTE: other (non-model specific) layers are loaded with the dialog_loaded fixture
    """
    if not finv_vlay is None:
        dialog_model.comboBox_finv_vlay.setLayer(finv_vlay)
        return finv_vlay
    return None


@pytest.fixture
def widget_data_d(dialog_model,
                  widget_modelConfig_data_d, #tests.data.tutorial_fixtures
                  finv_vlay_loaded, #needed for all the layer widgets  
                  ):
    """enters the test data onto each widget of the model config dialog"""
    
 
        
        
    
    assert not widget_modelConfig_data_d is None, 'widget_modelConfig_data_d fixture is None'
    #if widget_modelConfig_data_d is not None:
    for k,v in widget_modelConfig_data_d.items():
        widget = getattr(dialog_model, k)
        try:
            set_widget_value(widget, v)
        except Exception as e:
            raise IOError(f'failed to set widget \'{k}\' to value \'{v}\' w/\n    {e}')
        
        
    return widget_modelConfig_data_d


@pytest.fixture
def vfunc(dialog_model, vfunc_fp, monkeypatch):
    
    #===========================================================================
    # L2 models
    #===========================================================================
    if not vfunc_fp is None:
        assert_vfunc_fp(vfunc_fp)
        
        #patch the file dialog
        """over-writes the monkeypatch from teh main dialog test?"""
        monkeypatch.setattr(QFileDialog,"getOpenFileName",lambda *args, **kwargs: (vfunc_fp, ''))
        
        click(dialog_model.pushButton_V_vfunc_load) #Model_config_dialog._vfunc_load_from_file()
        
        return vfunc_fp
    
    #===========================================================================
    # L1 Models
    #===========================================================================
    return None

@pytest.fixture
def functionGroups_d(dialog_model, widget_FunctionGroup_t, finv_vlay):
    
    if widget_FunctionGroup_t is not None:
        result_d=dict()
        cnt=0
        for i, test_d in enumerate(widget_FunctionGroup_t):
            #add the group
            fg_index, widget, widget_d = dialog_model._add_function_group()
            
            result_d[fg_index] = dict()
            
            #set the values
            for name, d_i in widget_d.items():
                if d_i['tag'] is not None:
                    target_fieldName = test_d[d_i['tag']]
 
                    
                    #check this is in the layer
                    assert target_fieldName in finv_vlay.fields().names(), 'bad field name'
                    
                    #select it with the widget
                    d_i['widget'].setField(target_fieldName)
                    cnt+=1
                    
                    result_d[fg_index][d_i['tag']] = target_fieldName
                    
        print(f'set {cnt} function group fields')
    
    else:
        result_d=None
        
    return result_d



#===============================================================================
# TESTS------
#===============================================================================
"""STRATEGY

lots of small tests with checks

then one complete test to build the projDB for the next phase"""


 
@pytest.mark.parametrize(*_04_MS_args)
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_01_launch_config(dialog_model,model, qtbot):
    """simple launching and closing of the model configuration dialog
    
    loads a simple projDB_fp (just initialized models)
    """     
    #assert dialog.model==model
    
    #===========================================================================
    # close
    #===========================================================================
    qtbot.mouseClick(dialog_model.pushButton_close, Qt.LeftButton)
    
    print(f'done')




#===============================================================================
# @pytest.mark.parametrize("tutorial_name, projDB_fp", [
#     ('cf1_tutorial_02', oj_main('04_MS_createTemplates_cf1_f72317', 'projDB.canflood2')),
#     ('cf1_tutorial_02b', oj_main('04_MS_createTemplates_cf1_ea97b3', 'projDB.canflood2'))
# ])
#===============================================================================


@pytest.mark.parametrize(
    ("tutorial_name", "projDB_fp"),
    [
        pytest.param(
            'cf1_tutorial_01',_04_MS_args_d['cf1_tutorial_01'],
            marks=pytest.mark.xfail(reason="have not specified finv_elevType",strict=True  ),
        ),
        pytest.param(
            'cf1_tutorial_02',_04_MS_args_d['cf1_tutorial_02'],
            #marks=pytest.mark.xfail(reason="no vlay provided yet",strict=True),
        ),
        # Additional cases you commented out can stay commented:
        # pytest.param('cf1_tutorial_02b', oj('04_MS_createTemplates_cf1_ea97b3', 'projDB.canflood2')),
        # pytest.param('cf1_tutorial_02c', oj('04_MS_createTemplates_cf1_1ae7e8', 'projDB.canflood2')),
    ]
)
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_02_save(dialog_model,
                            model,
                            finv_vlay_loaded,
                                                      
                            test_name, qtbot):
    """basic model dialog init + slect finv + save
    
    model init:
        
    clicking save loads:
        table_parameters
        table_finv
        table_expos
        table_gels
        
    does NOT load
        vfuncs
        functionGroups (f1+)
        results
    """     
    #assert dialog.model==model
    #===========================================================================
    # load parameters
    #===========================================================================
    """done by fixture"""
    #===========================================================================
    # resolve dialog
    #===========================================================================
 
    click(dialog_model.pushButton_save)
    
    #===========================================================================
    # check---------
    #===========================================================================
    print(f'\n\nchecking dialog\n{"="*80}')
    

        
        

    #===========================================================================
    # write------
    #===========================================================================
    #write_projDB(dialog_model, test_name)
    
    
 

@pytest.mark.parametrize(*_04_MS_args)
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_02_widgetData(dialog_model,
                            model, 
                               
                            widget_data_d,
                            ):
    """ model dialog launch + widget data + save
    """
        #===========================================================================
    # load parameters
    #===========================================================================
    """done by fixture"""
    #===========================================================================
    # resolve dialog
    #===========================================================================
 
    click(dialog_model.pushButton_save)
    
    #===========================================================================
    # checks----------
    #===========================================================================

    #===========================================================================
    # #against testing parameters
    #===========================================================================
    for k,v in widget_data_d.items():
        #print(f'checking \'{k}\'==\'{v}\'')
        widget = getattr(dialog_model, k)
        assert get_widget_value(widget)==v, f'for \'{k}\' got bad value \'{get_widget_value(widget)}\''
        
    #===========================================================================
    # #against set projeft Database
    #===========================================================================
    param_df = model.get_table_parameters().set_index('varName')
    
    ##param_df = param_df.set_index('varName').loc[:, ['widgetName', 'value']]
    param_d = param_df[~param_df['dynamic']].dropna(subset=['widgetName']).set_index('widgetName')['value'].dropna().to_dict()
    assert len(param_d)>0, f'no parameters found for model \'{model.name}\''
    #checkc that the keys match

    
    # Check if widget_data_d keys are a subset of param_d keys
    """
    param_d['comboBox_finv_vlay']
    view(param_df)
    pprint.pprint(widget_data_d)
    """
    
    #these widgets are unique as we enter data here but dont include in the params
    #they are converted to nested dynamic parameters
    ignore_widgets_l = [
        'mFieldComboBox_AI_01_elev',  'mFieldComboBox_AI_01_scale',
        'mFieldComboBox_AI_01_tag', 'mFieldComboBox_AI_01_cap',
        ]
    
    check_k = set(widget_data_d.keys()) - set(ignore_widgets_l)


    if not set(check_k).issubset(param_d.keys()):
        missing_keys = set(check_k) - set(param_d.keys())
        raise AssertionError(f'Parameter keys do not match the widget data keys. \n    Missing keys: {missing_keys}')

    #loop and check each
    for k,v in widget_data_d.items():
        if k in ignore_widgets_l: continue
        assert str(v)==param_d[k], f'for \'{k}\' got bad value \'{v}\''


L2_MS_args = ( #params for L2 models
    ("tutorial_name", "projDB_fp"),[
        ('cf1_tutorial_02',_04_MS_args_d['cf1_tutorial_02']),
        ('cf1_tutorial_02d',_04_MS_args_d['cf1_tutorial_02d']),
         ('cf1_tutorial_02d_2',_04_MS_args_d['cf1_tutorial_02d']),
])



@pytest.mark.parametrize(*L2_MS_args)
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_03_vfunc(dialog_model, model, 
                             finv_vlay_loaded, widget_data_d,                                
                            vfunc,
                            test_name, qtbot):
    """init + finv (needed for widgets) + widgets + vfunc load + save
    
    also loads:
        06_vfunc_index
        07_vfunc_data
    
    WARNING: pydev + pyunit capture is reset by the click tests
    
    NOTE: for L1 models, this test is identical to test_dial_model_02_save
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
    click(dialog_model.pushButton_save)
 
    
    #===========================================================================
    # check---------
    #===========================================================================
    print(f'\n\nchecking dialog\n{"="*80}')
    
    #check the vfunc index 
    vfunc_index_df = dialog_model.parent.projDB_get_tables(['06_vfunc_index'])[0]
    
    
    vfunc_fp = vfunc
    if not vfunc_fp is None:
        df_d = load_vfunc_to_df_d(vfunc_fp)
        assert len(df_d)==int(dialog_model.label_V_functionCount.text()), f'vfunc count failed to set'
        

        #check the keys match
        assert set(df_d.keys())==set(vfunc_index_df.index), 'vfunc keys do not match the index'
        
    else:
        assert len(vfunc_index_df)==0, 'expected no vfuncs in index'

        
    #===========================================================================
    # write------
    #===========================================================================
    #write_projDB(dialog_model, test_name)


 





@pytest.mark.parametrize(*L2_MS_args)
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_04_functionGroup(dialog_model,model, qtbot,
                                     finv_vlay_loaded, widget_data_d, 
                                     functionGroups_d, 
                                     ):
    """save + finv+widgets+ functionGroups
    
    add and remove then check
    """
    if functionGroups_d is None: functionGroups_d = dict()     
    #assert dialog.model==model
    gcnt =  1+len(functionGroups_d)
    assert len(dialog_model.functionGroups_index_d)==gcnt, 'expected one additional function group'
    w1 =  dialog_model.functionGroups_index_d[len(functionGroups_d)]['widget']
    
    
    #===========================================================================
    # add a new one
    #===========================================================================
    click(w1.pushButton_mod_plus)
    gcnt+=1
    
    assert len(dialog_model.functionGroups_index_d)==gcnt
    #===========================================================================
    # remove it
    #===========================================================================
    click(dialog_model.functionGroups_index_d[gcnt-1]['widget'].pushButton_mod_minus)
    gcnt-=1
    assert len(dialog_model.functionGroups_index_d)==gcnt
    
    
    #===========================================================================
    # save
    #===========================================================================
    click(dialog_model.pushButton_save)
    
    
    #===========================================================================
    # Check it----------
    #===========================================================================
 
    #===========================================================================
    # dialog status
    #===========================================================================
    #check the function groups
    assert len(dialog_model.functionGroups_index_d)==len(functionGroups_d)+1, \
        f'expected {len(functionGroups_d)} function groups, got {len(dialog_model.functionGroups_index_d)}'
    
    #check the Additionals
    for fg_index, fg_d in functionGroups_d.items():
        #check against what is set on the dialog
        parent_d = dialog_model.functionGroups_index_d[fg_index]
        widget = parent_d['widget']
        
        #index by tag
        child_widget_d = {d['tag']:k for k,d in parent_d['child_d'].items() if d['tag'] is not None}
        
        for tag, value in fg_d.items():
            
            w = getattr(widget, child_widget_d[tag])
            assert get_widget_value(w)==value, f'for \'{tag}\' got bad value \'{get_widget_value(w)}\''

    #===========================================================================
    # projDB
    #===========================================================================
    param_df = model.get_table_parameters().set_index('varName'
                          ).dropna(subset=['fg_index']).drop(['dynamic', 'required', 'model_index'], axis=1)
 
    assert param_df['value'].notna().all(), 'expected all parameter values to be set'
    #check main (fg=0)
    #main_fg_df = param_df[param_df['fg_index']==0] 
    
    
    #f0 fields
    fg0_fields = {'f0_cap':'mFieldComboBox_AI_01_scale',
                  'f0_elev':'mFieldComboBox_AI_01_elev',  
                  'f0_tag':'mFieldComboBox_AI_01_tag',
                  'f0_cap':'mFieldComboBox_AI_01_cap',
                  }
    
    for k, widget_name in fg0_fields.items():
        assert param_df.loc[k, 'value']==widget_data_d[widget_name], 'f0 mismatch'
        
    #f1+fields
    for fg_index, fg_d in functionGroups_d.items():
        for tag, value in fg_d.items():
            
            k = f'f{fg_index}_{tag}'
            
            assert param_df.loc[k, 'value'] == value, f'for \'{k}\' got bad value \'{param_df.loc[k, "value"]}\''
 

#add the psudo test
_04_MS_args[1].append(
    ('cf1_tutorial_02d_2',_04_MS_args_d['cf1_tutorial_02d'])
)



@pytest.mark.parametrize(*_04_MS_args)
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_10_saveAll(dialog_model, model,
                               finv_vlay_loaded,
                               widget_data_d,                                  
                            vfunc,
                            functionGroups_d,
                            test_name, qtbot):
    """all save tests
    i.e. modle compiling
    """
    
    #===========================================================================
    # save
    #===========================================================================
    click(dialog_model.pushButton_save) #Model_config_dialog._save()
    
    #===========================================================================
    # write------
    #===========================================================================
    write_projDB(dialog_model, test_name)
    
    
    
    
    
 
    

_10_save_args = ("tutorial_name, projDB_fp", [
    pytest.param('cf1_tutorial_01', gfp('test_10_saveAll_c1-0-cf1__bbaceb'),),  
    pytest.param('cf1_tutorial_02', gfp('test_10_saveAll_c1-0-cf1__89377f'),),
    pytest.param('cf1_tutorial_02b', gfp('test_10_saveAll_c1-0-cf1__40367f'),),
    pytest.param('cf1_tutorial_02c', gfp('test_10_saveAll_c1-0-cf1__51ada1'),),
    pytest.param('cf1_tutorial_02d', gfp('test_10_saveAll_c1-0-cf1__114fcd'),),
    pytest.param('cf1_tutorial_02d_2', gfp('test_10_saveAll_c1-0-cf1__ccfc45'),),
])


@pytest.mark.dev
@pytest.mark.parametrize(*_10_save_args)
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_dial_model_20_run(dialog_model, model,
                           
                           finv_vlay_loaded,
                           
                           test_name,tutorial_name 
                           ):
    """run the model (post compile)
    loads compiled data via the projDB
    

    
    NOTE: using this as the endpoint ProjDB for:
        - builgin plugin tutorial data
        - test_04_dialog_main_post.py
    """
    
    #===========================================================================
    # load parameters 
    #===========================================================================
    """done by dialog_model (loads projDB)"""
    
    #===========================================================================
    # load layers
    #===========================================================================
    """finv_vlay_loaded loads the finv
    other layers are loaded by dialog_loaded fixture
    """
    
    #===========================================================================
    # load vfuncs
    #===========================================================================
    """done by dialog_model (loads projDB)"""
    
    #===========================================================================
    # compile model tables
    #===========================================================================
    """included in projDB... just checking"""
    df_d = model.get_tables(model.compile_model_tables, result_as_dict=True)
    for table_name, df in df_d.items(): 
        assert len(df)>0, f'got empty table \'{table_name}\''
    
    #===========================================================================
    # trigger run sequence
    #===========================================================================
    try:
        click(dialog_model.pushButton_run) # Model_config_dialog._run_model()
    except Exception as e:
        raise ModelNotReadyError(f'failed to run model \'{model.name}\' w/ error: {e}')
    
    #===========================================================================
    # check
    #===========================================================================
    print(f'\n\nchecking dialog_model\n{"="*80}')
    
    
    #table presence
    for table_name in model.compile_model_tables:
        df = model.get_tables([table_name])[0]
        assert len(df)>0, f'got empty table \'{table_name}\''
        
    #result value
    assert float(model.get_parameter_value('result_ead'))>0
    
    
    #===========================================================================
    # write------
    #===========================================================================
    write_projDB(dialog_model, test_name)
    
    #write to plugin test
    #moved this to test_05
    #===========================================================================
    # if overwrite_testdata_plugin:
    #     from canflood2.tutorials.tutorial_data_builder import test_data_dir as plugin_test_data_dir
    #     
    #     ofp = os.path.join(plugin_test_data_dir, 'projDBs', tutorial_name+'.canflood2')
    #     #assert os.path.exists(ofp), f'expected to find a projDB file at \n    {ofp}'
    #     
    #     #copy over the .sqlite file
    #     projDB_fp = dialog_model.parent.get_projDB_fp()
    #     shutil.copyfile(projDB_fp, ofp) 
    #     
    #     dialog_model.logger.info(f'wrote projDB_fp to \n    {ofp}')
    #===========================================================================
        
        
    
    

_20_run_args = ("tutorial_name, projDB_fp", [
    pytest.param('cf1_tutorial_01',oj('test_20_run_c1-0-cf1_tuto_392609', 'projDB.canflood2'),),  
    pytest.param('cf1_tutorial_02',oj('test_20_run_c1-0-cf1_tuto_13a988', 'projDB.canflood2'),),
    pytest.param('cf1_tutorial_02b',oj('test_20_run_c1-0-cf1_tuto_802bc4', 'projDB.canflood2'),),
    pytest.param('cf1_tutorial_02c',oj('test_20_run_c1-0-cf1_tuto_6e937d', 'projDB.canflood2'),),
    pytest.param('cf1_tutorial_02d',oj('test_20_run_c1-0-cf1_tuto_45abf7', 'projDB.canflood2'),),
    ])












     

 