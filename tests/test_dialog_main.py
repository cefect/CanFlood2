'''
Created on Mar 5, 2025

@author: cef
'''


#===============================================================================
# IMPORTS----------
#===============================================================================
import pytest, time, sys, inspect, os, shutil, hashlib
from pytest_qgis.utils import clean_qgis_layer
import pandas as pd

from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt 
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem,
    QComboBox,
    )
from PyQt5.QtCore import QTimer


from qgis.PyQt import QtWidgets


import tests.conftest as conftest
from tests.conftest import (
    conftest_logger, assert_intersecting_values_match_verbose,
    test_result_write_filename_prep, click
    )

from canflood2.assertions import assert_projDB_fp, assert_hazDB_fp

from canflood2.dialog_main import Main_dialog
from canflood2.parameters import fileDialog_filter_str, eventMeta_control_d, consequence_category_d


from canflood2.hp.basic import view_web_df as view

#===============================================================================
# DATA--------
#===============================================================================
test_data_dir = os.path.join(conftest.test_data_dir, 'test_dialog_main')
os.makedirs(test_data_dir, exist_ok=True)

 

#===============================================================================
# HELPERS---------
#===============================================================================
overwrite_testdata=True
def write_sqlite(result, ofp, write=overwrite_testdata):
    if write:
        os.makedirs(os.path.dirname(ofp), exist_ok=True)
        
        #copy over the .sqlite file
        shutil.copyfile(result, ofp) 
 
        conftest_logger.info(f'wrote result to \n    {ofp}')
        

        
 

def oj(*args):
    return os.path.join(test_data_dir, *args)

def oj_out(test_name, result):
    return oj(test_result_write_filename_prep(test_name), os.path.basename(result))


def _dialog_preloader(dialog,  
                      tmpdir=None,
                      projDB_fp=None, hazDB_fp=None, monkeypatch=None,
                      aoi_vlay=None, dem_rlay=None,
                      finv_vlay=None,
                      widget_data_d = None,
                      haz_rlay_d=None,
                      eventMeta_df=None,
                      ):
    """
    Helper to preload the dialog with some data.

 
    """
    # Dictionary to store info about the applied settings.
    applied_data = {}

    #===========================================================================
    # setup databases
    #===========================================================================
    if projDB_fp is not None: 
        projDB_fp = shutil.copyfile(projDB_fp, os.path.join(tmpdir, os.path.basename(projDB_fp)))
        assert_projDB_fp(projDB_fp)
        applied_data['projDB_fp'] = projDB_fp
        
    if hazDB_fp is not None:
        hazDB_fp = shutil.copyfile(hazDB_fp, os.path.join(tmpdir, os.path.basename(hazDB_fp)))
        assert_hazDB_fp(hazDB_fp)
        applied_data['hazDB_fp'] = hazDB_fp
        
        
    #===========================================================================
    # patch load buttons on databases
    #===========================================================================
    """using the loader functions to set the UI state"""
    for fp, buttonName in {
        projDB_fp:'pushButton_PS_projDB_load',
        hazDB_fp:'pushButton_HZ_hazDB_load'}.items():
 
        if fp is None: continue
        assert not monkeypatch is None, f'need to provide monkeypatch for loading from databases'
        #patch the dialog     
        monkeypatch.setattr(QFileDialog,"getOpenFileName",lambda *args, **kwargs: (fp, ''))
    
 
        print(f'clicking {buttonName}\n====================================\n\n')
        # Simulate clicking the load project database button.
        button = getattr(dialog, buttonName)
        click(button)
 
    
    
    
    
    
    
    #===========================================================================
    # setup other attributes
    #===========================================================================

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
        click(dialog.pushButton_HZ_hrlay_load)
 
        
    if finv_vlay is not None:
        pass
        
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

        dialog.tableWidget_HZ_eventMeta.set_df_to_QTableWidget_spinbox(eventMeta_df)        
 
        
    print(f'dialog preloaded with {len(applied_data)} settings')
    return applied_data


def write_both_DBs(dialog, test_name):
    #hazDB_fp
    hazDB_fp = dialog.get_hazDB_fp()
    write_sqlite(hazDB_fp, oj_out(test_name, hazDB_fp))
