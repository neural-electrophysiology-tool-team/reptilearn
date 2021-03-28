import csv
from pathlib import Path
import multiprocessing as mp

import database as db
import rl_logging


class DataLogger(mp.Process):
    def __init__(self, columns, csv_path: Path = None, log_to_db=True, table_name=None):
        self.table_name = table_name
        self.columns = columns
        self.col_names = [c[0] if type(c) is tuple else c for c in columns]
        self.log_to_db = log_to_db
        if csv_path is not None:
            self.csv_path = csv_path if type(csv_path) is Path else Path(csv_path)
        else:
            self.csv_path = None

        self.logger = None

        super().__init__()

    def _init_log(self):
        self.logger = rl_logging.logger_configurer(self.name)
        self.logger.debug("Initializing data logger...")

        if self.log_to_db:
            self.con = db.make_connection()
            if self.table_name is not None:
                db.with_commit(
                    self.con,
                    db.create_hypertable,
                    self.table_name,
                    self.columns,
                    "time",
                    if_not_exists=True,
                )

        if self.csv_path is not None:
            ex = self.csv_path.exists()
            self.csv_file = open(str(self.csv_path), "a")
            self.csv_writer = csv.writer(self.csv_file, delimiter=",")
            if not ex:
                self.csv_writer.writerow(self.col_names)
        else:
            self.csv_file = None
            self.csv_writer = None

    def _write(self, data):
        if self.log_to_db is not None and self.table_name is not None:
            try:
                db.with_commit(
                    self.con,
                    db.insert_row,
                    self.table_name,
                    self.col_names,
                    data,
                    "time",
                )
            except Exception:
                self.logger.exception("While inserting row to database:")

        if self.csv_writer is not None:
            self.csv_writer.writerow(data)

    def run(self):
        self._init_log()

        while True:
            data = self._get_data()

            if data is None:
                self.logger.debug("Stopping data logger...")
                break
            else:
                self._write(data)

        self.close()

    def close(self):
        if self.csv_file is not None:
            self.csv_file.close()

        if self.con is not None:
            self.con.close()

    def _get_data(self):
        return None


class QueuedDataLogger(DataLogger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_q = mp.Queue()

    def log(self, item):
        self._log_q.put(item)

    def stop(self):
        self._log_q.put(None)

    def _get_data(self):
        return self._log_q.get()
