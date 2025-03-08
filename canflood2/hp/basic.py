'''
Created on Mar 8, 2025

@author: cef
'''


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