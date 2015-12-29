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
Classes which deal with observers, bits of code which fire when a
C{L{Model}} is updated and updated cells match certain conditions of
the observer, such as cell name or statements about the cell's value.

@var DEBUG: Turns on debugging messages for the observer module.
"""

import cells
from cells import Cell

DEBUG = False

def _debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "observer".rjust(cells._DECO_OFFSET) + " > ")
    if DEBUG or cells.DEBUG:
        print(" ".join(msgs))

# we want observers to be defined at the class level but have per-instance
# information. So, do the same trick as is done with CellAttr/Cells
class ObserverAttr(object):
    """
    Wrapper for Observers within Models. Will auto-vivify an Observer
    within a Model instance the first time it's called. 
    """
    def __init__(self, name, *args, **kwargs):
        self.name, self.args, self.kwargs = name, args, kwargs

    def __get__(self, owner, ownertype):
        if not owner: return self
        # if there isn't a value in owner.myname, make it an observer
        _debug("got request for observer", self.name,
              "args =", str(self.args),
              "kwargs =", str(self.kwargs))
        if self.name not in list(owner.__dict__.keys()):
            owner.__dict__[self.name] = Observer(*self.args,
                                                 **self.kwargs)
        return owner.__dict__[self.name]

class Observer(object):
    """
    Wrapper for a function which fires when a C{L{Model}} updates and
    certain conditions are met. Observers may be bound to specific
    attributes or whether a function returns true when handed a cell's
    old value or new value, or any combination of the above. An
    observer that has no conditions on its running runs whenever the
    Model updates. Observers with multiple conditions will only fire
    when all the conditions pass. Observers run at most once per
    datapulse.

    You should use the C{L{Model.observer}} decorator to add Observers
    to Models:

    >>> import cells
    >>> class A(cells.Model):
    ...     x = cells.makecell(value=4)
    ...
    >>> @A.observer(attrib="x",
    ...             newvalue=lambda a: a % 2)
    ... def odd_x_obs(model):
    ...     print "New value of x is odd!"
    ...
    >>> @A.observer(attrib="x")
    ... def x_obs(model):
    ...     print "x got changed!"
    ...
    >>> @A.observer()
    ... def model_obs(model):
    ...     print "something in the model changed"
    ...
    >>> @A.observer(attrib="x",
    ...             newvalue=lambda a: a % 2,
    ...             oldvalue=lambda a: not (a % 2))
    ... def was_even_now_odd_x_obs(model):
    ...     print "New value of x is odd, and it was even!"
    ...
    >>> a = A()
    something in the model changed
    x got changed!
    >>> a.x = 5
    something in the model changed
    x got changed!
    New value of x is odd!
    New value of x is odd, and it was even!
    >>> a.x = 11
    something in the model changed
    x got changed!
    New value of x is odd!
    >>> a.x = 42
    something in the model changed
    x got changed!


    @ivar attrib: (optional) The cell name this observer watches. Only
        when a cell with this name changes will the observer fire. You
        may also pass a list of cell names to "watch".

    @ivar oldvalue: A function (signature: C{f(val) -> bool}) which,
        if it returns C{True} when passed a changed cell's out-of-date
        value, allows the observer to fire.

    @ivar newvalue: A function (signature: C{f(val) -> bool}) which,
        if it returns C{True} when passed a changed cell's out-of-date
        value, allows the observer to fire.

    @ivar func: The function to run when the observer
        fires. Signature: C{f(model_instance) -> (ignored)}

    @ivar priority: When this observer should be run compared to the
        other observers on this model. Larger priorities run first,
        None (default priority) is run last. Observers with the same
        priority are possible; there are no guarantees as to the run
        order in that case.

    @ivar last_ran: The DP this observer last ran in. Observers only
        run once per DP.
    """
    
    def __init__(self, attrib, oldvalue, newvalue, func, priority=None):
        """__init__(self, attrib, oldvalue, newvalue, func, priority)

        Initializes a new Observer. All arguments are required, but
        only func is required to be anything but none.

        See attrib, oldvalue, and newvalue instance variable docs for
        explanation of their utility."""
        self.attrib_name = attrib
        self.oldvalue = oldvalue
        self.newvalue = newvalue
        self.func = func
        self.priority = priority
        self.last_ran = 0

    def run_if_applicable(self, model, attr):
        """
        Determine whether this observer should fire, and fire if
        appropriate.

        @param model: the model instance to search for matching cells
        within.

        @param attr: the attribute which "asked" this observer to run.
        """
        _debug("running observer", self.func.__name__)
        if self.last_ran == cells.cellenv.dp:   # never run twice in one DP
            _debug(self.func.__name__, "already ran in this dp")
            return
        
        if self.attrib_name:
            if isinstance(self.attrib_name, str):
                attrs = (self.attrib_name,)
            else:
                attrs = self.attrib_name

        for attrib_name in attrs:
            if isinstance(attr, Cell):
                if attr.name == attrib_name:
                    _debug("found a cell with matching name!")
                    break
            elif getattr(model, attrib_name) is attr:
                _debug(self.func.__name__, "looked in its model for an " +
                   "attrib with its desired name; found one that " +
                   "matched passed attr.")
                break
            else:
                _debug("Attribute name tests failed")
        return

        if self.newvalue:
            if isinstance(attr, Cell):
                if not self.newvalue(attr.value):
                    _debug(self.func.__name__,
                          "function didn't match cell's new value")
                    return
            else:
                if not self.newvalue(attr):
                    _debug(self.func.__name__, "function didn't match non-cell")
                    return

        # since this is immediately post-value change, the last_value attr
        # of the cell is still good.
        if self.oldvalue:
            if isinstance(attr, Cell):
                if not self.oldvalue(attr.last_value):
                    _debug(self.func.__name__,
                           "function didn't match old value")
                    return

        # if we're here, it passed all the tests, so
        _debug(self.func.__name__, "running")
        self.func(model)
        self.last_ran = cells.cellenv.dp
