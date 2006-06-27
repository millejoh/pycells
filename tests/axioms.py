#!/usr/bin/env python

import unittest, sys
sys.path += "../"
import cells
from copy import copy

class DataPulseAxioms(unittest.TestCase):
    """A set of axioms about 'data pulses', that is, what happens to a group
    of dependent cells when a perturbation is introduced"""
    def setUp(self):
        cells.reset()
        self.rule_cell_runcount = 0

        def rule_cell_func(cellself, prev):
            self.rule_cell_runcount += 1
            return 42
        
        self.rule_cell = cells.Cell(None, "rule_cell", rule=rule_cell_func)
        self.value_cell = cells.Cell(None, "value_cell", value=21)

    def test_Axiom1_GlobalUpdateCounter(self):
        """
        1. Global Update Counter: There is a global datapulse
        counter. (Guarantees that there is a globally-consistent
        notion of the time at which updates occur.)
        """
        self.failUnless(cells.dp > 0)
        
    def test_Axiom2_CellTime(self):
        """
        2. Per-Cell 'As Of' Value: Every cell has a
        'current-as-of-datapulse' value that is initialized with a
        value that is less than the global datapulse count will ever
        be.
        """
        self.failUnless(self.rule_cell.dp == 0)

    def test_Axiom3_CellOutOfDate(self):
        """
        3. Out-of-dateness: A cell is out of date if its datapulse
        value is lower than the datapulse value of any of the cells it
        depends on.

        Given the previous two axioms, a new cell is *always* out of
        date.
        """
        self.failUnless(self.rule_cell.requires_update == True)

    def test_Axiom4_OutOfDateCellUpdates(self):
        """
        4. Out-of-date Before: When a rule-driven cell's value is
        queried, its rule is only run if the cell is out of date;
        otherwise a cached previous value is returned.  (Guarantees
        that a rule is not run unless its dependencies have changed
        since the last datapulse the rule was run in.)
        """
        # by axiom 3, rule_cell is out of date
        self.rule_cell.get() # should bring it up to date by running the rule
        self.failUnless(self.rule_cell_runcount == 1) 
        self.rule_cell.get()       # since it's now up to date, the rule
        self.failUnless(self.rule_cell_runcount == 1) # should not have been run

    def test_Axiom5_CellDPUpdates(self):
        """
        5. Up-to-date After: Once a cell's rule is run (or its value
        is changed, if it is an input cell), its datapulse value must
        be equal to the global datapulse counter.  (Guarantees that a
        rule cannot run more than once per datapulse.)
        """
        # Rule cell test:
        self.rule_cell.get() # as before, we bring rule_cell up to date
        self.failUnless(self.rule_cell.dp == cells.dp)

        # Value cell test:
        self.value_cell.set(42)
        self.failUnless(self.value_cell.dp == cells.dp)
        
    def test_Axiom6_InputAdvancesSystem(self):
        """
        6. Inputs Move The System Forward: When an input cell's value
        changes, it increments the global datapulse and stores the new
        global datapulse value in its own datapulse value.
        """
        pre_update = cells.dp
        self.value_cell.set(42)
        self.failUnless(cells.dp == pre_update + 1)
        self.failUnless(self.value_cell.dp == cells.dp)

        
