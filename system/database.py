"""
Communicate with TimescaleDB databases. 
This module requires the psycopg2 library. psycopg2 is an optional dependency, and only 
necessary when database communication is required.

The module tries to make a default connection to a localhost 
"""
try:
    import psycopg2
except Exception:
    print("WARNING: Can't load psycopg2 library. Database logging will not be available.")


class DatabaseException(Exception):
    pass


def make_connection(user, host, port, db):
    return psycopg2.connect(
        f"dbname='{db}' user='{user}' host='{host}' port='{port}'"
    )


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
    - cur: A psycopg cursor    
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
    cols = ", ".join([col_name + " " + data_type for col_name, data_type in columns])
    exists = "if not exists" if if_not_exists else ""
    query = f"create table {exists} {name}({cols});"
    cur.execute(query)


def create_hypertable(cur, name, columns, time_column_name, if_not_exists=False):
    create_table(cur, name, columns, if_not_exists)
    exists = "TRUE" if if_not_exists else "FALSE"
    cur.execute(
        f"select create_hypertable('{name}', '{time_column_name}', if_not_exists => {exists});"
    )


def drop_table(cur, name):
    cur.execute(f"drop table {name};")


def insert_row(cur, table_name, col_names, data, time_col=None):
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
    with con.cursor() as c:
        try:
            ret = f(c, *args, **kwargs)
        finally:
            con.commit()

        return ret