#projDB
    projDB_fp = dialog.get_projDB_fp()
    write_sqlite(projDB_fp, oj_out(test_name, projDB_fp))
    
 
 
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
    click(dialog.pushButton_PS_projDB_new)
 
    
    #===========================================================================
    # post
    #===========================================================================
    result = dialog.lineEdit_PS_projDB_fp.text()
    write_sqlite(result, oj_out(test_name, result))
     
    # Verify that the lineEdit now contains the dummy file path.
    assert_projDB_fp(result)
    assert  dialog.lineEdit_PS_projDB_fp.text()== dummy_file
    
 

    
 


 
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
def test_dial_main_02_save_ui_to_project_database(dialog, 
                                                  monkeypatch,
                                                  aoi_vlay, dem_rlay, widget_data_d,
                                                  haz_rlay_d, eventMeta_df, 
                                                  tmpdir, test_name,
                                                  ):
    """
    after creating a new project database,
    Test that clicking the 'save' button saves the UI to the project database.
    
    also including hazard info here as this is important for the saving function
 
    """
    #===========================================================================
    # prep
    #===========================================================================
 
    _ = _dialog_preloader(dialog, 
                          #projDB_fp=projDB_fp, 
                          aoi_vlay=aoi_vlay, dem_rlay=dem_rlay,
                          widget_data_d=widget_data_d,
                          haz_rlay_d=haz_rlay_d, eventMeta_df=eventMeta_df,
                          tmpdir=tmpdir)
    
    #===========================================================================
    # #create a new projDB
    #===========================================================================
    dummy_file = tmpdir.join(f'projDB.canflood2').strpath    
    
    monkeypatch.setattr(
        QFileDialog, 
        "getSaveFileName", 
        lambda *args, **kwargs: (dummy_file, "sqlite database files (*.canflood2)")
    )
 
    print('clicking new project database\n====================================\n\n')
    # Simulate clicking the new project database button.
    click(dialog.pushButton_PS_projDB_new)
 
    
    #===========================================================================
    # create a new HazDB
    #===========================================================================
    dummy_file = tmpdir.join(f'hazDB.db').strpath    
    
    monkeypatch.setattr(
        QFileDialog, 
        "getSaveFileName", 
        lambda *args, **kwargs: (dummy_file, "sqlite database files (*.db)")
    )
    
    print('clicking new hazard database\n====================================\n\n')
    # Simulate clicking the new project database button.
    click(dialog.pushButton_HZ_hazDB_new)  #Main_dialog._create_new_hazDB()
 
    #===========================================================================
    # execute
    #===========================================================================

    
    print('clicking save\n====================================\n\n')
    # Simulate clicking the save button.
    click(dialog.pushButton_save) #Main_dialog._save_ui_to_DBs()
 
    
    
    #===========================================================================
    # test
    #===========================================================================
    # Verify that the project database file path is saved.
    result = dialog.get_projDB_fp()
    assert_projDB_fp(result, check_consistency=True)
    
    #load parmeters table
    df = dialog.projDB_get_tables('02_project_parameters')
    
    test_d = df.loc[:, ['widgetName', 'value']].set_index('widgetName').to_dict()['value']
    
    #check against test data
    for widgetName,v in widget_data_d.items():
        assert test_d[widgetName] == v, f'failed to set {widgetName}'
        
        
    #===========================================================================
    # write
    #===========================================================================
    write_both_DBs(dialog, test_name)
 
 


@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02', oj('02_save_ui_to_project_dat_151acb', 'projDB.canflood2'))
])
@pytest.mark.parametrize("hazDB_fp", [
    None, #hazDB won't be copied over and loading will fail 
    oj('02_save_ui_to_project_dat_151acb', 'hazDB.db')
])

