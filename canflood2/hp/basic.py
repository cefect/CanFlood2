'''
Created on Mar 8, 2025

@author: cef
'''

import os, logging
import pandas as pd

def sanitize_filename(filename: str,
                      char_max=30) -> str:
    """
    Replace characters that are not allowed in Windows filenames with underscores.

    Parameters:
        filename (str): The original filename string.

    Returns:
        str: The sanitized filename with '[' and '/' replaced by '_'.
    """
    # Replace the characters '[' and '/' with '_'
    for char in ['[',']', '/', '\\', ':']:
        filename = filename.replace(char, '_')
        

        
    return filename


def view_web_df(df):
    if isinstance(df, pd.Series):
        df = pd.DataFrame(df)
    import webbrowser
    #import pandas as pd
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile(delete=False, suffix='.html', mode='w') as f:
        #type(f)
        df.to_html(buf=f)
        
    webbrowser.open(f.name)