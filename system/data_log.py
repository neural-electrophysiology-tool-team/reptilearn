import csv
from datetime import datetime
from pathlib import Path
import multiprocessing as mp

import rl_logging
import database as db
from video_stream import ImageObserver
import managed_state


class DataLogger(mp.Process):
    """
    An abstract data logger process

    Manages writing to csv files and/or a database (see database.py) but doesn't handle data acquisition.

    Override _get_data and optionally _on_start and _on_stop methods (see methods documentation).
    NOTE: The logger process is terminated once the logger receives a None (i.e. _get_data returns None)
    """

    def __init__(
        self,
        columns,
        csv_path: Path = None,
        split_csv=False,
        log_to_db=True,
        table_name=None,
    ):
        """
        Initialize logger

        Args:
        - columns: a list of ordered column names or a list of tuples (column_name, data_type).
        - csv_path: CSV file path. Set to None if you don't want to write to csv.
        - split_csv: When True the logger will create a new csv file each time it starts
        - log_to_db: Whether to add data to a database table. Requires a non-None table_name when set to True.
        - table_name: The name of a TimescaleDB hypertable to write to. If the table does not exist a new one is created.
        """
        self.table_name = table_name
        self.columns = columns
        self.col_names = [c[0] if type(c) is tuple else c for c in columns]
        self.log_to_db = log_to_db
        if csv_path is not None:
            self.csv_path = csv_path if type(csv_path) is Path else Path(csv_path)
        else:
            self.csv_path = None

        self.split_csv = split_csv
        self.logger = None
        self._logger_configurer = rl_logging._logger_configurer
        super().__init__()

    def _init_log(self):
        self.logger = self._logger_configurer.configure_child(self.name)
        self.logger.debug("Initializing data logger...")
        self.con = None

        if self.log_to_db:
            try:
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
            except NameError:
                self.logger.warning(
                    "Can't load psycopg2 library. Database logging will not be available."
                )
        if self.csv_path is not None:
            if self.split_csv:
                timestamp = datetime.now()
                csv_dir = self.csv_path.parent
                csv_name = self.csv_path.stem
                csv_path = Path(
                    csv_dir
                    / (csv_name + "_" + timestamp.strftime("%Y%m%d-%H%M%S") + ".csv")
                )
            else:
                csv_path = self.csv_path

            appending = csv_path.exists()

            self.csv_file = open(str(csv_path), "a")
            self.csv_writer = csv.writer(self.csv_file, delimiter=",")

            if not appending:
                self.csv_writer.writerow(self.col_names)
                self.csv_file.flush()
        else:
            self.csv_file = None
            self.csv_writer = None

    def _write(self, data):
        if self.con and self.log_to_db and self.table_name is not None:
            import database as db

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
            self.csv_file.flush()

    def run(self):
        self._init_log()
        self._on_start()

        self.logger.debug("Data logger started.")

        while True:
            data = self._get_data()

            if data is None:
                self.logger.debug("Stopping data logger.")
                break
            else:
                self._write(data)

        self._on_stop()
        self._close()

    def _close(self):
        if self.csv_file is not None:
            self.csv_file.close()

        if self.log_to_db and self.con is not None:
            self.con.close()

    def _get_data(self):
        """
        This method should handle getting data into the logger process. In case there's no new data to
        return, it must block until data arrives. Returning None will call _on_stop() and stop the logger process.
        """
        return None

    def _on_start(self):
        """
        Called when the process starts.
        """
        pass

    def _on_stop(self):
        """
        Called when the process stops after _get_data returns None.
        """
        pass


class QueuedDataLogger(DataLogger):
    """
    Data logger that receives data over a queue (multiprocessing.Queue).
    Use the QueuedDataLogger to log data from the process that created it.
    """

    def __init__(
        self,
        columns,
        csv_path: Path = None,
        split_csv=False,
        log_to_db=True,
        table_name=None,
    ):
        """
        Initialize the data logger. See DataLogger.__init__ for more information.
        """

        super().__init__(columns, csv_path, split_csv, log_to_db, table_name)
        self._log_q = mp.Queue()

    def log(self, record):
        """
        Log a single record to csv or database.

        Args:
        - record: any sequence that matches the number of columns defined in __init__
        """
        self._log_q.put(record)

    def stop(self):
        """
        Stops the logger process by sending a None on the queue.
        """
        self._log_q.put(None)

    def _get_data(self):
        try:
            return self._log_q.get()
        except KeyboardInterrupt:
            pass


class ObserverLogger(QueuedDataLogger):
    def __init__(
        self,
        image_observer: ImageObserver,
        columns,
        csv_path: Path = None,
        split_csv=False,
        log_to_db=True,
        table_name=None,
    ):
        super().__init__(columns, csv_path, split_csv, log_to_db, table_name)
        self.obs_communicator = image_observer.get_communicator()
        self.state_address = image_observer.state_store_address
        self.state_authkey = image_observer.state_store_authkey

        self.time_index = None
        for i, c in enumerate(columns):
            if type(c) is tuple:
                c = c[0]

            if c == "time":
                self.time_index = i
                break

        if self.time_index is None:
            raise ValueError("Missing 'time' column in columns argument.")

    def _on_start(self):
        self.state = managed_state.Cursor(
            (), authkey=self.state_authkey, address=self.state_address
        )
        self.remove_listener = self.obs_communicator.add_listener(
            self.on_observer_update, self.state
        )

    def _on_stop(self):
        self.remove_listener()

    def on_observer_update(self, output, timestamp):
        out_list: list = output.tolist()
        out_list.insert(self.time_index, timestamp)
        self.log(out_list)
