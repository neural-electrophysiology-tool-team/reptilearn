import arena


def lights_on(log):
    log.info("Turning lights on")
    arena.run_command("set", "AC Line 2", [1])


def lights_off(log):
    log.info("Turning lights off")
    arena.run_command("set", "AC Line 2", [0])


def heat_on(log):
    log.info("Turning heat on")
    arena.run_command("set", "AC Line 1", [1])


def heat_off(log):
    log.info("Turning heat off")
    arena.run_command("set", "AC Line 1", [0])
