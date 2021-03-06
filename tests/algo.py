#!/usr/bin/env python

import unittest, sys
#sys.path += "../"
import cells

"""
Cells' rules are as follows:

Def: Current: A cell is current if its datapulse is equal to the
     global datapulse.

0. If a cell is asked for its value, and it is current, it may return
   its value as-is.

1. If a cell is a value cell, setting it changes its value, advances
   the global datapulse value, and sets its datapulse value to the
   global dp value.
       
2. If a cell's value changes, it must tell all cells which call it to
   recalculate. The cell must flag itself as being in the midst of
   this process until all of its dependents have finished
   recalculating.

3. When a cell is asked for its value during a recalculation, it
   must query the cells it calls. This query recurses down the
   'calls' subgraph. Any cell which is current may be used as-is. Any
   cell which calls 0 cells who are at earlier datapulses is marked as
   being at the global datapulse. Any cell which depends on the
   changed value X begins recalculating as in 2.

4. If a cell has been queried, and this causes it to recalculate which
   causes its value to change, it must first cause the querying cell
   to recalculate. Any other recalculation commands by this cell must
   be queued. After that cell finishes recalculating, (and that change
   propogated up in the same manner) the queue of recalculations may
   be run.

The following are far more trivial rules for all cells -- this just seemed
the best place to test them
   
5. A cell must allow an alternate function to be passed which tests
   for equality of the previous & new values.

6. A cell must be garbage collected appropriately; that is, other
   cells must not prevent it from being GCd because of internal
   references.

"""


class AlgoTests_Rule0(unittest.TestCase):
    """
    0. If a cell is asked for its value, and it is current, it may return
    its value as-is.
    """
    def setUp(self):
        cells.reset()

    def test_ReturnWithoutRecalculation(self):
        """A cell does not recalculate itself if it is current
        """
        cells.cellenv.curr = None
        x = cells.Cell(None, name="x", rule=lambda s,p: (p or 39) + 3)
        self.assertTrue(x.getvalue() == x.getvalue())  # should not calculate twice

class AlgoTests_Rule1(unittest.TestCase):
    """1. If a cell is a value cell, setting it changes its value, advances
    the global datapulse value, and sets its datapulse value to the
    global dp value.
    """
    def setUp(self):
        cells.reset()
        self.x = cells.Cell(None, name="x", value=21)
        
    def testA_SettingAdvancesGlobalDP(self):
        """Rule 1 part a: A cell being set advances the global DP"""
        prev_dp = cells.cellenv.dp
        self.x.set(42)
        self.assertTrue(prev_dp + 1 == cells.cellenv.dp)

    def testB_SettingChangesValue(self):
        """Rule 1 part b: A cell being set changes its value"""
        self.x.set(42)
        self.assertTrue(self.x.getvalue() == 42)

    def testC_SettingChangesCellsDP(self):
        """Rule 1 part c: A cell being set advances its DP to the global DP
        """
        self.x.set(42)
        self.assertTrue(self.x.dp == cells.cellenv.dp)

class AlgoTests_Rule2(unittest.TestCase):
    """2. If a cell's value changes, it must tell all cells which call it to
    recalculate. The cell must flag itself as being in the midst of
    this process until all of its dependents have finished
    recalculating.
    """
    def setUp(self):
        cells.reset()
        self.x = cells.Cell(None, name="x", value=21)

        self.captured_notify_flag = None
        def a_rule(s, p):
            self.captured_notify_flag = self.x.notifying
            return self.x.getvalue() * 2
        self.a = cells.Cell(None, name="a", rule=a_rule)

    def testA_SettingNotifications(self):
        """Rule 2 part a: A cell with a changed value must tell the
        cells which call it to recalculate"""
        self.a.getvalue()                         # a is now dependent on x
        self.x.set(42)
        self.assertTrue(self.a.getvalue() == 84)

    def testB_SettingRecalcNotificationFlag(self):
        """Rule 2 part b: A cell with a changed value must flag itself
        as 'notifying' until all cells which call it have finished
        recalculating"""
        self.a.getvalue()                    # a is now dependent on x
        self.x.set(42)         # x causes a to run, capturing x's flag
        self.assertTrue(self.captured_notify_flag == True)

