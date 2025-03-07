'''
Created on Mar 6, 2025

@author: cef
'''


import pytest
 
from PyQt5.QtWidgets import QWidget
from canflood2.core import Model



@pytest.fixture
def model(logger):
    model = Model(logger=logger)
    return model
    