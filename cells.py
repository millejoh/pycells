#!/usr/bin/env python
 
#-----------------------------
# PyCells: First draft
#-----------------------------
# License forthcoming...
#-----------------------------

DEBUG = False

def debug(*msgs):
    if DEBUG:
        print " ".join(msgs)

def makecell(name, function=lambda s,p: None):
    """Standard cell attribute factory"""
    return CellAttr(name=name, function=function)

def fun2cell(*args, **kwargs):
    """Decorator version of makecell

    TODO: More here."""
    def fun2cell_decorator(func):
        cellname = kwargs.get('name')
        if not cellname:
            cellname = func.__name__
        return CellAttr(name=cellname, function=func)

    return fun2cell_decorator
    

def observer(klass, cellname):
    """Decorator to add an observer to a cell in a class

    TODO: Explain observers, describe required signature for observing funcs,
    warn that wrapped function is pretty much uncallable
    """
    debug("running observer decorator for", str(klass), cellname)
    def observer_decorator(func):
        klass.__dict__[cellname].observers.append(func)
        
    return observer_decorator
    

class Cell(object):
    """The actual Cell. Does everything interesting.

    TODO: Write a better description
    """
    def __init__(self, name, function=lambda s,p: None, value=None,
                 observers=[]):
        debug("running cell init for", name, "with", str(len(observers)),
              "observers")
        self.name = name
        self.function = function
        self.value = value
        self.observers = observers
        
        self.called_by = set([])     # the cells which call this cell
        self.calls = set([])         # the cells which this cell calls

        self.time = None
        self.bound = False

    def get(self, owner):
        """Special getter for Cell attributes.

        If there's a memoized value, return it directly. If there isn't, this
        is the first time this cell's been run. So, run it, memoize the calc'd
        value, and return that.
        """
        debug(">>> Getting", self.name)

        # first, determine if this cell needs its initial calculation
        if not self.value:
            debug(">>> function for", self.name, "callable?",
                  str(callable(self.function)))

            self.run(owner)

        debug(">>>", self.name, "is", str(self.value))

        if (owner._curr):               # if there's a calling cell,
            # notify calling cell that it depends on this cell
            owner._curr.calls.add(self)
            # and add the calling cell to the called-by list
            self.called_by.add(owner._curr)

        return self.value

    def set(self, owner, value):
        """Special setter for Cell attributes.

        TODO: Describe my behavior
        """
        if self.value != value:
            owner._time += 1
            self.time = owner._time

            debug(">>> Owner time is:", str(owner._time))
            debug(">>> Setting", self.name, "to", str(value))
            debug(">>>", self.name, "calls", \
                  str([ cell.name for cell in self.calls]))
            debug(">>>", self.name, "called by", \
                  str([ cell.name for cell in self.called_by]))

            oldval = self.value         # save for observers
            oldbound = self.bound       # ditto
            self.bound = True
            self.value = value

            # run my observers
            debug(">>> Number of observers:", str(len(self.observers)))
            for observer in self.observers:
                debug(">>> Running observer", str(observer))
                observer(self.value, oldval, oldbound)
            
            self.equalize(owner)

    def run(self, owner):
        """Runs the value-generating function & re-equalizes the subgraph"""
        # update to this time quantum, then run the function
        debug(">>> Owner time is:", str(owner._time))
        self.time = owner._time
        oldval = self.value
        debug(">>>", self.name, "time is:", str(owner._time))

        # set this cell as the currently-running cell
        oldrunner = owner._curr
        owner._curr = self
        
        # note the function is passed the *owner* as the first arg, mimicking
        # standard Foo.bar dispatch
        self.value = self.function(owner, self.value)

        # only rerun dependents if the value changed
        if oldval != self.value:
            self.equalize(owner)

        # now that the subgraph is equalized, restore the old running cell
        owner._curr = oldrunner

    def equalize(self, owner):
        """Brings the subgraph of dependents to equlibrium."""
        debug(">>> Equalizing", self.name)
        
        # re-run the cells which call this cell
        for dependent in self.called_by:
            # only run if the dependent hasn't been run in this quantum
            debug(">>> Dependent:", dependent.name, "at", str(dependent.time))
            if dependent.time < self.time:
                debug(">>> Dependent:", dependent.name, "re-run")
                dependent.run(owner)
        # the subtree is now at equilibrium.


class CellAttr(object):
    """A descriptor for a Cell attribute in a ModelObject"""
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs
        self.observers = []

    def getcell(self, owner):
        # if there isn't a value in owner.myname, make it a cell
        debug("--> got request for cell in", self.name)
        if self.name not in owner.__dict__.keys():
            # first, find out if this object has overrides on this cell's init
            override = owner._initregistry.get(self.name)
            
            if override:               # it does, use the override
                newcell = Cell(self.name, observers=self.observers, **override)
            else:                       # it doesn't, use class's default
                newcell = Cell(self.name, observers=self.observers,
                               *self.args, **self.kwargs)
                
            owner.__dict__[self.name] = newcell

        return owner.__dict__[self.name]
        
    def __get__(self, owner, ownertype):
        if not owner: return self
        # return the value in owner.myname
        return self.getcell(owner).get(owner)

    def __set__(self, owner, value):
        cell = self.getcell(owner)  # get the cell in owner.myname        
        cell.set(owner, value)      # and push a value into it

        
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