class AlgoTests_Rule3(unittest.TestCase):
    """3. When a cell is asked for its value during a recalculation, it
    must query the cells it calls. This query recurses down the
    'calls' subgraph. Any cell which is current may be used as-is. Any
    cell which calls 0 cells who are at earlier datapulses is marked as
    being at the global datapulse. Any cell which depends on the
    changed value X begins recalculating as in rule 2.
    """
    def setUp(self):
        cells.reset()
        self.x = cells.Cell(None, name="x", value=1)
        self.b = cells.Cell(None, name="b", rule=lambda s,p: (p or 40) + 2)
        self.a = cells.Cell(None, name="a",
                            rule=lambda s,p: self.b.getvalue() * self.x.getvalue())
        
    def testA_QueriedCellWithNoOODUpdates(self):
        """Rule 3 part a: A cell which depends on no out-of-date cell
        updates itself to the global DP"""
        self.x.getvalue()                    # x is current
        b_prev = self.b.getvalue()           # b is current
        self.a.getvalue()                    # initialize deps on b and x
        
        cells.cellenv.dp += 1           # advance DP
        self.a.getvalue()                    # no dependencies are out-of-date, so
        # fail unless its DP count = global DP count
        self.assertTrue(self.a.dp == cells.cellenv.dp)

    def testB_CalledCellQueriesCalled(self):
        """Rule 3 part b: A cell B which is called by a cell A which
        must recalculate due to a changed cell X. B must be queried to
        verify it's up-to-date.
        """
        #   x <-- a --> b
        # b should not be recalculated, but its DP should be == global
        # DP after equalization since it was queried to check if it
        # was up to date
        self.a.getvalue()               # links set up, b initialized to 42
        self.x.set(2)                   # a out of date, recalculates
        self.assertTrue(self.b.dp == cells.cellenv.dp) # b up-to-date
        self.assertTrue(self.b.value == 42) # but it did not recalculate

    def testC_QueriedCellRecalculates(self):
        """Rule 3 part c: A cell B which calls changed cell X, must
        recalculate when queried"""
        #   x <-- a --> b
        #   ^__________/
        # we're gonna have to jury-rig this, since we can't let b
        # recalculate first naturally
        self.b = cells.Cell(None, name="b",
                            rule=lambda s,p: (p or 2) * self.x.getvalue())
        
        self.b.add_calls(self.x)             # set up dependencies for b by hand
        self.b.add_called_by(self.a)
        self.a.add_calls(self.b, self.x)     # and for a
        self.x.add_called_by(self.a, self.b) # .. and x
        
        # run a fake x.set(3) in the desired order:
        cells.cellenv.dp += 1          #  
        self.x.value = 3               #   TODO: verify everything's done here
        self.x.changed_dp = cells.cellenv.dp
        self.x.dp = cells.cellenv.dp
        self.a.updatecell()               # causes b.updatecell() to run
        self.assertTrue(self.b.value == 6) # which causes b's rule to run
        self.x.changed = False
        
        # but now that x's change has propogated, further updates on a:
        self.a.updatecell()
        # which will call b.updatecell(), won't cause b.run()
        self.assertTrue(self.b.value == 6)

