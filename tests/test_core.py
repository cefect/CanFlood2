'''
Created on Mar 6, 2025

@author: cef
'''


import pytest
 
from PyQt5.QtWidgets import QWidget
from canflood2.core import Model

from .test_dialog_model import oj as oj_dialog
#===============================================================================
# helpers
#===============================================================================



@pytest.fixture
def model(logger,
          finv_vlay, vfunc_fp, #need to 
          ):
    model = Model(logger=logger)
    return model
    
    
#===============================================================================
# tests---
#===============================================================================
def test_core_01_init(model):
    assert model.parent is None
    
    print(model.get_index_d())


@pytest.mark.dev
@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02', oj_dialog('02_save_c1-0-cf1_tutorial_04e68f', 'projDB.canflood2'))
])
def test_core_02_run(model,
                     projDB_fp,
                     ):
    """call the core run method"""
    
    model.run_model(projDB_fp)