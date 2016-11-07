import asyncio

from asynciojobs import AbstractJob

# to be added to other ssh-based jobs in apssh or elsewhere

# xxx would make sense to
# (*) add support for commands in addition to command
# (*) come up with a specific exception class for when
# shell comands (local or remote for that matter) exit != 0

class LocalJob(AbstractJob):
    """
    A class that can be used in a asynciojobs Engine
    to run a command locally
    no support for commands yet though

    The regular behaviour is to tear down running process when
    co_shutdown is called. However this can be by-passed 
    by setting eternal = True

    """
    def __init__(self, command, eternal=False, *args, **kwds):
        self.command = command
        self.eternal = eternal
        # implementation
        self._proc = None
        self._exitcode = None
        AbstractJob.__init__(self, *args, **kwds)

    async def co_run(self):
        print("LocalJob is starting command {}".format(self.command))
        self._proc = await asyncio.create_subprocess_shell(self.command)
        self._exitcode = await self._proc.wait()
        print("LocalJob command {} returned {}"
              .format(self.command, self._exitcode))
        self._proc = None
        if self._exitcode != 0:
            raise Exception("command {} returned {}"
                            .format(self.command, self._exitcode))

    async def co_shutdown(self):
        if self._proc:
            if self.eternal:
                print("eternal LocalJob instance is kept running")
            else:
                print("LocalJob is terminating {}".format(self.command))
                self._proc.terminate()
                self._proc = None
