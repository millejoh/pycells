"""
PyCells

TODO: More here.
"""

from cell import Cell, InputCell, RuleCell, RuleThenInputCell, OnceAskedLazyCell
from cell import UntilAskedLazyCell, AlwaysLazyCell
from cell import CellException, RuleCellSetError
from cell import InputCellRunError, SetDuringNotificationError
from cellattr import CellAttr
from modelobject import ModelObject, NonCellSetError

DEBUG = False

def debug(*msgs):
    if DEBUG:
        print " ".join(msgs)

def reset():
    global dp
    global curr
    global curr_propogator
    global queued_updates
    global deferred_sets
    
    dp = 1
    curr = None
    curr_propogator = None
    queued_updates = []
    deferred_sets = []
        
def makecell(name, *args, **kwargs):
    """Standard cell attribute factory"""
    return CellAttr(name, *args, **kwargs)

def fun2cell(*args, **kwargs):
    """Decorator version of makecell

    TODO: More here."""
    def fun2cell_decorator(func):        
        if not kwargs.has_key('name'):
            cellname = func.__name__
        else:
            cellname = kwargs.pop('name')
        return CellAttr(name=cellname, rule=func, *args, **kwargs)

    return fun2cell_decorator

reset()
