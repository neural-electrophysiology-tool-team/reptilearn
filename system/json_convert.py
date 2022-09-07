"""
Author: Tal Eisenberg, 2021
"""
from pathlib import Path
import datetime


def json_convert(v):
    """
    Convert various datatypes that are not supported by the json module into json-compatible types.
    """
    if hasattr(v, "tolist"):
        return v.tolist()
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, datetime.datetime):
        return v.isoformat()

    raise TypeError(v)
