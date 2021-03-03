import importlib


def instantiate_class(class_name, *args, **kwargs):
    module_name, class_name = class_name.rsplit(".", 1)
    ClassObject = getattr(importlib.import_module(module_name), class_name)
    return ClassObject(*args, **kwargs)
