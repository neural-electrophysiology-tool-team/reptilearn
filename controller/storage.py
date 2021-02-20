import psycopg2


def make_connection(host="127.0.0.1", port=5432, db="reptilearn"):
    return psycopg2.connect(f"dbname='{db}' user='postgres' host='{host}' port='{port}'")


def create_bbox_position_table(conn):
    query_create_table = """
    CREATE TABLE bbox_position (
       time TIMESTAMPTZ NOT NULL,
       x1 DOUBLE PRECISION,
       y1 DOUBLE PRECISION,
       x2 DOUBLE PRECISION,
       y2 DOUBLE PRECISION,
       confidence DOUBLE PRECISION
    );
    """
    query_create_hypertable = "SELECT create_hypertable('bbox_position', 'time');"

    cur = conn.cursor()
    cur.execute(query_create_table)
    cur.execute(query_create_hypertable)
    conn.commit()
    cur.close()


def insert_bbox_position(conn, data):
    cur = conn.cursor()
    try:
        cur.execute("""
        INSERT INTO bbox_position (time, x1, y1, x2, y2, confidence) 
               VALUES (to_timestamp(%s), %s, %s, %s, %s, %s);""", tuple(data))
    except psycopg2.Error as error:
        print(error.pgerror)
    conn.commit()
    cur.close()
