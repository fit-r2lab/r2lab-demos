import asyncio

from asynciojobs import AbstractJob

# to be added to other ssh-based jobs in apssh or elsewhere

class LocalJob(AbstractJob):
    def __init__(self, command, *args, **kwds):
        self.command = command
        self._proc = None
        AbstractJob.__init__(self, *args, **kwds)

    async def co_run(self):
        print("LocalJob is starting command {}".format(self.command))
        self._proc = await asyncio.create_subprocess_shell(self.command)
        self.exitcode = await self._proc.wait()
        self._proc = None

    async def co_shutdown(self):
        if self._proc:
            print("LocalJob is terminating {}".format(self.command))
            self._proc.terminate()
            self._proc = None
