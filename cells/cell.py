"""
Cell

Cell, and subclasses of Cell.
TODO: More here.
"""

DEBUG = False

import cells

def debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "        cell > ")
    if DEBUG:
        print " ".join(msgs)


class CellException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class RuleCellSetError(CellException):
    pass

class EphemeralCellUnboundError(CellException):
    pass

class ValueCellRunError(CellException):
    pass

class SetDuringNotificationError(CellException):
    pass
        
class Cell(object):
    """The base Cell class. Does everything interesting.

    TODO: Write a better description
    """
    def __init__(self, owner, name, rule=lambda s,p: None, value=None,
                 observers=[], type=None):
        debug("running cell init for", name, "with", str(len(observers)),
              "observers, value=", str(value))
        self.name = name
        self.rule = rule
        self.value = value
        self.observers = observers
        self.owner = owner
        
        self.called_by = set([])     # the cells whose rules call this cell
        self.calls = set([])         # the cells which this cell's rule calls

        self.dp = 0
        self.bound = False
        
        self.constant = False
        self.notifying = True
        self.changed = False

        if value:
            self.bound = True
            self.run_observers(None, False)

    def get(self):
        debug("Getting", self.name)

        # first, determine if this cell needs a recalculation
        self.update()
        
        debug(self.name, "is", str(self.value))

        if cells.curr:               # if there's a calling cell,
            # and it's not a rule-then-value cell
            if not isinstance(cells.curr, RuleThenValueCell):
                # notify calling cell that it depends on this cell
                cells.curr.calls.add(self)
                # and add the calling cell to the called-by list
                self.called_by.add(cells.curr)

        return self.value

    def set(self, value):
        """Special setter for Cell attributes.

        TODO: Describe my behavior
        """
        self.value_set = True
        
        if self.value != value:
            cells.dp += 1
            self.dp = cells.dp
            self.changed = True

            debug("Setting", self.name, "to", str(value))

            oldval = self.value         # save for observers
            oldbound = self.bound       # ditto
            self.bound = True
            self.value = value
            
            self.run_observers(oldval, oldbound)

            self.change = False

    def update(self, queryer=None):
        """Determines whether this cell needs to be updated."""
        debug(self.name, "updating")

        if not self.bound:              # if unbound, always recalc
            debug(self.name, "unbound in update")
            self.run(queryer)
        else:
            debug(self.name, "bound in update; I call",
                  str([ cell.name for cell in self.calls ]))
            for called in self.calls:                
                # this cell depends on the changed cell
                if called.changed == True:
                    debug(self.name, "is updating, found a changed cell:",
                          called.name)
                    # rerun, propogating to the queryer 1st
                    self.run(queryer)
                else:
                    debug(self.name, "running update on", called.name)
                    # recurse down the calls graph
                    called.update(self)
        # and no matter what, at this point we're updated.
        self.dp = cells.dp

    def add_calls(self, *calls_cells):
        """Appends the passed list of cells to this cell's calls list"""
        for cell in calls_cells:
            self.calls.add(cell)

    def add_called_by(self, *cb_cells):
        """Appends the passed list of cells to this cell's called-by list"""
        for cell in cb_cells:
            self.called_by.add(cell)

    def run_observers(self, oldval, oldbound):
        debug("Number of observers:", str(len(self.observers)))
        for observer in self.observers:
            debug("Running observer", str(observer))
            observer(self.owner, self.value, oldval, oldbound)

    def pre_run_hook(self):
        """A testing hook; exec's as the first statement in run()"""
        pass
            
    def run(self, queryer=None):
        """Runs the rule & propogates the change to this cell's called-by list,
        if neccessary, starting with the queryer (if passed)."""
        self.pre_run_hook()

        # update to this datapulse, then run the rule
        debug("Global datapulse is:", str(cells.dp))

        self.dp = cells.dp        
        oldval = self.value
        oldbound = self.bound
        
        debug(self.name, "datapulse is:", str(self.dp))

        # set this cell as the currently-running cell
        if cells.curr:
            debug("Currently-running cell was", str(cells.curr.name))
        else:
            debug("No currently-running cell")
        oldrunner = cells.curr
        cells.curr = self
        debug("Currently-running cell is now", str(self.name))

        # note the function is passed the *owner* as the first arg, 
        # mimicking standard Foo.bar dispatch
        self.value = self.rule(self.owner, self.value)
        self.bound = True
        
        # only rerun dependents & observers if the value changed
        if oldval != self.value:
            self.notifying = True
            self.run_observers(oldval, oldbound)
            
            self.notifying = False

        # now that the subgraph is equalized, restore the old running cell
        cells.curr = oldrunner
            
        if not cells.curr:
            debug("No currently-running cell")
        else:
            debug("Currently-running cell back to",
                  str(cells.curr.name))


class RuleCell(Cell):
    """A cell whose value is determined by a function (a rule)."""
    def set(self, value):
        raise RuleCellSetError("cannot set a rule cell")

class RuleThenValueCell(Cell):
    """Runs the rule to determine initial value, then acts like a ValueCell"""
    def __init__(self, *args, **kwargs):
        Cell.__init__(self, *args, **kwargs)
        self.run()
        self.rule = None
        self.bound = True
        self.run_observers(None, False)

        
class ValueCell(Cell):
    def run(self):
        raise ValueCellRunError("attempt to run a value cell")
    
class EphemeralCell(Cell):
    def get(self):
        debug("get for", self.name, "(ephemeral)")
        if not self.bound:
            debug("ephemeral", self.name, "unbound")
            if cells.curr:               # if there's a calling cell,
                # notify calling cell that it depends on this cell
                cells.curr.calls.add(self)
                # and add the calling cell to the called-by list
                self.called_by.add(cells.curr)

            raise EphemeralCellUnboundError("attempt to read from unbound cell")
        else:
            return Cell.get(self)
        
    def set(self, value):
        """set, equalize, then unset"""
        debug("ephemeral cell", self.name, "setting")
        Cell.set(self, value)
        debug("ephemeral cell", self.name, "equalized, unbinding")
        self.bound = False

    def run(self):
        """run, equalize, then unset"""
        Cell.run(self)
        self.bound = False

    
