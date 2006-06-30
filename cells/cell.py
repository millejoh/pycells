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
        self.notifying = False
        self.changed_dp = cells.dp

        self.propogate_to = None

        if value:
            self.bound = True
            self.run_observers(None, False)

    def get(self):
        # if there's a cell on the call stack, this get is part of a rule
        # run. so, make the appropriate changes to the cells' deps
        if cells.curr:                  # (curr == None when not propogating)
            cells.curr.add_calls(self)
            self.add_called_by(cells.curr)
        
        self.update()
        return self.value

    def set(self, value):
        debug(self.name, "setting")        
        if self.value != value:
            debug(self.name, "new value is different; propogating change")
            self.value = value

            cells.dp += 1
            self.dp = cells.dp

            self.propogate()

    def update(self, queryer=None):
        debug(self.name, "updating")
        if queryer:
            self.propogate_to = queryer
            
        if not self.bound:              # if this cell has never been calc'd:
            debug(self.name, "unbound, rerunning")
            self.run()                  # it's never current
            return True
        if self.changed():                # if this cell was changed in this DP
            debug(self.name, "changed, telling queryer to recalc")
            return True                 # the asking cell must recalculate.
        if self.dp == cells.dp:         # if this cell is current,
            debug(self.name, "is current.")
            return False                # it's current.
        if not cells.curr_propogator:   # if the system isn't propogating,
            debug(self.name, "sees system is not propogating; is current.")
            self.dp = cells.dp
            return False                # this cell is current.

        # otherwise, verify we're current: (by the above ifs, the
        # system is propogating and this cell is not current)
        for cell in self.calls:
            debug(self.name, "asking", cell.name, "to update")
            if cell.update(self):       # if any called cell requires us,
                debug(self.name, "got recalc command from", cell.name)
                if not self.dp == cells.dp:
                    if self.run():          # we need to re-run
                        pt = queryer
                        if self.propogate_to:
                            pt = self.propogate_to
                        self.propogate(pt) # and propogate
                        self.propogate_to = None

                    # after that run(), self.calls is out of date, and
                    # all the cells the rule calls are neccessarily
                    # up-to-date, so bomb out of this loop right
                    # now. This cell's up-to-date.
                    return False

        # if we get here, no cell called by this cell required this cell to
        # update, so update DP and return False (since this cell didn't change)
        debug(self.name,
              "finished asking called cells to update without getting recalc;",
              "is current.")
        self.dp = cells.dp
        return False

    def propogate(self, propogate_first=None):
        if cells.curr_propogator:
            debug(self.name, "propogating. Old propogator was",
                  cells.curr_propogator.name)
        else:
            debug(self.name, "propogating. No old propogator")
        prev_propogator = cells.curr_propogator
        cells.curr_propogator = self
        self.changed_dp = cells.dp
        self.notifying = True

        # first, notify the 'propogate_first' cell
        if propogate_first:
            # append everything but the propogate_first cell onto the deferred
            # propogation FIFO
            deferrals = list(self.called_by - set([propogate_first]))
            debug(self.name, "deferring update of",
                  str([ c.name for c in deferrals ]))
            cells.queued_updates.extend(deferrals)
            
            debug(self.name, "asking", propogate_first.name, "to update first")
            propogate_first.update()
            debug(self.name, "finished propogating to first update",
              propogate_first.name)
        else:
            for cell in Cell.propogation_list(self, propogate_first):
                debug(self.name, "asking", cell.name, "to update")
                cell.update()
                
        self.notifying = False
        cells.curr_propogator = prev_propogator

        if cells.curr_propogator:
            debug(self.name, "finished propogating; switching to propogating",
                  str(cells.curr_propogator.name))
        else:
            debug(self.name, "finished propogating. No old propogator")
        
        # run deferred updates if no cell is currently propogating
        if not cells.curr_propogator:
            # okay, this is hacky:
            cells.curr_propogator = cells.Cell(None,
                                              "dummy for queued propogation")
            
            debug("no cell propogating! running deferred updates.")
            for cell in cells.queued_updates:
                debug("Running deferred update on", cell.name)
                cell.update()
                
            cells.curr_propogator = None

    def run(self):
        debug(self.name, "running")
        # call stack manipulation
        oldcurr = cells.curr
        cells.curr = self

        # the rule run may rewrite the dep graph; prepare for that by nuking
        # c-b links to this cell and calls links from this cell:
        for cell in self.calls:
            debug(self.name, "removing c-b link from", cell.name)
            cell.remove_cb(self)
        self.reset_calls()

        oldval = self.value
        self.dp = cells.dp                             # we're up-to-date
        self.value = self.rule(self.owner, self.value) # run the rule
        self.bound = True
        
        # restore old running cell
        cells.curr = oldcurr

        # return changed status
        debug(self.name, "changed?", str(oldval != self.value))
        return oldval != self.value

    def changed(self):
        return cells.dp == self.changed_dp

    def propogation_list(self, elide=None):
        return self.called_by - set([elide])
    
    def add_calls(self, *calls_cells):
        """Appends the passed list of cells to this cell's calls list"""
        self.calls.update(set(calls_cells))

    def add_called_by(self, *cb_cells):
        """Appends the passed list of cells to this cell's called-by list"""
        self.called_by.update(set(cb_cells))

    def remove_cb(self, *cb_cells):
        """Removes the passed list of cells from this cell's called-by list"""
        self.called_by.difference_update(set(cb_cells))

    def reset_calls(self):
        """Resets the calls list to empty"""
        self.calls = set([])

    def run_observers(self, oldval, oldbound):
        debug("Number of observers:", str(len(self.observers)))
        for observer in self.observers:
            debug("Running observer", str(observer))
            observer(self.owner, self.value, oldval, oldbound)



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

    
