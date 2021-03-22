from collections import Sequence


class _PathNotFound:
    pass


path_not_found = _PathNotFound()


def getitem(d, path, default=path_not_found):
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

    
setitem = _path_element_fn(_setitem_coll)
update = _path_coll_fn(lambda c, kvs: c.update(kvs))
delete = _path_element_fn(lambda c, k: c.pop(k))
remove = _path_coll_fn(_remove_coll)
append = _path_coll_fn(lambda c, v: c.append(v))
exists = _path_element_fn(_exists_coll, return_from_fn=True)
contains = _path_coll_fn(lambda c, k: k in c, return_from_fn=True)
