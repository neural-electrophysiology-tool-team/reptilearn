import arena
from rl_logging import get_main_logger

log = get_main_logger()


def lights_on():
    log.info("Turning lights on")
    arena.run_command("set", "Day lights", [1])


def lights_off():
    log.info("Turning lights off")
    arena.run_command("set", "Day lights", [0])


def IRlights_on(log):
    log.info("Turning IR lights on")
    arena.run_command("set", "Night lights", [1])


def IRlights_off(log):
    log.info("Turning IR lights off")
    arena.run_command("set", "Night lights", [0])


def heat_on():
    log.info("Turning heat on")
    arena.run_command("set", "AC Line 1", [1])


def heat_off():
    log.info("Turning heat off")
    arena.run_command("set", "AC Line 1", [0])
