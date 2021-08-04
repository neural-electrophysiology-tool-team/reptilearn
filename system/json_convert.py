from pathlib import Path
import datetime


def json_convert(v):
    """
    conversion for various datatypes that are not supported by the json module.
    """
    if hasattr(v, "tolist"):
        return v.tolist()
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, datetime.datetime):
        return v.isoformat()

    raise TypeError(v)
