#!/usr/bin/env python

import unittest, sys
sys.path += "../"
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
        cells.curr = None
        x = cells.Cell(None, "x", rule=lambda s,p: (p or 39) + 3)
        self.failUnless(x.get() == x.get())  # should not calculate twice

class AlgoTests_Rule1(unittest.TestCase):
    """1. If a cell is a value cell, setting it changes its value, advances
    the global datapulse value, and sets its datapulse value to the
    global dp value.
    """
    def setUp(self):
        cells.reset()
        self.x = cells.Cell(None, "x", value=21)
        
    def testA_SettingAdvancesGlobalDP(self):
        """Rule 1 part a: A cell being set advances the global DP"""
        prev_dp = cells.dp
        self.x.set(42)
        self.failUnless(prev_dp + 1 == cells.dp)

    def testB_SettingChangesValue(self):
        """Rule 1 part b: A cell being set changes its value"""
        self.x.set(42)
        self.failUnless(self.x.get() == 42)

    def testC_SettingChangesCellsDP(self):
        """Rule 1 part c: A cell being set advances its DP to the global DP
        """
        self.x.set(42)
        self.failUnless(self.x.dp == cells.dp)

class AlgoTests_Rule2(unittest.TestCase):
    """2. If a cell's value changes, it must tell all cells which call it to
    recalculate. The cell must flag itself as being in the midst of
    this process until all of its dependents have finished
    recalculating.
    """
    def setUp(self):
        cells.reset()
        self.x = cells.Cell(None, "x", value=21)

        self.captured_notify_flag = None
        def a_rule(s, p):
            self.captured_notify_flag = self.x.notifying
            return self.x.get() * 2
        self.a = cells.Cell(None, "a", rule=a_rule)

    def testA_SettingNotifications(self):
        """Rule 2 part a: A cell with a changed value must tell the
        cells which call it to recalculate"""
        self.a.get()                         # a is now dependent on x
        self.x.set(42)
        self.failUnless(self.a.get() == 84)

    def testB_SettingRecalcNotificationFlag(self):
        """Rule 2 part b: A cell with a changed value must flag itself
        as 'notifying' until all cells which call it have finished
        recalculating"""
        self.a.get()                    # a is now dependent on x
        self.x.set(42)         # x causes a to run, capturing x's flag
        self.failUnless(self.captured_notify_flag == True)

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
        self.x = cells.Cell(None, "x", value=1)
        self.b = cells.Cell(None, "b", rule=lambda s,p: (p or 40) + 2)
        self.a = cells.Cell(None, "a",
                            rule=lambda s,p: self.b.get() * self.x.get())
        
    def testA_QueriedCellWithNoOODUpdates(self):
        """Rule 3 part a: A cell which depends on no out-of-date cell
        updates itself to the global DP"""
        self.x.get()                    # x is current
        b_prev = self.b.get()           # b is current
        self.a.get()                    # initialize deps on b and x
        
        cells.dp += 1                   # advance DP
        self.a.get()                    # no dependencies are out-of-date, so
        self.failUnless(self.a.dp == cells.dp) # its DP count == global DP count

    def testB_CalledCellQueriesCalled(self):
        """Rule 3 part b: A cell B which is called by a cell A which
        must recalculate due to a changed cell X. B must be queried to
        verify it's up-to-date.
        """
        #   x <-- a --> b
        # b should not be recalculated, but its DP should be == global
        # DP after equalization since it was queried to check if it
        # was up to date
        self.a.get()               # links set up, b initialized to 42
        self.x.set(2)                   # a out of date, recalculates
        self.failUnless(self.b.dp == cells.dp) # b up-to-date
        self.failUnless(self.b.value == 42) # but it did not recalculate

    def testC_QueriedCellRecalculates(self):
        """Rule 3 part c: A cell B which calls changed cell X, must
        recalculate when queried"""
        #   x <-- a --> b
        #   ^__________/
        # we're gonna have to jury-rig this, since we can't let b
        # recalculate first naturally
        self.b = cells.Cell(None, "b", rule=lambda s,p: (p or 2) * self.x.get())
        
        self.b.add_calls(self.x)             # set up dependencies for b by hand
        self.b.add_called_by(self.a)
        self.a.add_calls(self.b, self.x)     # and for a
        self.x.add_called_by(self.a, self.b) # .. and x
        
        # run a fake x.set(3) in the desired order:
        cells.dp += 1                 #  \
        self.x.value = 3              #   } TODO: verify everything's done here
        self.x.changed_dp = cells.dp  #  /
        self.x.dp = cells.dp          # /
        self.a.update()               # causes b.update() to run
        self.failUnless(self.b.value == 6) # which causes b's rule to run
        self.x.changed = False
        
        # but now that x's change has propogated, further updates on a:
        self.a.update()
        # which will call b.update(), won't cause b.run()
        self.failUnless(self.b.value == 6)

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
        
        self.x = cells.Cell(None, "x", value=5)

        def anon_rule(name, getfrom):
            def rule(s,p):
                self.runlog.append(name)
                return getfrom.get() + (p or 0)
            return rule

        self.c = cells.Cell(None, "c", rule=anon_rule('c', self.x))
        self.b = cells.Cell(None, "b", rule=anon_rule('b', self.c))

        def a_rule(s,p):
            self.runlog.append("a")
            return self.b.get() + self.x.get() + (p or 0)
        self.a = cells.Cell(None, "a", rule=a_rule)

        self.h = cells.Cell(None, "h", rule=anon_rule('h', self.a))
        self.i = cells.Cell(None, "i", rule=anon_rule('i', self.b))
        self.j = cells.Cell(None, "j", rule=anon_rule('j', self.c))

        # build dependencies
        self.h.get()
        self.i.get()
        self.j.get()

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
        self.failUnless(self.runlog[:3] == ["c", "b", "a"])

    def testB_QueriedCellQueuesRecalcs(self):
        """Rule 4 part b: After the querying cell is recalculated, the
        remaining dependent cells must be run."""
        # (continuing from test_4_QueryingCellRecalcsFirst:
        # ... then c's queued cells recalc... Verify that bit.
        self.failUnless("j" in self.runlog)

    def testC_QueuedCellsRunAfterQueryingCells(self):
        """Rule 4 part c: The cells which were queued for
        recalculation must run after all querying cells have been run,
        FIFO."""
        # (continuing from test_4_QueriedCellQueuesRecalcs) ... then
        # b's, then a's. Verify that bit.  (note, h isn't deferred so
        # it's run first, then c's (j), then b's deferred (i).)
        self.failUnless(self.runlog[3:] == ["h", "j", "i"])

class AlgoTests_Rule9999(unittest.TestCase):
    """All the 'trivial' rules go in here"""
    def testA_AlternateEqualityTester(self):
        """5. A cell must allow an alternate function to be passed which tests
        for equality of the previous & new values."""
        x = cells.Cell(None, "x", value=5,
                       unchanged_if=lambda old,new: abs(old - new) < 5)
        a = cells.Cell(None, "a", rule=lambda s,p: x.get() * 2)

        self.failUnless(a.get() == 10)
        x.set(7)                        # will *not* set, since |5-7| < 5
        self.failUnless(a.get() == 10)  # and so no propogation happens
        x.set(11)                       # will set, since |5-11| > 5
        self.failUnless(a.get() == 22)
        
        
if __name__ == "__main__":
    unittest.main()
