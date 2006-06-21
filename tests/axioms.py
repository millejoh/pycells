#!/usr/bin/env python

import unittest, sys
sys.path += "../"
import cells

class DataPulseAxioms(unittest.TestCase):
    """A set of axioms about 'data pulses', that is, what happens to a group
    of dependent cells when a perturbation is introduced"""
    def setUp(self):
        self.cellA_runcount = 0

        def cellA_func(cellself, prev):
            self.cellA_runcount += 1
            return 42
        
        self.cellA = cells.Cell(None, "cellA", rule=cellA_func)
        self.cellB = cells.Cell(None, "cellB", value=21)

    def test_Axiom1_GlobalUpdateCounter(self):
        """
        1. Global Update Counter: There is a global update
        counter. (Guarantees that there is a globally-consistent
        notion of the time at which updates occur.)
        """
        self.failUnless(cells.time > 0)
        
    def test_Axiom2_CellTime(self):
        """
        2. Per-Cell 'As Of' Value: Every cell has a 'current-as-of'
        update count that is initialized with a value that is less
        than the global update count will ever be.
        """
        self.failUnless(self.cellA.time == 0)

    def test_Axiom3_CellOutOfDate(self):
        """
        3. Out-of-dateness: A cell is out of date if its update count
        is lower than the update count of any of the cells it depends
        on.

        Given the previous two axioms, a new cell is *always* out of
        date.
        """
        self.failUnless(self.cellA.requires_update == True)

    def test_Axiom4_OutOfDateCellUpdates(self):
        """
        4. Out-of-date Before: When a rule-driven cell's value is
        queried, its rule is only run if the cell is out of date;
        otherwise a cached previous value is returned.  (Guarantees
        that a rule is not run unless its dependencies have changed
        since the last time the rule was run.)
        """
                                        # by axiom 3, cellA is out of date
        self.cellA.get()       # should bring it up to date by running the rule
        self.failUnless(self.cellA_runcount == 1) 
        self.cellA.get()       # since it's now up to date, the rule
        self.failUnless(self.cellA_runcount == 1) # should not have been run

    def test_Axiom5_CellTimeUpdates(self):
        """
        5. Up-to-date After: Once a cell's rule is run (or its value
        is changed, if it is an input cell), its update count must be
        equal to the global update count.  (Guarantees that a rule
        cannot run more than once per update.)
        """
        # as before, we bring cellA up to date:
        self.cellA.get()
        self.failUnless(self.cellA.time == cells.time)
        
    def test_Axiom6_InputAdvancesSystem(self):
        """
        6. Inputs Move The System Forward
        When an input cell changes, it increments the global update count and 
        stores the new value in its own update count.
        """
        pre_update = cells.time
        self.cellB.set(42)
        self.failUnless(cells.time == pre_update + 1)
        self.failUnless(self.cellB.time == cells.time)

if __name__ == "__main__":
    unittest.main()
