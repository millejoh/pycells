"""
Cell

Cell, and subclasses of Cell. You will almost certainly never use
these directly, instead relying on C{L{Model}} and its subclasses to
instantiate these into objects for you.

@var DEBUG: Turns on debugging messages for the cell module.

@group Cell Types: Cell, RuleCell, InputCell, RuleThenInputCell,
    LazyCell, AlwaysLazyCell, OnceAskedLazyCell, UntilAskedLazyCell

@group Exceptions: EphemeralCellUnboundError, InputCellRunError,
    RuleAndValueInitError, RuleCellSetError, SetDuringNotificationError
"""

DEBUG = False

import cells, weakref

def _debug(*msgs):
    """
    debug() -> None

    Prints debug messages.
    """
    msgs = list(msgs)
    msgs.insert(0, "cell".rjust(cells._DECO_OFFSET) + " > ")
    if DEBUG or cells.DEBUG:
        print " ".join(msgs)

        
class Cell(object):
    """
    The base Cell class. Does everything interesting.
    """
    def __init__(self, owner, **kwargs):
        """
        __init__(self, owner, name=None, rule=None, value=None,
        unchanged_if=None) -> None

        Initializes a Cell object. You must not specify both C{rule}
        and C{value}.

        @param name: This cell's name. When using a C{Cell} with
            C{L{Model}}s, this parameter is assigned automatically.

        @param rule: Define a rule which backs this cell. You must
            only define one of C{rule} or C{value}. Lacking C{celltype},
            this creates a L{RuleCell}.  This must be passed a
            callable with the signature C{f(self, prev) -> value},
            where C{self} is the model instance the cell is in and
            C{prev} is the cell's out-of-date value.

        @param value: Define a value for this cell. You must only
            define one of C{rule} or C{value}. Lacking C{celltype}, this
            creates an L{InputCell}.

        @param unchanged_if: Sets a function to determine if a cell's
            value has changed. For example,

                >>> class A(cells.Model):
                ...     x = cells.makecell(value=1,
                ...                        unchanged_if=lambda n,o:abs(n-o)>5)
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

        @raise RuleAndValueInitError: If both C{rule} and C{value} are
            passed, raise an exception
        """
        _debug("running cell init for", kwargs.get("name") or 'anonymous')

        if kwargs.get("value", None) and kwargs.get("rule", None):
            raise RuleAndValueInitError(
                "Cell.__init__ was passed both rule and value parameters")
        
        self.owner = owner
        self.name = kwargs.get("name", None)
        self.rule = kwargs.get("rule", lambda s,p: None)
        self.value = kwargs.get("value", None)
        self.unchanged_if = kwargs.get("unchanged_if", lambda o,n: o == n)
        
        self.called_by = set([])     # the cells whose rules call this cell
        self.calls = set([])         # the cells which this cell's rule calls

        self.dp = 0
        self.changed_dp = 0
        self.bound = False
        
        self.constant = False
        self.notifying = False

        self.propogate_to = None
        self.lazy = False
        self.last_value = None

        self.synapse_space = {}         # storage for synapses used in this
                                        # cell's (possible) rule
        
        if kwargs.has_key("value"):
            self.bound = True
            self.changed_dp = cells._dp
            self.dp = cells._dp

    def get(self):
        """
        get(self, init=False) -> value

        Returns this cell's up-to-date value.
        """
        # if there's a cell on the call stack, this get is part of a rule
        # run. so, make the appropriate changes to the cells' deps
        if cells._curr:                  # (curr == None when not propogating)
            cells._curr.add_calls(self)
            self.add_called_by(cells._curr)
        
        self.update()
        return self.value

    def set(self, value):
        """
        set(self, value) -> None

        Sets this cell's value and begins propogation of the change,
        if neccessary.

        @param value: The value to set this cell's value to.
        """
        if cells._curr_propogator:       # if a propogation is happening
            _debug(self.name, "sees in-progress propogation; deferring set.")
            cells._deferred_sets.append((self, value)) # defer the set
        else:
            _debug(self.name, "setting")        
            if not self.unchanged_if(self.value, value):
                _debug(self.name, "new value is different; propogating change")
                self.last_value = self.value
                self.value = value

                cells._dp += 1
                self.dp = cells._dp

                if self.owner:
                    self.owner._run_observers(self)
                
                self.propogate()

    def update(self, queryer=None):
        """
        update(self, queryer=None) -> bool

        Updates this cell to the current global DP (datapulse),
        returning True if it changed, False otherwise.

        @param queryer: The cell to L{propogate} to first, if
            neccessary
        """
        _debug(self.name, "updating")
        if queryer:
            self.propogate_to = queryer
            
        if not self.bound:              # if this cell has never been calc'd:
            _debug(self.name, "unbound, rerunning")
            self.run()                  # it's never current
            return True
        if self.changed():                # if this cell was changed in this DP
            _debug(self.name, "changed, telling queryer to recalc")
            return True                 # the asking cell must recalculate.
        if self.dp == cells._dp:         # if this cell is current,
            _debug(self.name, "is current.")
            return False                # it's current.
        if not cells._curr_propogator:   # if the system isn't propogating,
            if not self.lazy:           # and we're not lazy,
                _debug(self.name, "sees system is not propogating; is current.")
                self.dp = cells._dp
                return False            # this cell is current.

        # otherwise, verify we're current: (by the above ifs, the
        # system is propogating and this cell is not current)
        for cell in self.calls_list():
            _debug(self.name, "asking", cell.name, "to update")
            if cell.update(self):       # if any called cell requires us,
                _debug(self.name, "got recalc command from", cell.name)
                if not self.dp == cells._dp:
                    if self.run():          # we need to re-run
                        # the run changed the value of this cell, so
                        # propogate the change, starting at the cell which
                        # requested this cell update
                        pt = queryer
                        if self.propogate_to:
                            pt = self.propogate_to
                        self.propogate(pt) 
                        self.propogate_to = None

                    # after that run(), self.calls is out of date, and
                    # all the cells the rule calls are neccessarily
                    # up-to-date, so bomb out of this loop right
                    # now. This cell's up-to-date.
                    return False

        # if we get here, no cell called by this cell required this cell to
        # update, so update DP and return False (since this cell didn't change)
        _debug(self.name,
              "finished asking called cells to update without getting recalc;",
              "is current.")
        self.dp = cells._dp
        return False

    def propogate(self, propogate_first=None):
        """
        propogate(self, propogate_first=None) -> None

        Propogates an update command to the set of cells which call
        this cell.

        @param propogate_first: If cell C{A} asks cell C{B} to update,
            and cell C{B}'s value changes (causing a C{propogate}
            call), it must propogate to C{A} first, before any of the
            other cells which call C{B}.
        """
        if cells._curr_propogator:
            _debug(self.name, "propogating. Old propogator was",
                  cells._curr_propogator.name)
        else:
            _debug(self.name, "propogating. No old propogator")
        prev_propogator = cells._curr_propogator
        cells._curr_propogator = self
        self.changed_dp = cells._dp
        self.notifying = True

        # first, notify the 'propogate_first' cell
        if propogate_first:
            # append everything but the propogate_first cell onto the deferred
            # propogation FIFO
            deferrals = list(self.called_by() - set([propogate_first]))
            _debug(self.name, "deferring update of",
                  str([ c.name for c in deferrals ]))
            cells._queued_updates.extend(deferrals)
            
            _debug(self.name, "asking", propogate_first.name, "to update first")
            propogate_first.update()
            _debug(self.name, "finished propogating to first update",
              propogate_first.name)
        else:
            # weird for testing
            for cell in Cell.propogation_list(self, propogate_first):
                if cell.lazy:
                    _debug(self.name, "saw", cell.name,
                          ", but it's lazy -- not updating")
                else:
                    _debug(self.name, "asking", cell.name, "to update")
                    cell.update()
                
        self.notifying = False
        cells._curr_propogator = prev_propogator

        if cells._curr_propogator:
            _debug(self.name, "finished propogating; switching to propogating",
                  str(cells._curr_propogator.name))
        else:
            _debug(self.name, "finished propogating. No old propogator")
        
        # run deferred stuff if no cell is currently propogating
        if not cells._curr_propogator:
            # first, updates:            
            # okay, this is a little hacky:
            cells._curr_propogator = cells.Cell(None,
                                              name="queued propogation dummy")
            
            _debug("no cell propogating! running deferred updates.")
            to_update = cells._queued_updates
            cells._queued_updates = []
            for cell in to_update:
                _debug("Running deferred update on", cell.name)
                cell.update()
                
            cells._curr_propogator = None

            # next, deferred sets:
            _debug("running deferred sets")
            to_set = cells._deferred_sets
            cells._deferred_sets = []
            for cell, value in to_set:
                cell.set(value)

    def run(self):
        """
        run(self) -> bool

        Runs the backing function (rule) for this cell. The sequence is:
        
          1. Remove this cell from all other cell's called-by sets
          
          2. Empty this cell's calls set.
          
          3. Run the function, which as a side effect may add this
             cell to other cells' called-by sets and add links in this
             cell's calls set
             
          4. If this cell's value changes,

             4.1 Run any L{observer}s in this cell's Model

             4.2 Return C{True}
        """
        _debug(self.name, "running")
        # call stack manipulation
        oldcurr = cells._curr
        cells._curr = self

        # the rule run may rewrite the dep graph; prepare for that by nuking
        # c-b links to this cell and calls links from this cell:
        for cell in self.calls_list():
            _debug(self.name, "removing c-b link from", cell.name)
            cell.remove_cb(self)
        self.reset_calls()

        self.dp = cells._dp                             # we're up-to-date
        newvalue = self.rule(self.owner, self.value)   # run the rule
        self.bound = True
        
        # restore old running cell
        cells._curr = oldcurr

        # return changed status
        if self.unchanged_if(self.value, newvalue):
            _debug(self.name, "unchanged.")
            return False
        else:
            _debug(self.name, "changed.")
            self.last_value = self.value
            self.value = newvalue

            # run any observers on this cell
            if self.owner:
                self.owner._run_observers(attribute=self)
            
            return True


    def changed(self):
        """
        changed(self) -> bool

        Did this cell's value change in this DP (datapulse)?
        """
        return cells._dp == self.changed_dp

    def calls_list(self):
        """
        calls_list(self) -> generator

        Returns a generator of cell objects whose rules call this cell
        """
        return (r() for r in self.calls)

    def called_by_list(self):
        """
        called_by_list(self) -> generator

        Returns a generator of cell objects which this cell's rule calls
        """
        return (r() for r in self.calls)

    def propogation_list(self, elide=None):
        """
        propogation_list(self, elide=None) -> generator

        Returns a generator of cell objects which this cell should
        propogate to, minus any cell passed in C{elide}.

        @param elide: Remove a cell from the list of cells to
            propogate a change to. Used by L{propogate} to remove a
            cell it had to propogate to first.
        """
        return (r() for r in self.called_by - set([elide]))
    
    def add_calls(self, *calls_cells):
        """Appends the passed list of cells to this cell's calls list"""
        self.calls.update(set([ weakref.ref(cell) for cell in calls_cells ]))

    def add_called_by(self, *cb_cells):
        """Appends the passed list of cells to this cell's called-by list"""
        self.called_by.update(set([ weakref.ref(cell) for cell in cb_cells ]))

    def remove_cb(self, *cb_cells):
        """Removes the passed list of cells from this cell's called-by list"""
        self.called_by.difference_update(set(
            [ weakref.ref(cell) for cell in cb_cells ]))

    def reset_calls(self):
        """Resets the calls list to empty"""
        self.calls = set([])


