#===============================================================================
# """auto update tab figures using pytest
# 
# could integreate this into the sphinx builder conf.py at some point.. but that seems overkill
# 
# This is a per-project script that should be shared with git tracking
# 
# needs to be run from the project pygis venv. eg:
# 
#     start cmd.exe /k python -m pytest --maxfail=10 %TEST_DIR% -c %SRC_DIR%\tests\pytest.ini
# 
# """
#===============================================================================


import pytest
import os
from PyQt5.QtWidgets import QTabWidget, QToolBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt

from tests.conftest import *
from tests.test_01_dialog_main import dialog_loaded, dialog_main, oj
from tests.test_02_dialog_model import oj as oj_model
from tests.test_02_dialog_model import dialog_model, model 


from canflood2.parameters import src_dir


def _write_dialog_screenshot(dialog, output_image):
    # Adjust the dialog size to fit its contents and render it to a QPixmap.
    #dialog.adjustSize()
    pixmap = QPixmap(dialog.size())
    dialog.render(pixmap)
    
# Save the rendered screenshot as a PNG.
    output_dir = os.path.join(src_dir, 'docs', 'source', 'assets') # Directory for saving images
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_image)
    pixmap.save(output_path)
    
    dialog.close()
    
    return output_path




def _write_tab_figure(dialog, output_image, tab_widget_name):
    tab_widget = dialog.findChild(QTabWidget)
    if not tab_widget:
        raise AssertionError("QTabWidget not found in the dialog.")
# Find the desired tab by its widget's objectName
    target_index = None
    for i in range(tab_widget.count()):
        child_widget = tab_widget.widget(i)
        if child_widget.objectName() == tab_widget_name:
            target_index = i
            tab_widget.setCurrentIndex(i)
            break
 
    if target_index is None:
        raise AssertionError(f"Tab with objectName '{tab_widget_name}' not found in the QTabWidget.")
    
    output_path = _write_dialog_screenshot(dialog, output_image)
    





def _write_toolbox_figure(dialog, output_image, page_name):
    # Find the QToolBox that is a direct child of the dialog.
    toolbox = dialog.findChild(QToolBox)
    if not toolbox:
        raise AssertionError("QToolBox not found in the dialog.")

    # Iterate through the toolbox pages and select the one with the matching objectName.
    target_index = None
    for i in range(toolbox.count()):
        child_widget = toolbox.widget(i)
        if child_widget.objectName() == page_name:
            target_index = i
            toolbox.setCurrentIndex(i)
            break

    if target_index is None:
        raise AssertionError(f"Page with objectName '{page_name}' not found in the QToolBox.")

    output_path = _write_dialog_screenshot(dialog, output_image)
    
    print(f"Screenshot of page '{page_name}' saved to {output_path}") # Close the dialog after taking the screenshot.



    

@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02',oj_model('test_05_run_c1-0-cf1_tuto_3fc21f', 'projDB.canflood2'))
     ])
@pytest.mark.parametrize('output_image, tab_widget_name', [
    ('01-dialog-welcome.png', 'tab_01_welcome'),
    ('02-dialog-projectSetup.PNG', 'tab_02_PS'),
    ('03-dialog-hazard.PNG', 'tab_03_HZ'),
    ('04-dialog-modelSuite.PNG', 'tab_04_MS'),
    ('05-dialog-results.PNG', 'tab_05_R'),
 
], indirect=False)
def test_capture_tab_screenshot(dialog_loaded, 
                                output_image, tab_widget_name):
    """
    Capture a screenshot of a specific tab in a PyQt5 QDialog and save it as a PNG.

    Parameters:
        dialog (QDialog): The dialog object provided by pytest-qgis.
        output_image (str): Name of the output PNG file.
        tab_widget_name (str): Object name of the tab to capture.
    """

    dialog = dialog_loaded
    # Ensure the dialog is loaded and find the QTabWidget
    _write_tab_figure(dialog, output_image, tab_widget_name)





 
@pytest.mark.dev
@pytest.mark.parametrize("tutorial_name, projDB_fp", [
    ('cf1_tutorial_02',oj_model('test_05_run_c1-0-cf1_tuto_3fc21f', 'projDB.canflood2'))
     ])
@pytest.mark.parametrize('output_image, page_widget_name', [
    ('06-dialog-MC-AssetInventory.png', 'page_01_AI'),
    ('07-dialog-MC-Vulnerability.PNG', 'page_02_Vuln'),
    ('08-dialog-MC-Exposure.PNG', 'page_03_Exp'),
    ('09-dialog-MC-Risk.PNG', 'page_04_Risk'), 
], indirect=False)
@pytest.mark.parametrize("consequence_category, modelid", (['c1', 0],))
def test_capture_tab_screenshot_model(dialog_model, 
                                output_image, page_widget_name):
    """
    Capture a screenshot of a specific tab in a PyQt5 QDialog and save it as a PNG.

    Parameters:
        dialog (QDialog): The dialog object provided by pytest-qgis.
        output_image (str): Name of the output PNG file.
        tab_widget_name (str): Object name of the tab to capture.
    """

    dialog = dialog_model
    # Ensure the dialog is loaded and find the QTabWidget
    _write_toolbox_figure(dialog, output_image, page_widget_name)
    
    
    
    
    
    