class AlgoTests_Rule4(unittest.TestCase):
    """4. If a cell has been queried, and this causes it to recalculate which
    causes its value to change, it must first cause the querying cell
    to recalculate. Any other recalculation commands by this cell must
    be queued. After that cell finishes recalculating, (and that change
    propogated up in the same manner) the queue of recalculations may
    be run.
    """
    def setUp(self):
        #    h     i     j
        #    |     |     |
        #    v     v     v
        #    a --> b --> c
        #    |           |
        #    \-- > x <---/
        cells.reset()
        self.runlog = []
        
        self.x = cells.Cell(None, name="x", value=5)

        def anon_rule(name, getfrom):
            def rule(s,p):
                self.runlog.append(name)
                return getfrom.getvalue() + (p or 0)
            return rule

        self.c = cells.Cell(None, name="c", rule=anon_rule('c', self.x))
        self.b = cells.Cell(None, name="b", rule=anon_rule('b', self.c))

        def a_rule(s,p):
            self.runlog.append("a")
            return self.b.getvalue() + self.x.getvalue() + (p or 0)
        self.a = cells.Cell(None, name="a", rule=a_rule)

        self.h = cells.Cell(None, name="h", rule=anon_rule('h', self.a))
        self.i = cells.Cell(None, name="i", rule=anon_rule('i', self.b))
        self.j = cells.Cell(None, name="j", rule=anon_rule('j', self.c))

        # build dependencies
        self.h.getvalue()
        self.i.getvalue()
        self.j.getvalue()

        self.runlog = []

        # run an x.set(3) in the desired order:
        self.x.propogation_list = lambda s,e: [ self.a, self.c ]
        self.c.propogation_list = lambda s,e: [ self.b, self.j ]
        self.b.propogation_list = lambda s,e: [ self.a, self.i ]

        self.x.set(3)

    def testA_QueryingCellRecalcsFirst(self):
        """Rule 4 part a: A cell which recalculates because of an
        up-to-date query must first cause the querying cell to
        recalculate (which recurses)"""
        # x changes, and x tells a to recalc, a queries b queries c.
        # c recalcs, then b recalcs, then a recalcs... Verify that last bit.
        self.assertTrue(self.runlog[:3] == ["c", "b", "a"])

    def testB_QueriedCellQueuesRecalcs(self):
        """Rule 4 part b: After the querying cell is recalculated, the
        remaining dependent cells must be run."""
        # (continuing from test_4_QueryingCellRecalcsFirst:
        # ... then c's queued cells recalc... Verify that bit.
        self.assertTrue("j" in self.runlog)

    def testC_QueuedCellsRunAfterQueryingCells(self):
        """Rule 4 part c: The cells which were queued for
        recalculation must run after all querying cells have been run,
        FIFO."""
        # (continuing from test_4_QueriedCellQueuesRecalcs) ... then
        # b's, then a's. Verify that bit.
        self.assertTrue(self.runlog[3:] == ["j", "i", "h"])

class AlgoTests_Rule9999(unittest.TestCase):
    """All the 'trivial' rules go in here"""
    def testA_AlternateEqualityTester(self):
        """5. A cell must allow an alternate function to be passed which tests
        for equality of the previous & new values."""
        x = cells.Cell(None, name="x", value=5,
                       unchanged_if=lambda old,new: abs(old - new) < 5)
        a = cells.Cell(None, name="a", rule=lambda s,p: x.getvalue() * 2)

        self.assertTrue(a.getvalue() == 10)
        x.set(7)                        # will *not* set, since |5-7| < 5
        self.assertTrue(a.getvalue() == 10)  # and so no propogation happens
        x.set(11)                       # will set, since |5-11| > 5
        self.assertTrue(a.getvalue() == 22)

    def testB_DelWorks(self):
        """6. A cell must be garbage collected appropriately; that is,
        other cells must not prevent it from being GCd because of
        internal references.
        """
        import weakref
        
        self.x = cells.Cell(None, value=3)
        a = cells.Cell(None, rule=lambda s,p: self.x.getvalue() + 1)

        ref_x = weakref.ref(self.x)
        a.getvalue()
        del(self.x)
        self.assertFalse(ref_x())
        
if __name__ == "__main__":
    unittest.main()
