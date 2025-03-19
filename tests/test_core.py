'''
Created on Mar 6, 2025

@author: cef
'''


import pytest, os
 
from PyQt5.QtWidgets import QWidget
from canflood2.core import Model
from canflood2.dialog_main import Main_dialog_projDB

from .test_dialog_model import oj as oj_dialog

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
        
        self.logger.debug('Main_dialog_emulator initiated')
        
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
 
#===============================================================================
# fixtures-------
#===============================================================================
@pytest.fixture
def dialog(logger, projDB_fp):
    """emulate the Main_dialog"""
    assert os.path.exists(projDB_fp)
    dialog = Main_dialog_emulator(logger=logger, projDB_fp=projDB_fp)
    return dialog

@pytest.fixture
def model(dialog,
          #finv_vlay, vfunc_fp, #need to 
          ):
    
    model = Model(logger=dialog.logger)
    dialog.add_model(model)
    return model
    
    
#===============================================================================
# tests---
#===============================================================================
@pytest.mark.dev
@pytest.mark.parametrize("projDB_fp", [oj_dialog('04_compile_c1-0-cf1_tutor_de8ebb', 'projDB.canflood2')])
def test_core_01_init(model):
    """simple init test"""
    assert isinstance(model.parent, Main_dialog_projDB) 
    print(model.get_index_d())



@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02', oj_dialog('04_compile_c1-0-cf1_tutor_de8ebb', 'projDB.canflood2'))
])
def test_core_02_run(model,
                     projDB_fp,
                     tutorial_name, #dont really need this
                     ):
    """call the core run method"""
     
    model.run_model(projDB_fp)
