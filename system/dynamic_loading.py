import importlib
from pathlib import Path
import inspect


def instantiate_class(class_name, *args, **kwargs):
    module_name, class_name = class_name.rsplit(".", 1)
    ClassObject = getattr(importlib.import_module(module_name), class_name)
    return ClassObject(*args, **kwargs)


def load_module(path: Path, package=None):
    name = package + "." + path.stem if package else path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, spec


def reload_module(spec):
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_subclass(module, parent):
    classes = inspect.getmembers(module, inspect.isclass)
    for name, c in classes:
        if issubclass(c, parent):
            return c
    return None


def load_modules(modules_dir, logger=None):
    modules = {}
    module_pys = modules_dir.glob("*.py")

    for py in module_pys:
        try:
            module, spec = load_module(py, package=modules_dir.stem)
            modules[py.stem] = module, spec
        except Exception:
            if logger:
                logger.exception("While loading modules:")

    return modules
