"""
PyCells

TODO: More here.
"""
DEBUG = False
DECO_OFFSET = 9                 # for the debug '  module > ' messages

dp = 0
curr = None
curr_propogator = None
queued_updates = []
deferred_sets = []

from cellattr import CellAttr

def makecell(*args, **kwargs):
    """Standard cell attribute factory"""
    return CellAttr(*args, **kwargs)

def fun2cell(*args, **kwargs):
    """Decorator version of makecell"""
    def fun2cell_decorator(func):        
        return CellAttr(rule=func, *args, **kwargs)
    return fun2cell_decorator

from cell import Cell, InputCell, RuleCell, RuleThenInputCell, OnceAskedLazyCell
from cell import UntilAskedLazyCell, AlwaysLazyCell
from cell import CellException, RuleCellSetError
from cell import InputCellRunError, SetDuringNotificationError

from model import Model, NonCellSetError
from family import Family
from synapse import ChangeSynapse

def debug(*msgs):
    if DEBUG:
        print " ".join(msgs)

def reset():
    global dp, curr, curr_propogator, queued_updates, deferred_sets
    
    dp = 1
    curr = None
    curr_propogator = None
    queued_updates = []
    deferred_sets = []
        

reset()
