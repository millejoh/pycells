"""
PyCells

PyCells is a port of Ken Tilton's Cells extenstion to Common
Lisp. Cells are objects which automatically discover the cells which
call them, and notify those cells of changes.

@var DEBUG: Turns on debugging messages for *all* submodules. This is
    a whole lot of text, so you'll probably want to use the
    submodules' C{DEBUG} flags instead
"""
DEBUG = False

_DECO_OFFSET = 9                 # for the debug '  module > ' messages

_dp = 0
_curr = None
_curr_propogator = None
_queued_updates = []
_deferred_sets = []

from cellattr import CellAttr

def makecell(*args, **kwargs):
    """
    makecell(rule=None, value=None, unchanged_if=None,
    celltype=None) -> CellAttr

    Creates a new cell attribute in a L{Model}. This attribute may be
    accessed as one would access a non-cell attribute, and
    autovivifies itself in the instance upon first access (in
    L{Model.__init__}).

    @param rule: Define a rule which backs this cell. You must only
        define one of C{rule} or C{value}. Lacking C{celltype}, this
        creates a L{RuleCell}.  This must be passed a callable with
        the signature C{f(self, prev) -> value}, where C{self} is the
        model instance the cell is in and C{prev} is the cell's
        out-of-date value.

    @param value: Define a value for this cell. You must only define
        one of C{rule} or C{value}. Lacking C{celltype}, this creates an
        L{InputCell}.

    @param unchanged_if: Sets a function to determine if a cell's
        value has changed. For example,

            >>> class A(cells.Model):
            ...     x = cells.makecell(value=1,
            ...                        unchanged_if=lambda n,o: abs(n - o) > 5)
            ...     y = cells.makecell(rule=lambda s,p: s.x * 2)
            ... 
            >>> a = A()
            >>> a.x
            1
            >>> a.y
            2
            >>> a.x = 3
            >>> a.x
            3
            >>> a.y
            6
            >>> a.x = 90
            >>> a.x
            3
            >>> a.y 
            6

        The signature for the passed function is C{f(old, new) ->
        bool}.
            
    @param celltype: Set the cell type to generate. You must pass C{rule}
        or C{value} correctly. Refer to L{cells.cell} for available
        types.
    """
    return CellAttr(*args, **kwargs)

def fun2cell(*args, **kwargs):
    """
    fun2cell(unchanged_if=None, celltype=None) -> decorator

    By default, creates a new RuleCell using the decorated function as
    the C{rule} parameter.

    @param unchanged_if: Sets a function to determine if a cell's
        value has changed. For example,

            >>> class A(cells.Model):
            ...     x = cells.makecell(value=1,
            ...                        unchanged_if=lambda n,o: abs(n - o) > 5)
            ...     y = cells.makecell(rule=lambda s,p: s.x * 2)
            ... 
            >>> a = A()
            >>> a.x
            1
            >>> a.y
            2
            >>> a.x = 3
            >>> a.x
            3
            >>> a.y
            6
            >>> a.x = 90
            >>> a.x
            3
            >>> a.y 
            6

        The signature for the passed function is C{f(old, new) ->
        bool}.
            
    @param celltype: Set the cell type to generate. You must pass C{rule}
        or C{value} correctly. Refer to L{cells.cell} for available
        types.
    """
    def fun2cell_decorator(func):        
        return CellAttr(rule=func, *args, **kwargs)
    return fun2cell_decorator

from cell import Cell, InputCell, RuleCell, RuleThenInputCell, OnceAskedLazyCell
from cell import UntilAskedLazyCell, AlwaysLazyCell
from cell import _CellException, RuleCellSetError
from cell import InputCellRunError, SetDuringNotificationError

from model import Model, NonCellSetError
from family import Family, FamilyTraversalError
from synapse import ChangeSynapse

def _debug(*msgs):
    """
    debug() -> None

    Prints debug messages.
    """
    if DEBUG:
        print " ".join(msgs)

def reset():
    """
    reset() -> None

    Resets all of PyCells' globals back to their on-package-import
    values.  This is a pretty dangerous thing to do if you care about
    the currently-instantiated cells' values, but quite useful while
    fooling around in an ipython session.
    """
    global _dp, _curr, _curr_propogator, _queued_updates, _deferred_sets
    
    _dp = 1
    _curr = None
    _curr_propogator = None
    _queued_updates = []
    _deferred_sets = []

reset()
