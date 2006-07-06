import cells
from cell import Cell, EphemeralCellUnboundError
from cellattr import CellAttr
from observer import Observer, ObserverAttr

DEBUG = False

def debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "model".rjust(cells.DECO_OFFSET) + " > ")
    if DEBUG or cells.DEBUG:
        print " ".join(( str(msg) for msg in msgs))

class ModelMetatype(type):
    def __init__(klass, name, bases, dikt):
        # copy over inherited registries of observers and non-cell attributes
        klass._observernames = set([])
        klass._noncells = set([])
        for cls in bases:
            obsnames = getattr(cls, "_observernames", None)
            noncellnames = getattr(cls, "_noncells", None)
            if obsnames:
                klass._observernames.update(obsnames)
            if noncellnames:
                klass._noncells.update(noncellnames)

        # do some work on various attributes of this class:
        for k,v in dikt.iteritems():
            debug("metaclass inspecting", k)
            if isinstance(v, CellAttr):
                debug("metaclass adding name field to", k)
                v.name = k

            elif isinstance(v, ObserverAttr):
                debug("registering observer", k)
                klass._observernames.add(k)

            else:                       # non-cell, non-observer attrib
                debug("registering noncell", k)
                klass._noncells.add(k)
                
                      
class Model(object):
    __metaclass__ = ModelMetatype

    _initialized = False

    # the default cells in a Model:
    model_name = cells.makecell(value=None)
    model_value = cells.makecell(value=None)
    parent = cells.makecell(value=None)
    
    def __init__(self, *args, **kwargs):
        # initialize cells based on kwargs
        self._initregistry = {}
        klass = self.__class__

        # do automagic overriding:
        for k,v in kwargs.iteritems():       # for each keyword arg
            if k in dir(klass):       # if there's a match in my class
                # normalize the input
                if callable(v):
                    cellinit = {'rule': v}
                elif 'keys' in dir(v) and \
                         ('rule' in v.keys() or
                          'value' in v.keys()):
                    cellinit = v
                else:
                    cellinit = {'value': v}
                    
                # set the new init in the registry for this cell name; to be
                # read at cell-build time
                self._initregistry[k] = cellinit

        # turn the observer name registry into a list of real Observers
        self._observers = []
        for name in self._observernames:
            self._observers.append(getattr(self, name))

        # do initial equalizations
        debug("INITIAL EQUALIZATIONS START")
        for name in dir(self):
            try:
                getattr(self, name) # will run observers by itself
            except EphemeralCellUnboundError, e:
                debug(name, "was an unbound ephemeral")
        debug("INITIAL EQUALIZATIONS END")

        # run observers on non-cell attributes
        for key in self._noncells:
            self.run_observers(getattr(self, key))

        # and now we're initialized. lock the object down.
        self._initialized = True

        
    def __setattr__(self, key, value):
        if isinstance(self.__dict__.get(key), Cell): # always set Cells
                object.__setattr__(self, key, value)
        elif not self._initialized:     # we can set noncells before init
            if key not in self._noncells: # make sure it's registered, though
                self._noncells.add(key)
            object.__setattr__(self, key, value) # and then set it
        else:
            raise NonCellSetError, "Setting non-cell attributes of models " + \
                  "after init is disallowed"
        
    def set_with_integrity(self, name, value):
        "Explicitly deferred set. Neccessary? I don't think so..."
        debug(name, "=", str(value), "(with integrity)")
        self._setqueue.append((name, value))

    def run_observers(self, attribute):
        """Runs each observer in turn. There's some optimization that
        could go on here, if it turns out to be neccessary.
        """
        debug("model running observers -- ", str(len(self._observers)),
              "to test")
        for observer in self._observers:
            observer.run_if_applicable(self, attribute)

    @classmethod
    def observer(klass, attrib=None, oldvalue=None, newvalue=None):
        def observer_decorator(func):
            klass._observernames.add(func.__name__)
            setattr(klass, func.__name__, ObserverAttr(func.__name__, attrib,
                                                       oldvalue, newvalue,
                                                       func))
                                
        return observer_decorator


class NonCellSetError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
