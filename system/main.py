"""
Main module. Run this module to start the system.
Author: Tal Eisenberg, 2021

Run 'python main.py -h' for help about command line arguments.
"""

if __name__ == "__main__":
    # We do this to prevent re-initializing the system each time a process is created when using the spawn method.
    import system