class DependencyDiscoveryAxioms(unittest.TestCase):
    """
    Overview: cells automatically notice when other cells depend on
    them, then notify them at most once if there is a change.
    """
    def setUp(self):
        cells.reset()
        self.captured_curr = None
        self.captured_called_by = None

        def report(modelself, prev):
            self.captured_curr = cells.curr
            self.captured_called_by = copy(self.flypaper.called_by)
            return 42

        self.flypaper = cells.Cell(None, "flypaper", rule=report)

        self.dummy_current = cells.Cell(None, "dummy_current",
                                        rule=lambda s,p: 42)
        cells.curr = self.dummy_current

    def tearDown(self):
        del(self.captured_curr, self.captured_called_by, self.flypaper)

    def test_Axiom1_CurrCell(self):
        """
        1. Thread-local'current rule cell': There is a thread-local
        variable that always contains the cell whose rule is currently
        being evaluated in the corresponding thread.  This variable
        can be empty (e.g. None).
        """
        # first, show the variable exists
        self.failUnless(cells.curr is None)
        
        # second, show the curr-cell variable changes during rule evaluation
        flypaper.run()
        self.failUnless(self.captured_curr is not None)

        # TODO: third, show the curr-cell variable is thread-local.
        

    def test_Axiom2_CurrMaintenance(self):
        """
        2.'Currentness' Maintenance: While a cell rule's is being run,
        the variable described in #1 must be set to point to the cell
        whose rule is being run.  When the rule is finished, the
        variable must be restored to whatever value it had before the
        rule began.  (Guarantees that cells will be able to tell who
        is asking for their values.)
        """
        previous_curr = cells.curr
        self.flypaper.get()      # flypaper puts curr in captured_curr
        self.failUnless(self.captured_curr is self.flypaper)
        self.failUnless(cells.curr is previous_curr)

    def test_Axiom3_DepCreation(self):
        """
        3. Dependency Creation: When a cell is read, it adds the
        'currently-being evaluated' cell to a called-by list that it
        will notify of changes.
        """
        self.flypaper.get()
        self.failUnless(self.dummy_current in self.flypaper.called_by)

    def test_Axiom4_DepCreateOrder(self):
        """
        4. Dependency Creation Order: New cells are added to the
        called-by list only *after* the cell being read has brought
        itself up-to-date, and notified all *previous* entries in
        called-by of the change.  (Ensures that the called-by cell
        does not receive redundant notification if the caller
        cell has to be brought up-to-date first.)
        """
        self.flypaper.get()
        # dummy was added...
        self.failUnless(self.dummy_current in self.flypaper.called_by)
        # but not until the rule eval was complete
        self.failIf(self.dummy_current in self.captured_called_by)

    def test_Axiom5_MinimalDependencies(self):
        """
        5. Dependency Minimalism: A cell should only be added to the
        called-by list if it does not already present in the cell's
        called-by list.  (This isn't strictly mandatory, the
        system behavior will be correct but inefficient if this
        requirement isn't met.)
        """
        # sets curr to flypaper, adds dummy to flypaper's c-b, resets to dummy
        self.flypaper.get()                  
        # set another dummy to system's currently-running cell var
        cells.curr = cells.Cell(None, "dummy2", value=63)
        # and add it to flypaper's called-by list
        self.flypaper.get()

        # now the test:
        prev_cb = copy(self.captured_called_by)
        cells.curr = self.dummy_current
        self.flypaper.get()

        # not sure this works with all collections, but...
        self.failUnless(list(prev_cb).sort() == \
                        list(self.captured_called_by).sort())

    def test_Axiom6_DependencyRemoval(self):
        """
        6. Dependency Removal: Just before a cell's rule is run, it
        must cease to be on any other cells' called-by lists.
        (Guarantees that a dependency from a previous update cannot
        trigger an unnecessary repeated calculation.)
        """
        # dummy_current is the currently-running cell. add it to flypaper's
        # c-b list
        self.flypaper.get()
        cells.curr = None
        
        # now, if we run dummy_current it should remove itself from flypaper's
        # c-b list:
        self.dummy_current.run()

        # since it wasn't *actually* dependent on flypaper, it shouldn't set up
        # a dependency on flypaper, so we just check dummy_current isn't in
        # flypaper's c-b list:
        self.failIf(self.dummy_current in self.flypaper.called_by)
        
    def test_Axiom7_DependencyNotification(self):
        """
        7. Dependency Notification: Whenever a cell's value changes
        (due to a rule calculation or input change causing an actual
        change in a cell's value), it must notify all cells which call
        it that it has changed, in such a way that *none* of the
        callers are asked to recalculate their value until *all* of
        the callers have first been notified of the change.  (This
        guarantees that inconsistent views cannot occur.)
        """
        # this axiom is going to take a different environment than 1-6, so
        # nuke the currently-running variable
        cells.curr = None

        doTest = False

        # now, create some cells with dependencies:
        x = cells.Cell(None, "x", value=42)
        
        def a_rule(s, p):
            if doTest: self.failIf(not a.notified or b.dp > a.dp)
            return x.get() / 2
        a = cells.Cell(None, "b", rule=a_rule)

        def b_rule(s,p):
            if doTest: self.failIf(not b.notified or a.dp > b.dp)
            return x.get() * 2
        b = cells.Cell(None, "c", rule=b_rule)
        
        # set up dependencies 
        a.get()
        b.get()
        
        # now, when x changes, a and b will be run; tests inside their
        # rules ensure they are both notified before either is run
        doTest = True
        x.set(84)

    def test_Axiom8_OneNotification(self):
        """
        8. One-Time Notification: A cell's callers are removed from
        its called-by collection as soon as they have been notified.
        In particular, the cell's called-by collection must be cleared
        *before* any of the callers are asked to recalculate
        themselves.  (This guarantees that callers reinstated in a
        cell's called-by list as a side effect of recalculation will
        not get a duplicate notification in the current update, or
        miss a notification in a future update.)
        """
        # so, we make a dependency graph like:
        #  a <-- b
        cells.curr = None
        a = cells.Cell(None, "a", value=42)
        b = cells.Cell(None, "b", rule=lambda s,p: a.get() / 42)

        # now, add instrumentation to a to read its called-by list before
        # asking called-by cells to recalculate
        def cap_cb(cell):
            self.captured_called_by = cell.called_by
        a.pre_cb_recalculate_hook = cap_cb

        # so, what we should see is a's called-by list as empty when we change
        # it. b will be asked to recalc, and add itself back to a's called-by.
        a.set(84)
        self.failIf(self.captured_called_by)
        # and just for giggles...
        self.failUnless(list(a.called_by).sort() == [b].sort())
                
    def test_Axiom9_ConvertToConst(self):
        """
        9. Conversion to Constant If a cell's rule is run and no
        dependencies were created, the cell must become a 'constant'
        cell, and do no further listener additions or notification,
        once any necessary notifications to existing listeners are
        completed.  (That is, if the rule's run changed the cell's
        value, it must notify its existing listeners, but then the
        listener collection must be cleared -- *again*, in addition to
        the clearing described in #8.)
        """
        a = cells.Cell(None, "a", rule=lambda s,p: 42)
        a.get()
        self.failUnless(a.constant)
        self.failIf(a.called_by)

        b = cells.Cell(None, "b", rule=lambda s,p: 2 * a.get())
        b.get()
        self.failIf(a.called_by)

    def test_Axiom10_NoSetsDuringNotification(self):
        """
        10. No Changes During Notification: It is an error to change
        an input cell's value while change notifications are taking
        place.
        """
        cells.curr = None
        x = cells.Cell(None, "x", value=42)
        

        # create a modified Cell which instead of notifying, instead sets
        # the input cell 'x'
        class EvilCell(cells.Cell):
            def notify_called_by(fakeself):
                x.set(21)

        # now, set up a dependency graph like: x <-- evil <-- good
        evil = EvilCell(None, "evil", rule=lambda s,p: x.get() * 2)
        good = cells.Cell(None, "good", rule=lambda s,p: evil.get() + 2)
        good.get()

        # this should raise an exception:
        self.failUnlessRaises(cells.SetDuringNotificationError, x.set, 5)

    def test_Axiom11_WeakNotifyLinks(self):
        """
        11. Weak Notification: Automatically created inter-cell links
        must not inhibit garbage collection of either cell.
        (Technically optional, but very easy to do.)
        """
        pass
        
if __name__ == "__main__":
    unittest.main()