def test_dial_main_02b_load_project_database(dialog, 
                                             projDB_fp, hazDB_fp, 
                                             aoi_vlay, dem_rlay, #need to load the layers
                                             monkeypatch, tmpdir,
                                             ):
    """Test that clicking the 'load project database' button sets the lineEdit with the dummy file path.
 
    """
    #===========================================================================
    # setup
    #===========================================================================
    #load the layers
    _dialog_preloader(dialog, aoi_vlay=aoi_vlay, dem_rlay=dem_rlay, tmpdir=tmpdir)
    
    
 
    #copy over the test data to a temporary directory
    projDB_fp = shutil.copyfile(projDB_fp, os.path.join(tmpdir, os.path.basename(projDB_fp)))
    
    if not hazDB_fp is None:
        #needed for when the ui state is loaded from the parameter table
        hazDB_fp = shutil.copyfile(hazDB_fp, os.path.join(tmpdir, os.path.basename(hazDB_fp)))
    
    

    
    #patch the dialog
 
    monkeypatch.setattr(
        QFileDialog, 
        "getOpenFileName", 
        lambda *args, **kwargs: (projDB_fp, fileDialog_filter_str)
    )

    #===========================================================================
    # execute
    #===========================================================================
    print('clicking load project database\n====================================\n\n')
    # Simulate clicking the load project database button.
    click(dialog.pushButton_PS_projDB_load)
    
    #===========================================================================
    # check
    #===========================================================================
    
    hazDB_fp_test = dialog.lineEdit_HZ_hazDB_fp.text()
    if not hazDB_fp is None:
        hazDB_fp_test = dialog.get_hazDB_fp()
        assert_hazDB_fp(hazDB_fp_test)
        
    else:
        assert hazDB_fp_test is None

    
 

    
    




@pytest.mark.parametrize('tutorial_name', ['cf1_tutorial_02'])
@pytest.mark.parametrize("projDB_fp", [
    None, oj('02_save_ui_to_project_dat_151acb', 'projDB.canflood2')
    ])
def test_dial_main_03_create_new_hazDB(monkeypatch, dialog, test_name, projDB_fp, 
                                       tmpdir,
                                        aoi_vlay, dem_rlay, #need to load the layers
                                       ):
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
        _dialog_preloader(dialog, projDB_fp=projDB_fp, tmpdir=tmpdir, monkeypatch=monkeypatch,
                          aoi_vlay=aoi_vlay, dem_rlay=dem_rlay)
 
    #===========================================================================
    # execute
    #===========================================================================
    # Simulate clicking the new project database button.
    click(dialog.pushButton_HZ_hazDB_new) #Main_dialog._create_new_hazDB()
 
    
    #===========================================================================
    # post
    #===========================================================================3
    result = dialog.lineEdit_HZ_hazDB_fp.text()
    assert  result== dummy_file 
    assert_hazDB_fp(result)
    
 
    
    #write the resulting data
    if not projDB_fp is None:        
        write_both_DBs(dialog, test_name)







@pytest.mark.parametrize(
    "projDB_fp, hazDB_fp, tutorial_name",
    [(oj('02_save_ui_to_project_dat_151acb', 'projDB.canflood2'), 
      oj('02_save_ui_to_project_dat_151acb', 'hazDB.db'), 
      'cf1_tutorial_02')]
)
def test_dial_main_05_MS_createTemplates(dialog, projDB_fp, hazDB_fp, haz_rlay_d, 
                                         aoi_vlay, dem_rlay,  #needed to load teh project
                                         tmpdir, test_name, monkeypatch):
    """test creation and clearing of the model suite"""
    
    _dialog_preloader(dialog, projDB_fp=projDB_fp, hazDB_fp=hazDB_fp, haz_rlay_d=haz_rlay_d,
                      aoi_vlay=aoi_vlay, dem_rlay=dem_rlay,
                      tmpdir=tmpdir, monkeypatch=monkeypatch)
    
    #===========================================================================
    # #create the model suite templates
    #===========================================================================
    click(dialog.pushButton_MS_createTemplates)
 
    
    #check they have been added to the dialog index
    assert set(dialog.model_index_d.keys()) == set(consequence_category_d.keys())
    
    #===========================================================================
    # clear the model suite
    #===========================================================================
    print(f'clearing {len(dialog.model_index_d)} model suite templates\n===================================\n\n')
    click(dialog.pushButton_MS_clear)  #Main_dialog._clear_model_suite()
    
    #check they have been removed
    assert len(dialog.model_index_d) == 0
    
    #===========================================================================
    # #create the model suite templates
    #===========================================================================
    
    """creating a second time as an additional test.. also gives us the result data"""
    print(f'creating {len(consequence_category_d)} model suite templates\n======================================\n\n')
    click(dialog.pushButton_MS_createTemplates)  #Main_dialog._create_model_templates()
    
    #check they have been added to the dialog index
    assert set(dialog.model_index_d.keys()) == set(consequence_category_d.keys())
    
    
    #===========================================================================
    # post
    #===========================================================================3
    write_both_DBs(dialog, test_name)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
 

