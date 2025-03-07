'''
Created on Apr. 26, 2024

@author: cef


testing QGIS plugin
    see test_dialog for dialog tests
'''
import pytest, logging, os
from qgis.core import QgsApplication, QgsProject, Qgis, QgsLogger, QgsMessageLog


from canflood2.hp.logr import get_log_stream

print(os.environ.get('PYTHONPATH'))

#from .conftest import mod_logger #needed to connect to QgsMessageLog
 
 

 
 
 
#===============================================================================
# tests --------
#===============================================================================
 
 
 
@pytest.mark.parametrize('qlevel',[Qgis.Info, Qgis.Critical], indirect=False) 
def test_logging(qlevel, qgis_app, logger, test_name):
     
    print(f'print test message')
    logger.info(f'logger.info message')
    log = logger.getChild('testChild')
    log.info(f'child logger.info message')
    QgsMessageLog.logMessage('QgsMessageLog message', 'tabName', level=qlevel)
    
    
    print(f'finished {test_name}\n===========================\n\n')
 
 

 

#===============================================================================
# def test_plugin_loads(qgis_app, qgis_iface, mocker):
#     """Tests if the plugin adds its button to the QGIS interface correctly."""
#     
#     import pytest_mock #required for overriding QGIS settings
#     from canflood2.plugin import Canflood_plugin as Plugin
#     from canflood2.dialog_main import Main_dialog as Dialog
#   
#     mocker.patch('PyQt5.QtCore.QSettings.value', return_value='en_EN') # Corrected import path 
#    
#     plugin = Plugin(iface=qgis_iface)
#     print('plugin init') 
#     plugin.initGui()
#     
#     assert len(plugin.actions) == 1  # Expecting one action 
#     assert plugin.actions[0].text() == "CanFlood2", f'got unexpected string: {plugin.actions[0].text()}'  # Check the action's text
#     
#     
#     # Ensure first_start is True so that the dialog will be created on launch
#     plugin.first_start = True
#     plugin.launch_dialog()
# 
#     # Verify that the dialog was created and is of the correct type.
#     assert hasattr(plugin, 'dlg')
#     assert isinstance(plugin.dlg, Dialog)
#===============================================================================
    
 