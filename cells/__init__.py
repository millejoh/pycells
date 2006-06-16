"""
PyCells

TODO: More here.
"""

from cell import Cell, ValueCell, RuleCell, RuleThenValueCell, EphemeralCell
from cellattr import CellAttr
from modelobject import ModelObject

DEBUG = False

def debug(*msgs):
    if DEBUG:
        print " ".join(msgs)
        
def makecell(name, *args, **kwargs):
    """Standard cell attribute factory"""
    return CellAttr(name=name, *args, **kwargs)

def fun2cell(*args, **kwargs):
    """Decorator version of makecell

    TODO: More here."""
    def fun2cell_decorator(func):        
        if not kwargs.has_key('name'):
            cellname = func.__name__
        else:
            cellname = kwargs.pop('name')
        return CellAttr(name=cellname, function=func, *args, **kwargs)

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
