"""
Holds a reference to the application config module.

Author: Tal Eisenberg, 2022
"""
import importlib
import sys
import traceback


_config = None


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
        _config = importlib.import_module(f"config.{config_name}")
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    return _config
