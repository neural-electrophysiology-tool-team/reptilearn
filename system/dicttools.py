"""
Functions for querying or mutating values in arbitrarily nested dictionaries and lists.
Author: Tal Eisenberg, 2021

Each of the functions in this module are "path functions" - f(d, path), where d is a
collection, and path is either a string key, an int index, or a tuple representing
a path in the collection. A path's tuple elements are keys for each level in the nested collection
hierarchy, for example:

getitem(d, ("x", "y")) is equivalent to d["x"]["y"].
"""

from collections.abc import Sequence


class _PathNotFound:
    pass


path_not_found = _PathNotFound()


def _path_element_fn(element_fn, return_from_fn=False):
    def fn(d, path, *args, **kwargs):
        if isinstance(path, str):
            path = (path,)
        if len(path) == 0:
            raise KeyError("An empty path was supplied.")

        c = getitem(d, path[:-1])

        if not (isinstance(c, dict) or isinstance(c, list)):
            raise KeyError(f"path {path} does not point to a dictionary or list.")

        ret = element_fn(c, path[-1], *args, **kwargs)
        return ret if return_from_fn else d

    return fn


def _path_coll_fn(dict_fn, return_from_fn=False):
    def fn(d, path, key, *args, **kwargs):
        if isinstance(path, str):
            path = (path,)

        c = getitem(d, path)

        ret = dict_fn(c, key, *args, **kwargs)
        return ret if return_from_fn else d

    return fn


def getitem(d, path, default=path_not_found):
    """
    Return the value of dictionary d at the supplied path.
    When the path doesn't exist in d the default value is returned.
    A default of path_not_found will cause an KeyError to be raised if the path
    doesn't exist.
    """
    if isinstance(path, str):
        path = (path,)

    c = d
    for k in path:
        if isinstance(c, dict):
            c = c.get(k, default)
            if c == default:
                if c is path_not_found:
                    raise KeyError(f"Path {path} does not exist.")
                else:
                    break

        elif isinstance(c, Sequence):
            if type(k) is not int:
                raise KeyError(f"Expecting an integer key {k} for path {path}")
            if k >= len(c):
                if default is path_not_found:
                    raise KeyError(f"Path {path} does not exist.")
                return default
            c = c[k]

    return c


def _setitem_coll(c, k, v):
    c[k] = v


def _exists_coll(c, k):
    if isinstance(c, dict):
        return k in c
    else:
        return len(c) > k


def _remove_coll(c, k):
    if not isinstance(c, list):
        raise KeyError("path does not point to a list.")
    return c.remove(k)


def _update_coll(c, kvs):
    return c.update(kvs)


def _delete(c, k):
    return c.pop(k)


def _append_coll(c, v):
    return c.append(v)


def _contains_coll(c, k):
    return k in c


setitem = _path_element_fn(_setitem_coll)
setitem.__doc__ = """setitem(d, path, v) - Sets path of d to the value v."""

update = _path_coll_fn(_update_coll)
update.__doc__ = """update(d, path, kvs) - Updates a dictionary at path of d with the contents of dict kvs."""

delete = _path_element_fn(_delete)
delete.__doc__ = """delete(d, path) - Deletes the key at path of d, removing it from its container."""

remove = _path_coll_fn(_remove_coll)
remove.__doc__ = (
    """remove(d, path, v) - Removes element v from the list at path of d."""
)

append = _path_coll_fn(_append_coll)
append.__doc__ = """append(d, path, v) - Appends v to the list at path of d."""

exists = _path_element_fn(_exists_coll, return_from_fn=True)
exists.__doc__ = """exists(d, path) - Returns True if path exists in d."""

contains = _path_coll_fn(_contains_coll, return_from_fn=True)
contains.__doc__ = (
    """contains(d, path, v) - Returns True if the container at path contains v"""
)
