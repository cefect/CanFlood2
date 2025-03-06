'''
Created on Mar 4, 2025

@author: cef
'''
import os
from datetime import datetime

#===============================================================================
# directories and files
#===============================================================================
src_dir = os.path.dirname(os.path.dirname(__file__))
plugin_dir = os.path.dirname(__file__)
home_dir = os.path.join(os.path.expanduser('~'), 'CanFlood2')

#===============================================================================
# logging
#===============================================================================

log_format_str =  "%(levelname)s.%(name)s.%(asctime)s:  %(message)s"



#===============================================================================
# autos
#===============================================================================
today_str = datetime.now().strftime("%Y%m%d")
