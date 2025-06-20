'''
Created on Mar 6, 2025

@author: cef
'''


import pytest, os, shutil, copy
 
from PyQt5.QtWidgets import QWidget
from canflood2.core import Model, Model_table_assertions
from canflood2.dialog_main import Main_dialog_projDB 

from tests.test_02_dialog_model import oj as oj_dModel

import tests.conftest as conftest
from .conftest import (
    conftest_logger, 
    result_write_filename_prep, click
    )

from canflood2.parameters import modelTable_params_d

modelTable_params_allowed_d = copy.copy(modelTable_params_d['table_parameters']['allowed'])

from .test_02_dialog_model import _10_save_args as DM_save_args
#===============================================================================
# DATA--------
#===============================================================================
test_data_dir = os.path.join(conftest.test_data_dir, 'core')
os.makedirs(test_data_dir, exist_ok=True)



#===============================================================================
# helpers
#===============================================================================

overwrite_testdata=False
def write_projDB(model, test_name):
 
    projDB_fp = model.parent.get_projDB_fp()
    ofp = oj_out(test_name, projDB_fp)
 
    if overwrite_testdata:
        os.makedirs(os.path.dirname(ofp), exist_ok=True)
        
        #copy over the .sqlite file
        shutil.copyfile(projDB_fp, ofp) 
 
        conftest_logger.info(f'wrote result to \n    {ofp}')
        

def oj(*args):
    return os.path.join(test_data_dir, *args)

def oj_out(test_name, result):
    return oj(result_write_filename_prep(test_name, clear_str='test_core_'), os.path.basename(result))

class Main_dialog_emulator(Main_dialog_projDB, Model_table_assertions):
    """emulating the main_dialopg without the qt ovcerhead"""
    def __init__(self, logger=None, projDB_fp=None):
        self.logger = logger
        self.model_index_d=dict()
        self.projDB_fp=projDB_fp
        
        self.logger.debug(f'Main_dialog_emulator initiated on \n    {projDB_fp}')
        
    def add_model(self, model):
        model.parent=self
        
        index_d = model.get_index_d()
        
        #setup model index
        category_code = index_d['category_code']
        if not category_code in self.model_index_d:
            self.model_index_d[category_code] = dict()
        
        self.model_index_d[index_d['category_code']][index_d['modelid']] = model
        
        model.update_parameter_d()
        
    def get_projDB_fp(self):
        """should override the parent method"""
        return self.projDB_fp
    
class Model_emulator(Model):
    
    def compute_status(self, *args, **kwargs):
        return ''
 
#===============================================================================
# fixtures-------
#===============================================================================
@pytest.fixture
def dialog(logger, projDB_fp, tmpdir):
    """emulate the Main_dialog"""
    assert os.path.exists(projDB_fp)
    projDB_fp = shutil.copyfile(projDB_fp, os.path.join(tmpdir, os.path.basename(projDB_fp)))
    
    dialog = Main_dialog_emulator(logger=logger, projDB_fp=projDB_fp)
    return dialog

@pytest.fixture
def model(dialog,
          #finv_vlay, vfunc_fp, #need to 
          ):
    
    model = Model_emulator(logger=dialog.logger)
    dialog.add_model(model)
    return model
    
    
#===============================================================================
# tests---
#===============================================================================

#@pytest.mark.parametrize("projDB_fp", [oj_dModel('test_04_save_c1-0-cf1_tut_07e00a', 'projDB.canflood2')])
@pytest.mark.parametrize(*DM_save_args)
def test_core_01_init(model,
                      tutorial_name, #ddummy for args
                      ):
    """simple init test"""
    assert isinstance(model.parent, Main_dialog_projDB) 
    print(model.get_index_d())



@pytest.mark.parametrize(*DM_save_args)
def test_core_02_table_impacts_to_db(model,
                     tutorial_name, #dont really need this
                     test_name,
                     ):
    """call the _table_impacts_to_db"""
     
    model._table_impacts_to_db()
    
    write_projDB(model, test_name)
    

 

@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_01', oj('02_table_impacts_to_db_cf_762fde', 'projDB.canflood2')),
    ('cf1_tutorial_02', oj('02_table_impacts_to_db_cf_b1d2b5', 'projDB.canflood2')),
    ('cf1_tutorial_02d', oj('02_table_impacts_to_db_cf_f6190b', 'projDB.canflood2')),
     ])
def test_core_03_table_impacts_prob_to_db(model,
                     tutorial_name, #dont really need this
                     test_name,
                     ):
    """call the _table_impacts_to_db"""
     
    model._table_impacts_prob_to_db()
    
    write_projDB(model, test_name)
    









@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_01', oj('03_table_impacts_prob_to__6264a6', 'projDB.canflood2')),
    ('cf1_tutorial_02', oj('03_table_impacts_prob_to__2ca9c8', 'projDB.canflood2')),
    ('cf1_tutorial_02d', oj('03_table_impacts_prob_to__3f9cf6', 'projDB.canflood2')),
]
)
def test_core_04_table_ead_to_db(model,
                     tutorial_name, #dont really need this
                     test_name,
                     ):
    """call the _table_ead_to_db"""
     
    model._table_ead_to_db()
    
    write_projDB(model, test_name)
    
    








@pytest.mark.dev
@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_01', oj('04_table_ead_to_db_cf1_tu_266f37', 'projDB.canflood2')),
    #('cf1_tutorial_02', oj('04_table_ead_to_db_cf1_tu_72b058', 'projDB.canflood2')),
    #('cf1_tutorial_02d', oj('04_table_ead_to_db_cf1_tu_116847', 'projDB.canflood2')),
])
@pytest.mark.parametrize("ead_lowPtail, ead_highPtail, ead_lowPtail_user, ead_highPtail_user", [
    (None, None, None, None), #pull from parameters
    ('none', 'none', None, None),
    ('extrapolate', 'extrapolate', None, None),
    ('flat', 'none', None, None),
    ('user', 'user', None, None),
    ('user', 'user', 1e10, 0.5),
    #('flat', 'none', None, None), #not implemented
])
def test_core_05_set_ead_total(model,
                     tutorial_name, #dont really need this
                     test_name,
                     ead_lowPtail, ead_highPtail,
                     ead_lowPtail_user, ead_highPtail_user
                     ):
    """call the _table_ead_to_db"""
     
    model._set_ead_total(ead_lowPtail=ead_lowPtail, ead_highPtail=ead_highPtail,
                         ead_lowPtail_user=ead_lowPtail_user, ead_highPtail_user=ead_highPtail_user,
                         )
    
    #write_projDB(model, test_name)
