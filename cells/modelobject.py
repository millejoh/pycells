import cells
from cell import Cell, EphemeralCellUnboundError
from cellattr import CellAttr

DEBUG = False

def debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "model object > ")
    if DEBUG:
        print " ".join(( str(msg) for msg in msgs))


class ModelObject(object):
    def __init__(self, *args, **kwargs):
        # initialize cells based on kwargs
        self._initregistry = {}
        klass = self.__class__
        
        for k,v in kwargs.iteritems():       # for each keyword arg
            if k in klass.__dict__.keys():   # if there's a match in my class
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
                
        # register observers
        self._observers = []
        debug("init'ing observers")
        for attrib_name in dir(self):
            attrib = getattr(self, attrib_name)
            debug(attrib, "?", isinstance(attrib, Observer))
            if isinstance(attrib, Observer):
                self._observers.append(attrib)
        
        self._initialized = False

        # do initial equalizations
        debug("INITIAL EQUALIZATIONS START")
        x = None
        for attrib in dir(self):
            try:
                x = getattr(self, attrib)   # just run every attribute...
            except EphemeralCellUnboundError, e:
                debug(attrib, "was an unbound ephemeral")
        debug("INITIAL EQUALIZATIONS END")

        self._initialized = True

    def __setattr__(self, key, value):
        if (not hasattr(self, "_initialized") or
            isinstance(self.__dict__[key], Cell) or
            not self._initialized):
            object.__setattr__(self, key, value)
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
            setattr(klass, func.__name__, Observer(attrib, oldvalue, newvalue,
                                                   func))
        return observer_decorator


class Observer(object):
    "Watch."
    def __init__(self, attrib, oldvalue, newvalue, func):
        self.attrib_name = attrib
        self.oldvalue = oldvalue
        self.newvalue = newvalue
        self.func = func
        self.last_ran = 0

    def run_if_applicable(self, model, attr):
        debug("running observer", self.func.__name__)
        if self.last_ran == cells.dp:   # never run twice in one DP
            debug(self.func.__name__, "already ran in this dp")
            return
        
        if self.attrib_name:
            if isinstance(attr, Cell):
                if attr.name != self.attrib_name:
                    debug(self.func.__name__, "wants a cell named '" +
                          self.attrib_name + "', got a cell named '" +
                          attr.name + "'")
                    return
            elif getattr(model, self.attrib_name) is not attr:
                debug(self.func.__name__, "looked in its model for an attrib" +
                      "with its desired name; didn't match passed attr.")
                return
            
        if self.newvalue:
            if isinstance(attr, Cell):
                if not self.newvalue(attr.value):
                    debug(self.func.__name__,
                          "function didn't match cell's new value")
                    return
            else:
                if not self.newvalue(attr):
                    debug(self.func.__name__, "function didn't match non-cell")
                    return

        # since this is immediately post-value change, the last_value attr
        # of the cell is still good.
        if self.oldvalue:
            if isinstance(attr, Cell):
                if not self.oldvalue(attr.last_value):
                    debug(self.func.__name__, "function didn't match old value")
                    return

        # if we're here, it passed all the tests, so
        debug(self.func.__name__, "running")
        self.func(model)
        self.last_ran = cells.dp

class NonCellSetError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
