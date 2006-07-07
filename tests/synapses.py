#!/usr/bin/env python

import unittest, sys
sys.path += "../"
import cells

"""
Synapses are filters for Cells. They can be applied to any type of
Cell, and they simply process the cell to build a value which is
provided to dependent cells as the filtered cell's value.

For instance, we want to write to a log file every hundred times a
resource is accessed. So, we build a cell 'log_text' which calls the
resource counter 'hits', with an observer 'log_text_obs' which does
the actual writing. We don't want to store any state with the
'log_text' cell's rule -- we just want the rule to be called when
there's a hundred hits. So, we define a filter on hits in log_text
that makes hits only propogate to log_text when the delta between its
last-propogated and new values is 100.

The following synapses are provided by cells.synapse:
(deferred)
"""

class SynapseTests(unittest.TestCase):
    def test_BasicSynapse(self):
        # so, we define two cells, one with the filter        
        self.a = cells.InputCell(None, 1, name="a")

        def b_rule(model, prev):
            if cells.ChangeSynapse(owner=self.b, name="filter1", read=self.a,
                                   delta=10)() > prev:
                return "no change"
            else:
                return "changed!"
                    
        self.b = cells.RuleCell(None, b_rule, name="b")

        # and then we build the deps
        curr_b = self.b.get()

        # and we increment the filtered cell a bit
        self.a.set(self.a.get() + 3)              # not enough
        self.failUnless(self.b.get() == curr_b)
        self.a.set(self.a.get() + 3)              # closer....
        self.failUnless(self.b.get() == curr_b)
        self.a.set(self.a.get() + 3)              # almost there...
        self.failUnless(self.b.get() == curr_b)

        # then we go over the threshold:
        self.a.set(self.a.get() + 3)
        # and we should see b change
        self.failIf(self.b.get() == curr_b)

if __name__ == "__main__": unittest.main()