@pytest.mark.parametrize(
    "projDB_fp, hazDB_fp, tutorial_name",
    [(oj('05_MS_createTemplates_L___e728c7', 'projDB.canflood2'), 
      oj('05_MS_createTemplates_L___e728c7', 'hazDB.db'), 
      'cf1_tutorial_02')]
)
def test_dial_main_06_MS_configure(dialog, tmpdir, test_name,
                                   projDB_fp, hazDB_fp,
                                   aoi_vlay, dem_rlay,
                                   haz_rlay_d, eventMeta_df, finv_vlay,
                                   monkeypatch,
                                                                      ):
    """test launching the model configuration dialog"""
    
    _dialog_preloader(dialog, 
                      projDB_fp=projDB_fp, hazDB_fp=hazDB_fp, monkeypatch=monkeypatch,
                        haz_rlay_d=haz_rlay_d, 
                      eventMeta_df=eventMeta_df, 
                      finv_vlay=finv_vlay,
                      aoi_vlay=aoi_vlay, dem_rlay=dem_rlay,
                      tmpdir=tmpdir)
    
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
    QTimer.singleShot(200, lambda: click(model_config_dialog.pushButton_ok))
    
 
    
    #retrieve the widget
    model = dialog.model_index_d[list(consequence_category_d.keys())[0]][0]
    widget = model.widget_d['pushButton_mod_config']['widget']
    click(widget)
 
    
    
    #===========================================================================
    # post
    #===========================================================================3
    result = dialog.get_projDB_fp()

    assert_projDB_fp(result, check_consistency=True)
    
 
    write_both_DBs(dialog, test_name)
    


    

@pytest.mark.dev
@pytest.mark.parametrize(
    "projDB_fp, hazDB_fp, tutorial_name",
    [(oj('06_MS_configure_L__09_REP_ba53e6', 'projDB.canflood2'), 
      oj('06_MS_configure_L__09_REP_ba53e6', 'hazDB.db'), 
      'cf1_tutorial_02')]
)
def test_dial_main_07_MS_run(dialog, tmpdir, test_name,
                                   projDB_fp, hazDB_fp,
                                   aoi_vlay, dem_rlay,
                                   haz_rlay_d, eventMeta_df, finv_vlay,
                                   monkeypatch,
                                                                      ):
    """test launching the model configuration dialog"""
    
    _dialog_preloader(dialog, 
                      projDB_fp=projDB_fp, hazDB_fp=hazDB_fp, monkeypatch=monkeypatch,
                        haz_rlay_d=haz_rlay_d, 
                      eventMeta_df=eventMeta_df, 
                      finv_vlay=finv_vlay,
                      aoi_vlay=aoi_vlay, dem_rlay=dem_rlay,
                      tmpdir=tmpdir)
    
    #===========================================================================
    # launch config window on first model
    #===========================================================================
    #schedule dialog to close
    #model_config_dialog = dialog.Model_config_dialog
    #QTimer.singleShot(200, lambda: QTest.mouseClick(model_config_dialog.pushButton_ok, Qt.LeftButton))
    
    
    #retrieve the widge
    model = dialog.model_index_d[list(consequence_category_d.keys())[0]][0]
    widget = model.widget_d['pushButton_mod_run']['widget']
    print(f'clicking run on model config dialog\n====================================\n\n')
    
    raise NotImplementedError('need to sort out the different run buttons')
    click(widget)
 
    
    #===========================================================================
    # check
    #===========================================================================
    model.get_model_tables_all()
    
    
    
    
    
    
    
    
    
    