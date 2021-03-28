import psycopg2


class DatabaseException(Exception):
    pass


def make_connection(host="127.0.0.1", port=5432, db="reptilearn"):
    return psycopg2.connect(
        f"dbname='{db}' user='postgres' host='{host}' port='{port}'"
    )


def list_tables(cur):
    query = (
        """
        select table_name
        from information_schema.tables
        where table_schema = 'public'
        order by table_name;
        """
    )
    cur.execute(query)
    return cur.fetchall()


def list_hypertables(cur):
    query = (
        """
        select table_name
        from _timescaledb_catalog.hypertable
        order by table_name;
        """
    )
    cur.execute(query)
    return cur.fetchall()


def list_columns(cur, table_name):
    query = (
        f"""
        select column_name, data_type
        from INFORMATION_SCHEMA.COLUMNS
        where table_name = '{table_name}'
        """
    )
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
    cur.execute(f"select create_hypertable('{name}', '{time_column_name}', if_not_exists => {exists});")


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


con = make_connection()


def with_commit(con, f, *args, **kwargs):
    with con.cursor() as c:
        ret = f(c, *args, **kwargs)
        con.commit()
        return ret


# example usage

bbox_col_names = ("time", "x1", "y1", "x2", "y2", "confidence")
bbox_col_types = ("timestamptz not null",) + ("double precision",) * 5


def create_bbox_table(cur):
    create_hypertable(
        cur,
        "bbox_position",
        zip(bbox_col_names, bbox_col_types),
        "time",
    )


def insert_bbox_position(cur, data):
    insert_row(cur, "bbox_position", bbox_col_names, data, time_col="time")


def example():
    import time

    with_commit(create_bbox_table)

    data = (time.time(), 500, 300, 550, 350, 0.9)
    with_commit(insert_bbox_position, data)


######
