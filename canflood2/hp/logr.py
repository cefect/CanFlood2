'''
Created on Mar. 26, 2020

@author: cefect

usually best to call this before any standard imports
    some modules have auto loggers to the root loger
    calling 'logging.getLogger()' after these configure will erase these
'''
import os, logging, logging.config, pprint, sys
 
 

log_format_str_d = {
    'StreamHandler':"%(asctime)s.%(levelname)s.%(name)s:  %(message)s",
    'FileHandler':  '%(asctime)s.%(levelname)s.%(name)s:  %(message)s',
    }
 


def get_log_stream(name=None, level=None,
                   log_format_str = None,
                   ):
    """get a logger with stream handler"""
    if name is None:
        name = str(os.getpid())
    if level is None:
        level = logging.DEBUG
    if log_format_str is None:
        log_format_str = log_format_str_d['StreamHandler']

            

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # see if it has been configured
    if not logger.handlers:
        
        handler = logging.StreamHandler(
            stream=sys.stdout,  # send to stdout (supports colors)
        )   
        formatter = logging.Formatter(log_format_str, datefmt="%M:%S", validate=True)
        handler.setFormatter(formatter)
        handler.setLevel(level)
        
        logger.addHandler(handler)
    return logger
 
    
def get_new_file_logger(
        logger_name='log',
        level=logging.DEBUG,
        fp=None, #file location to log to
        logger=None,
        ):
    
    #===========================================================================
    # configure the logger
    #===========================================================================
    if logger is None:
        logger = logging.getLogger(logger_name)
        
    
    if level is None:
        level = logging.DEBUG
        
    logger.setLevel(level)
    
    #===========================================================================
    # configure the handler
    #===========================================================================
    assert fp.endswith('.log')
    
    formatter = logging.Formatter(log_format_str_d['FileHandler'], datefmt='%H:%M:%S', validate=True)       
    handler = logging.FileHandler(fp, mode='w') #Create a file handler at the passed filename 
    handler.setFormatter(formatter) #attach teh formater object
    handler.setLevel(level) #set the level of the handler
    
    logger.addHandler(handler) #attach teh handler to the logger
    
    logger.debug('built new file logger  here \n    %s'%(fp))
    
    return logger
    