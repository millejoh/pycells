from cell import Cell, EphemeralCellUnboundError

DEBUG = False

def debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "model object > ")
    if DEBUG:
        print " ".join(msgs)


class ModelObject(object):
    """A thing that holds Cells"""
    def __init__(self, *args, **kwargs):
        # initialize cells based on kwargs
        self._initregistry = {}
        klass = self.__class__
        
        for k,v in kwargs.iteritems():       # for each keyword arg
            if k in klass.__dict__.keys():   # if there's a match in my class
                # normalize the input
                if callable(v):
                    cellinit = {'function': v}
                elif 'keys' in dir(v) and \
                         ('function' in v.keys() or
                          'value' in v.keys()):
                    cellinit = v
                else:
                    cellinit = {'value': v}
                    
                # set the new init in the registry for this cell name; to be
                # read at cell-build time
                self._initregistry[k] = cellinit
                                         
        self._curr = None
        self._time = 0
        self._setqueue = []

        # do initial equalizations
        # XXX: I'm not convinced this is a good way to do this
        debug("INITIAL EQUALIZATIONS START")
        x = None
        for attrib in dir(self):
            try:
                x = getattr(self, attrib)   # just run every attribute...
            except EphemeralCellUnboundError, e:
                debug(attrib, "was an unbound ephemeral")
        debug("INITIAL EQUALIZATIONS END")    

    def set_with_integrity(self, name, value):
        debug(name, "=", str(value), "(with integrity)")
        self._setqueue.append((name, value))
