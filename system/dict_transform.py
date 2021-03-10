class _PathNotFound:
    pass


path_not_found = _PathNotFound()


def get_path(d, path, default=path_not_found):
    c = d
    for k in path:
        c = c.get(k, default)
        if c == default:
            break

    return c


def update(d, path, value):
    c = d
    for k in path[:-1]:
        c = c[k]
    c[path[-1]] = value
    return d


def assoc(d, path, kvs):
    c = d
    for k in path[:-1]:
        c = c[k]

    if not (isinstance(c, dict) or isinstance(c, list)):
        raise KeyError("assoc_state path does not point to a dictionary or list.")

    c[path[-1]] = dict(c[path[-1]], **kvs)
    return d