# epydoc can't handle lambdas in a param list, apparently
_nonerule = lambda s,p: None
        
class RuleCell(Cell):
    """A cell whose value is determined by a function (a rule)."""
    def __init__(self, owner, rule=_nonerule, *args, **kwargs):
        """
        __init__(self, owner, name=None, rule=lambda s,p: None,
        unchanged_if=None) -> None

        Initializes a RuleCell object, which may not be C{set} and
        whose value is determined by a rule.

        @param name: This cell's name. When using a C{Cell} with
            C{L{Model}}s, this parameter is assigned automatically.

        @param rule: Define a rule which backs this cell. You must
            only define one of C{rule} or C{value}. Lacking C{celltype},
            this creates a L{RuleCell}.  This must be passed a
            callable with the signature C{f(self, prev) -> value},
            where C{self} is the model instance the cell is in and
            C{prev} is the cell's out-of-date value.

        @param unchanged_if: Sets a function to determine if a cell's
            value has changed. The signature for the passed function
            is C{f(old, new) -> bool}.

        @raise RuleCellSetError: If C{value} is passed as a parameter
        """
        if kwargs.get("value", None):
            raise RuleCellSetError("cannot define a RuleCell's value")
        Cell.__init__(self, owner, rule=rule, *args, **kwargs)
        
    def set(self, value):
        """
        set(self, value) -> None

        You may not C{set} a L{RuleCell}

        @raise RuleCellSetError: Always raises this exception.
        """
        raise RuleCellSetError("cannot set() a rule cell")

        
