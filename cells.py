#!/usr/bin/env python
 
#-----------------------------
# PyCells: First draft
#-----------------------------
# License forthcoming...
#-----------------------------

DEBUG = True

def debug(*msgs):
    if DEBUG:
        print " ".join(msgs)

def makecell(initarg, initform):
    """Standard cell attribute factory"""
    return CellAttr(name=initarg, function=initform)
# TODO: make a decorator version of the above

class Cell(object):
    """The actual Cell. Does everything interesting.

    TODO: Write a better description
    """
    def __init__(self, name, function):
        self.name = name
        self.function = function
        self.value = None
        self.called_by = set([])     # the cells which call this cell
        self.calls = set([])         # the cells which this cell calls
        self.time = None

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
            self.value = value
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

    def getcell(self, owner):
        # if there isn't a value in owner.myname, make it a cell
        print "--> got request for cell in", self.name
        if self.name not in owner.__dict__.keys():
            owner.__dict__[self.name] = Cell(self.name, *self.args, **self.kwargs)

        return owner.__dict__[self.name]
        
    def __get__(self, owner, ownertype):
        if not owner: return self
        # return the value in owner.myname
        return self.getcell(owner).get(owner)

    def __set__(self, owner, value):        
        cell = self.getcell(owner)      # get the cell in owner.myname        
        cell.set(owner, value)                 # push a value into it

        
class ModelObject(object):
    """A thing that holds Cells"""
    def __init__(self, *args, **kwargs):
        self._curr = None
        self._time = 0
