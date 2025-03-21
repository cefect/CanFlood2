'''
Created on Apr. 30, 2024

@author: cef

NOTE: qgis does not have sqlalchemy
'''

import sqlite3
import pandas as pd
 
 

def get_table_names(conn):
    """Retrieves a list of all tables (excluding default tables) from a SQLite database connection.

    Args:
        conn: A connection object to the SQLite database.

    Returns:
        A list of table names (excluding default tables).
    """

    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
    """)
    table_names = [row[0] for row in cursor.fetchall()]
    return table_names
    
def get_columns_names(conn, table_name):
    """Retrieves a list of all columns from a SQLite table.

    Args:
        conn: A connection object to the SQLite database.
        table_name: The name of the table to retrieve columns from.

    Returns:
        A list of column names.
    """

    cursor = conn.cursor()
    cursor.execute(f"""
        PRAGMA table_info([{table_name}]);
    """)
    column_names = [row[1] for row in cursor.fetchall()]
    return column_names

 


def pd_dtype_to_sqlite_type(dtype):
    """
    Convert a pandas dtype to a SQLite column type.
    SQLite uses a dynamic type system with these primary storage classes:
        NULL. The value is a NULL value.
        
        INTEGER. The value is a signed integer, stored in 0, 1, 2, 3, 4, 6, or 8 bytes depending on the magnitude of the value.
        
        REAL. The value is a floating point value, stored as an 8-byte IEEE floating point number.
        
        TEXT. The value is a text string, stored using the database encoding (UTF-8, UTF-16BE or UTF-16LE).
        
        BLOB. The value is a blob of data, stored exactly as it was input.

    This function maps common pandas dtypes to one of these SQLite types.
    """
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    elif pd.api.types.is_float_dtype(dtype):
        return "REAL"
    elif pd.api.types.is_bool_dtype(dtype):
        # SQLite doesn't have a native Boolean type; typically booleans are stored as integers.
        return "INTEGER"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        # Datetime values are usually stored as ISO8601 strings.
        return "TEXT"
    else:
        # Default to TEXT for object and other types.
        return "TEXT"