class InputCell(Cell):
    """A cell whose value can be set"""
    def __init__(self, owner, value=None, *args, **kwargs):
        """
        __init__(self, owner, name=None, rule=None, value=None,
        unchanged_if=None) -> None

        Initializes an InputCell object. You may not pass a C{rule}.

        @param name: This cell's name. When using a C{Cell} with
            C{L{Model}}s, this parameter is assigned automatically.

        @param value: Define a value for this cell. You must only
            define one of C{rule} or C{value}. Lacking C{celltype}, this
            creates an L{InputCell}.

        @param unchanged_if: Sets a function to determine if a cell's
            value has changed. The signature for the passed function
            is C{f(old, new) -> bool}.

        @raise InputCellRunError: If C{rule} is passed as a parameter
        """
        if kwargs.get("rule", None):
            raise InputCellRunError("You may not give an InputCell a rule")
        Cell.__init__(self, owner, value=value, *args, **kwargs)

    def run(self):
        """
        run(self) -> None

        You may not C{run()} an L{InputCell}

        @raise InputCellRunError: Always raises
        """
        raise InputCellRunError("attempt to run InputCell '" + self.name + "'")


class RuleThenInputCell(Cell):
    """Runs the rule to determine initial value, then acts like a InputCell"""
    def __init__(self, *args, **kwargs):
        """
        __init__(self, owner, name=None, rule=lambda s,p: None,
        unchanged_if=None) -> None

        Initializes a RuleThenInputCell, whose initial value is
        determined by the passed C{rule} but then acts like an L{InputCell}

        @param name: This cell's name. When using a C{Cell} with
            C{L{Model}}s, this parameter is assigned automatically.

        @param rule: Define a rule which backs this cell. You must
            only define one of C{rule} or C{value}. Lacking C{celltype},
            this creates a L{RuleCell}.  This must be passed a
            callable with the signature C{f(self, prev) -> value},
            where C{self} is the model instance the cell is in and
            C{prev} is the cell's out-of-date value.

        @param unchanged_if: Sets a function to determine if a cell's
            value has changed. The signature for the passed function
            is C{f(old, new) -> bool}.

        @raise RuleCellSetError: If C{value} is passed as a parameter
        """
        if kwargs.get("value", None):
            raise RuleCellSetError("cannot define a RuleCell's value")

        Cell.__init__(self, *args, **kwargs)
        self.run()
        self.rule = None
        self.bound = True

    def run(self):
        """
        run(self) -> None

        You may not C{run()} an L{InputCell}

        @raise InputCellRunError: Always raises
        """
        if self.bound:
            raise InputCellRunError("attempt to run RuleThenInputCell '" +
                                    self.name + "'")


