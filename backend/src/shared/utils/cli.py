import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_cli_command(*args):
    """Запускает CLI команду (в терминале)"""

    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    stdout_decoded = stdout.decode().strip()
    stderr_decoded = stderr.decode().strip()

    logger.info("[%s exited with %s]", args[0], process.returncode)
    if stdout_decoded:
        logger.info("[stdout]\n%s", stdout_decoded)
    if stderr_decoded:
        logger.error("[stderr]\n%s", stderr_decoded)

    return process.returncode, stdout_decoded, stderr_decoded
