'''
Created on Mar 5, 2025

@author: cef

helper functions for qt
'''
import pandas as pd
import numpy as np

from PyQt5.QtWidgets import (
    QFormLayout, QWidgetItem, QLabel, QLineEdit, QComboBox,
    QTableWidget, QWidget, QDoubleSpinBox, QSpinBox, QCheckBox, QDateEdit,
    QFileDialog
    )

from qgis.PyQt import QtWidgets
#from PyQt5.QtCore import QObject


def get_widget_value(widget):
    """Handles common widget types to extract their value."""
    if isinstance(widget, QLineEdit):
        return widget.text()
    elif isinstance(widget, QLabel):
        return widget.text()
    elif isinstance(widget, QComboBox):
        return widget.currentText() 
    elif isinstance(widget, QLabel):
        return widget.text()
    elif isinstance(widget, QDoubleSpinBox):
        return widget.value()
    elif isinstance(widget, QSpinBox):
        return widget.value()
    elif isinstance(widget, QCheckBox):
        return widget.isChecked()
    elif isinstance(widget, QDateEdit):
        return widget.date().toPyDate()
    
    else:
        raise NotImplementedError(type(widget))
    

def set_widget_value(widget, value):
    """Sets the value of a widget based on its type.

    Args:
        widget: The PyQt5 widget to set the value on.
        value: The value to set on the widget.

    Raises:
        TypeError: If the widget type is unsupported.
    """

    if isinstance(widget, QLineEdit):
        widget.setText(str(value))  # Ensure value is a string for LineEdit
    
    elif isinstance(widget, QLabel):
        widget.setText(str(value))  # Ensure value is a string for LineEdit
    elif isinstance(widget, QDoubleSpinBox):
        widget.setValue(float(value))
    elif isinstance(widget, QSpinBox):
        widget.setValue(int(value))
    elif isinstance(widget, QComboBox):
        if isinstance(value, str):
            index = widget.findText(value)
            if index != -1:  # Value found in ComboBox
                widget.setCurrentIndex(index)
            else:
                raise KeyError(f'requested value (\'{value}\') not in comboBox')
        elif isinstance(value, int):
            widget.setCurrentIndex(value)
        else:
            raise NotImplementedError(type(value))
    elif isinstance(widget, QCheckBox):
        widget.setChecked(bool(value))
    else:
        raise TypeError(f"Unsupported widget type: {type(widget)}")


def assert_string_in_combobox(combo_box: QComboBox, target_string: str):
    """
    Asserts that the given string is present as an item in the specified ComboBox.

    Args:
        combo_box: The QComboBox to check.
        target_string: The string to search for within the ComboBox items.
    """

    for index in range(combo_box.count()):
        if combo_box.itemText(index) == target_string:
            return  # Assertion passes if the string is found

    raise AssertionError(f"String '{target_string}' not found in ComboBox items")


class DialogQtBasic():
    """generic dialog methods"""
    
            
    def _get_child(self, childName, childType=QtWidgets.QPushButton):
        child = self.findChild(childType, childName)
        assert not child is None, f'failed to get {childName} of type \'{childType}\''
        return child
    
    def _change_tab(self, tabObjectName): #try to switch the tab on the gui
        try:
            tabw = self.tabWidget
            index = tabw.indexOf(tabw.findChild(QWidget, tabObjectName))
            assert index > 0, 'failed to find index?'
            tabw.setCurrentIndex(index)
        except Exception as e:
            raise IOError(f'bad tabname \'{tabObjectName}\'')
            self.logger.error(f'failed to change to {tabObjectName} tab w/ \n    %s' % e)