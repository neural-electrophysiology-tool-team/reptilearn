"""
Communicate with TimescaleDB databases.
This module requires the psycopg2 library. psycopg2 is an optional dependency, and only
necessary when database communication is required.

The module tries to make a default connection to a localhost
"""
try:
    import psycopg2
except Exception:
    print(
        "WARNING: Can't load psycopg2 library. Database logging will not be available."
    )


class DatabaseException(Exception):
    pass


def make_connection(user, host, port, db):
    return psycopg2.connect(f"dbname='{db}' user='{user}' host='{host}' port='{port}'")


def list_tables(cur):
    """
    Return a list of all public tables in the database.

    Args:
    - cur: A psycopg cursor
    """
    query = """
        select table_name
        from information_schema.tables
        where table_schema = 'public'
        order by table_name;
        """
    cur.execute(query)
    return cur.fetchall()


def list_hypertables(cur):
    """
    Return a list of all TimescaleDB hypertables in the database.

    Args:
    - cur: A psycopg cursor
    """
    query = """
        select table_name
        from _timescaledb_catalog.hypertable
        order by table_name;
        """
    cur.execute(query)
    return cur.fetchall()


def list_columns(cur, table_name):
    """
    Return a list of table columns (a list of tuples: (name, type))

    Args:
    - cur: A psycopg Cursor
    - table_name: A database table name (str)
    """
    query = f"""
        select column_name, data_type
        from INFORMATION_SCHEMA.COLUMNS
        where table_name = '{table_name}'
        """
    cur.execute(query)
    return cur.fetchall()


def create_table(cur, name, columns, if_not_exists=False):
    """
    Create a database table.

    Args:
    - cur: A psycopg Cursor
    - name: The name of the new table
    - columns: a list of tuples representing table columns. Each tuple has two elements -
               column name, and sql data type.
    - if_not_exists: When True, do not throw an error if a relation with the same name already exists.
    """
    cols = ", ".join([col_name + " " + data_type for col_name, data_type in columns])
    exists = "if not exists" if if_not_exists else ""
    query = f"create table {exists} {name}({cols});"
    cur.execute(query)


def create_hypertable(cur, name, columns, time_column_name, if_not_exists=False):
    """
    Create a TimescaleDB hypertable.

    Args:
    - cur: A psycopg Cursor
    - name: The name of the new table
    - columns: a list of tuples representing table columns. Each tuple has two elements -
               column name, and sql data type. One of the columns must be a time column of type timestamptz.
    - time_column_name: The name of the column that will hold time values.
    - if_not_exists: When True, do not throw an error if a relation with the same name already exists.
    """
    create_table(cur, name, columns, if_not_exists)
    exists = "TRUE" if if_not_exists else "FALSE"
    cur.execute(
        f"select create_hypertable('{name}', '{time_column_name}', if_not_exists => {exists});"
    )


def drop_table(cur, name):
    """
    Drop (delete) a table

    Args:
    - cur: A psycopg Cursor
    - name: The table name
    """
    cur.execute(f"drop table {name};")


def insert_row(cur, table_name, col_names, data, time_col=None):
    """
    Write data to a new row according to the specified column names. One
    of the columns must be a time column. The time data should be in seconds since epoch (see
    python time module).

    Args:
    - cur: A psycopg Cursor.
    - table_name: The row will be added to the table with this name.
    - col_names: A sequence of column names. Should be the same length as data
    - data: A sequence containing the row data. Each element is written to a single column
            according to the col_names argument.
    - time_col: The name of the column containing time values.
    """
    values = [
        "%s" if time_col is None or col != time_col else "to_timestamp(%s)"
        for col in col_names
    ]
    query = f"""
        insert into {table_name} ({", ".join(col_names)})
        values ({", ".join(values)});
        """
    cur.execute(query, tuple(data))


def with_commit(con, f, *args, **kwargs):
    """
    Call function f and then commit any transaction to the database.

    Args:
    - con: A psycopg database connection (obtained thru make_connection, for example)
    - f: The function to call before commiting. This usually executes some SQL queries.

    Any additional arguments (positional or named) will be passed to f.
    """
    with con.cursor() as c:
        try:
            ret = f(c, *args, **kwargs)
        finally:
            con.commit()

        return ret
