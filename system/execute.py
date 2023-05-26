from subprocess import STDOUT, Popen, PIPE


def execute(command, cwd=None, shell=False, logger=None):
    """
    Run external program as a subprocess and return its output

    Args:
    - command: (str) the command that will be executed.
    - cwd: Current working directory. cwd argument for subprocess.Popen
    - shell: Execute through a shell. shell argument for subprocess.Popen
    - logger: A logging.Logger to send output to.

    Return the command output.
    """
    process = Popen(
        command,
        shell=shell,
        cwd=cwd,
        stdout=PIPE,
        stderr=STDOUT,
    )
    output = ""

    # Poll process for new output until finished
    for line in process.stdout:
        if line:
            if isinstance(line, bytes):
                line = line.decode()
            line = line.rstrip()

            if logger:
                logger.info(line)

            if len(output) > 0:
                output += "\n" + line
            else:
                output = line

    process.wait()

    if process.returncode == 0:
        return output
    else:
        raise Exception(command, process.returncode, output)
