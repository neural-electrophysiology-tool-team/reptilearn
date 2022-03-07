try:
    import psycopg2
except Exception:
    print("WARNING: Can't load psycopg2 library.")


class DatabaseException(Exception):
    pass


def make_connection(host="127.0.0.1", port=5432, db="reptilearn"):
    return psycopg2.connect(
        f"dbname='{db}' user='postgres' host='{host}' port='{port}'"
    )


def list_tables(cur):
    query = """
        select table_name
        from information_schema.tables
        where table_schema = 'public'
        order by table_name;
        """
    cur.execute(query)
    return cur.fetchall()


def list_hypertables(cur):
    query = """
        select table_name
        from _timescaledb_catalog.hypertable
        order by table_name;
        """
    cur.execute(query)
    return cur.fetchall()


def list_columns(cur, table_name):
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


try:
    import psycopg2

    con = make_connection()
except Exception:
    pass


def with_commit(con, f, *args, **kwargs):
    with con.cursor() as c:
        try:
            ret = f(c, *args, **kwargs)
        finally:
            con.commit()

        return ret
