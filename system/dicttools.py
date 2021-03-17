class _PathNotFound:
    pass


path_not_found = _PathNotFound()


def get_path(d, path, default=path_not_found):
    if isinstance(path, str):
        path = (path,)
        
    c = d
    for k in path:
        c = c.get(k, default)
        if c == default:
            break

    return c


def update(d, path, value):
    if isinstance(path, str):
        path = (path,)
    
    c = get_path(d, path[:-1] if len(path) > 0 else ())

    if c is path_not_found:
        raise KeyError(f"update: path {path} does not exist.")

    c[path[-1]] = value
    return d


def assoc(d, path, kvs):
    if isinstance(path, str):
        path = (path,)

    c = get_path(d, path[:-1] if len(path) > 0 else ())

    if c is path_not_found:
        raise KeyError(f"assoc: path {path} does not exist.")

    if not (isinstance(c, dict) or isinstance(c, list)):
        raise KeyError(f"assoc: path {path} does not point to a dictionary or list.")

    if len(path) > 0:
        c[path[-1]] = dict(c[path[-1]], **kvs)
    else:
        for k, v in kvs.items():
            d[k] = v
            
    return d


def remove(d, path):
    if isinstance(path, str):
        path = (path,)

    c = get_path(d, path[:-1])
    if c is path_not_found:
        raise KeyError(f"remove: path {path} does not exist.")
    if not (isinstance(c, dict) or isinstance(c, list)):
        raise KeyError(f"remove: path {path} does not point to a dictionary or list.")

    c.pop(path[-1])
    return d


def contains(d, path, v):
    if isinstance(path, str):
        path = (path,)

    c = get_path(d, path)

    if c is path_not_found:
        raise KeyError(f"contains: path {path} does not exist.")
    if not (isinstance(c, dict) or isinstance(c, list)):
        raise KeyError(f"contains: path {path} does not point to a dictionary or list.")

    return v in c
