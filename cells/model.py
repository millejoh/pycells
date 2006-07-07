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
    # default cells for Model, currently partially hidden
    _model_name = cells.makecell(value=None)
    _model_value = cells.makecell(value=None)
    _parent = cells.makecell(value=None)

    __metaclass__ = ModelMetatype

    _initialized = False

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
            self._run_observers(getattr(self, key))

        # and now we're initialized. lock the object down.
        self._initialized = True

    def __getattr__(self, key):
        # shortstop the default cells
        if key in ("model_name", "model_value", "parent"):
            # and if they don't exist in this object
            if key not in dir(self):
                # copy the default over
                debug("copying default", key, "into this Model")
                object.__setattr__(self, key,
                                   object.__getattribute__(self, "_" + key))

        return object.__getattribute__(self, key)

    def __setattr__(self, key, value):
         # always set Cells
        if isinstance(self.__dict__.get(key), Cell):
                object.__setattr__(self, key, value)
        # we can set noncells before init
        elif not self._initialized:     
            if key not in self._noncells: # make sure it's registered, though
                self._noncells.add(key)
            object.__setattr__(self, key, value) # and then set it
        # we can set anything we've not seen, too
        elif key not in self.__dict__.keys():
            object.__setattr__(self, key, value)
        # but the only thing left is non-cells we've seen, which is verboten
        else:
            raise NonCellSetError, "Setting non-cell attributes of models " + \
                  "after init is disallowed"
        
    def _run_observers(self, attribute):
        """Runs each observer in turn. There's some optimization that
        could go on here, if it turns out to be neccessary.
        """
        debug("model running observers -- ", str(len(self._observers)),
              "to test")
        for observer in self._observers:
            observer.run_if_applicable(self, attribute)

    def _buildcell(self, name, *args, **kwargs):
        """Creates a new cell of the appropriate type"""
        debug("Building cell: owner:", str(self))
        debug("                name:", name)
        debug("                args:", str(args))
        debug("              kwargs:", str(kwargs))
        # figure out what type the user wants:
        if kwargs.has_key('type'):
            celltype = kwargs["type"]
        elif kwargs.has_key('rule'):  # it's a rule-cell.
            celltype = cells.RuleCell
        elif kwargs.has_key('value'):     # it's a value-cell
            celltype = cells.InputCell
        else:
            raise Exception("Could not determine target type for cell " +
                            "given owner: " + str(self) +
                            ", name: " + name +
                            ", args:" + str(args) +
                            ", kwargs:" + str(kwargs))
        
        kwargs['name'] = name
        return celltype(self, *args, **kwargs)

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
