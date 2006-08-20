# PyCells: Automatic dataflow management for Python
# Copyright (C) 2006, Ryan Forsythe

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# See LICENSE for the full license text.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
PyCells

PyCells is a port of Ken Tilton's Cells extenstion to Common
Lisp. Cells are objects which automatically discover the cells which
call them, and notify those cells of changes.

A short example:

    >>> import cells
    >>> class Rectangle(cells.Model):
    ...     width = cells.makecell(value=1)
    ...     ratio = cells.makecell(value=1.618)
    ...     @cells.fun2cell()
    ...     def length(self, prev):
    ...         print "Length updating..."
    ...         return float(self.width) * float(self.ratio)
    ... 
    >>> r = Rectangle()
    Length updating...
    >>> r.length
    1.6180000000000001
    >>> r.width = 5
    Length updating...
    >>> r.length
    8.0899999999999999


@var DEBUG: Turns on debugging messages for *all* submodules. This is
    a whole lot of text, so you'll probably want to use the
    submodules' C{DEBUG} flags instead

@var cellenv: Thread-local cell environment variables.
"""
DEBUG = False

_DECO_OFFSET = 9                 #: for the debug '  module > ' messages

import threading

cellenv = threading.local()
cellenv.dp = 0
cellenv.curr = None
cellenv.curr_propogator = None
cellenv.queued_updates = []
cellenv.deferred_sets = []

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

    A decorator which creates a new RuleCell using the decorated
    function as the C{rule} parameter.

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

from cell import Cell, InputCell, RuleCell, RuleThenInputCell
from cell import UntilAskedLazyCell, AlwaysLazyCell, DictCell, ListCell
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
    the currently-instantiated cells' state, but quite useful while
    fooling around in an ipython session.
    """
    global cellenv
    
    cellenv.dp = 1
    cellenv.curr = None
    cellenv.curr_propogator = None
    cellenv.queued_updates = []
    cellenv.deferred_sets = []

reset()