class LazyCell(RuleCell):
    """
    A RuleCell which does not update upon propogation. When it has
    C{L{get}()} run, it updates as other Cells do.
    """
    def __init__(self, *args, **kwargs):
        """
        __init__(self, owner, name=None, rule=lambda s,p: None,
        unchanged_if=None) -> None

        Initializes a LazyCell object, which may not be C{set} and
        whose value is determined by a rule.

        @param name: This cell's name. When using a C{Cell} with
            C{L{Model}}s, this parameter is assigned automatically.

        @param rule: Define a rule which backs this cell. You must
            only define one of C{rule} or C{value}. Lacking C{celltype},
            this creates a L{RuleCell}.  This must be passed a
            callable with the signature C{f(self, prev) -> value},
            where C{self} is the model instance the cell is in and
            C{prev} is the cell's out-of-date value.

        @param unchanged_if: Sets a function to determine if a cell's
            value has changed. The signature for the passed function
            is C{f(old, new) -> bool}.

        @raise RuleCellSetError: If C{value} is passed as a parameter
        """

        RuleCell.__init__(self, *args, **kwargs)
        self.lazy = True

class OnceAskedLazyCell(LazyCell):
    pass

class AlwaysLazyCell(LazyCell):
    """
    A LazyCell variant that is *always* Lazy
    """
    pass

class UntilAskedLazyCell(LazyCell):
    """
    A LazyCell who converts to a normal RuleCell after its first
    post-init C{L{get}()}
    """
    def get(self, init=False, *args, **kwargs):
        v = LazyCell.get(self, *args, **kwargs)
        if not init:
            self.lazy = False

        return v

class _CellException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class RuleCellSetError(_CellException):
    """
    RuleCells may not be set.
    """
    pass

class EphemeralCellUnboundError(_CellException):
    """
    An EphemeralCell was C{L{get}}ted without being bound.
    """
    pass

class InputCellRunError(_CellException):
    """
    An attempt to C{L{run}()} an InputCell was made.
    """
    pass

class SetDuringNotificationError(_CellException):
    """
    An attempt at a non-deferred C{L{set}()} happened during
    propogation.
    """
    pass

class RuleAndValueInitError(_CellException):
    """
    Both C{rule} and C{value} were passed to C{L{__init__}}.
    """
    pass
