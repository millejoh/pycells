import cells
from cells import Cell

DEBUG = False

def debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "    observer > ")
    if DEBUG or cells.DEBUG:
        print " ".join(msgs)

# we want observers to be defined at the class level but have per-instance
# information. So, do the same trick as is done with CellAttr/Cells
class ObserverAttr(object):
    def __init__(self, name, *args, **kwargs):
        self.name, self.args, self.kwargs = name, args, kwargs

    def __get__(self, owner, ownertype):
        if not owner: return self
        # if there isn't a value in owner.myname, make it an observer
        debug("got request for observer", self.name,
              "args =", str(self.args),
              "kwargs =", str(self.kwargs))
        if self.name not in owner.__dict__.keys():
            owner.__dict__[self.name] = Observer(owner, *self.args,
                                                 **self.kwargs)
        return owner.__dict__[self.name]

class Observer(object):
    "Watch."
    def __init__(self, owner, attrib, oldvalue, newvalue, func):
        self.owner = owner
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
