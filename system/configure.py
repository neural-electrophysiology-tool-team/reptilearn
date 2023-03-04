"""
Holds a reference to the application config module.

Author: Tal Eisenberg, 2022
"""
import importlib
import sys
import traceback
from types import ModuleType


_default_config_name = "config"

_config = None


def add_defaults(config, defaults):
    for (k, v) in defaults.items():
        if k not in config.__dict__:
            setattr(config, k, v)
        elif type(v) is dict:
            # add defaults inside a dictionary attribute
            for dk, dv in v.items():
                if dk not in config.__dict__[k]:
                    config.__dict__[k][dk] = dv

    return config


def get_config():
    """
    Return the global config module
    """
    return _config


def load_config(config_name):
    """
    Loads a config module from config.<config_name> (the config module must reside in
    the config subdirectory). For example, load_config("my_config") will load the config
    module at ./config/my_config.py.

    Return the new global config module. get_config() can be used to obtain the
    config module again.
    """
    global _config

    try:
        default_config = importlib.import_module(f"config.{_default_config_name}")
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    def is_config_attr(k, v):
        return (
            not k.startswith("__")
            and not isinstance(v, ModuleType)
            and not isinstance(v, type)
        )

    default_attrs = {
        k: v for (k, v) in default_config.__dict__.items() if is_config_attr(k, v)
    }

    try:
        _config = importlib.import_module(f"config.{config_name}")
        _config = add_defaults(_config, default_attrs)
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    return _config
