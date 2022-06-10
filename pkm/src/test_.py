from pkm.utils.ipc import IPCPackable


class XXX():

    def __init__(self, packable: bool):
        if packable:
            self.__getstate__ = self._getstate
        self.__setstate__ = self._setstate

    def _getstate(self):
        pass

    def _setstate(self, state):
        pass


xxx = XXX(True)
yyy = XXX(False)
print(isinstance(xxx, IPCPackable))
print(isinstance(yyy, IPCPackable))
