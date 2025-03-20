'''
Created on Mar 6, 2025

@author: cef
'''


import pytest, os, shutil
 
from PyQt5.QtWidgets import QWidget
from canflood2.core import Model
from canflood2.dialog_main import Main_dialog_projDB

from .test_dialog_model import oj as oj_dModel

import tests.conftest as conftest
from .conftest import (
    conftest_logger, 
    result_write_filename_prep, click
    )


#===============================================================================
# DATA--------
#===============================================================================
test_data_dir = os.path.join(conftest.test_data_dir, 'test_core')
os.makedirs(test_data_dir, exist_ok=True)



#===============================================================================
# helpers
#===============================================================================

overwrite_testdata=True
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

class Main_dialog_emulator(Main_dialog_projDB):
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

@pytest.mark.parametrize("projDB_fp", [oj_dModel('04_compile_c1-0-cf1_tutor_de8ebb', 'projDB.canflood2')])
def test_core_01_init(model):
    """simple init test"""
    assert isinstance(model.parent, Main_dialog_projDB) 
    print(model.get_index_d())



@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02', oj_dModel('04_compile_c1-0-cf1_tutor_de8ebb', 'projDB.canflood2'))
])
def test_core_02_table_impacts_to_db(model,
                     tutorial_name, #dont really need this
                     test_name,
                     ):
    """call the _table_impacts_to_db"""
     
    model._table_impacts_to_db()
    
    write_projDB(model, test_name)
    
    
    
@pytest.mark.dev
@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02', oj('02_table_impacts_to_db_cf_645f61', 'projDB.canflood2'))
])
def test_core_02_table_impacts_simple_to_db(model,
                     tutorial_name, #dont really need this
                     test_name,
                     ):
    """call the _table_impacts_to_db"""
     
    model._table_impacts_simple_to_db()
    
    write_projDB(model, test_name)
    
    
    
    
    
    
