#!/usr/bin/env python


import unittest, sys
sys.path += "../"
import cells

"""
There are several types of cells. These are their rules:

Input Cells:
1. Must be 'set'able
2. A set during propogation must defer until the propogation is complete
3. Trying to .run() a input cell throws an exception

Rule Cells:
1. Trying to set a rule cell throws an exception

Lazy Rule Cell, Once-asked flavor:
1. Evaluates during model initialization (if it's housed in a model)
2. Does not evaluate immediately when changes are propogated to it
3. Evaluates, if neccessary, when read

Lazy Rule Cell, Until-asked flavor:
1. Evaluates only when read
2. After evaluating, acts like a standard rule cell (ie, responds to propogation
   normally).

Lazy Rule Cell, Always-lazy flavor:
1. Evaluates only when read, and is unbound or a dependency has changed.
"""

class CellTypeTests_Input(unittest.TestCase):
    def setUp(self):
        cells.reset()
        self.x = cells.InputCell(None, "x", 5)
        
    def test_1_Settability(self):
        "Input 1: An input cell must be settable"
        try:
            self.x.set(4)
        except Exception, e:
            self.fail()

    def test_2_SetDuringPropogation(self):
        "Input 2: A set during propogation must defer until propogation is complete"
        a = cells.RuleCell(None, "a", lambda s,p: self.x.get() * 3)

        self.captured_x = None
        def d_rule(s,p):
            self.x.set(2)
            if not self.captured_x:
                self.captured_x = self.x.value
            return a.get()
        d = cells.RuleCell(None, "d", d_rule)

        # establish dependencies. 
        d.get()                         # x.value = 2, now.
        self.captured_x = None          # set trap
        self.x.set(5)
        # that set propogates to a, and a.value = 15. a's change propogates to
        # d. The x.set(2) happens in the middle of d's rule, but it defers until
        # the propogation is complete. So the captured x value should be 5.
        self.failUnless(self.captured_x == 5)

    def test_3_RunRaises(self):
        "Input 3: Running a value cell raises an exception."
        self.failUnlessRaises(cells.InputCellRunError, self.x.run)

class CellTypeTests_Rule(unittest.TestCase):
    def test_1_Nonsettability(self):
        "Rule 1: Rule cells may not be set"
        cells.reset()
        x = cells.RuleCell(None, "", lambda s,p: 0)
        self.failUnlessRaises(cells.RuleCellSetError, x.set, 5)

class CellTypeTests_OnceAskedLazy(unittest.TestCase):
    def setUp(self):
        cells.reset()
        self.x = cells.InputCell(None, "x", 4)
        self.a = cells.OnceAskedLazyCell(None, "a",
                                         rule=lambda s,p: self.x.get()+(p or 1))

        self.a.get()                         # establish dependencies
        self.x.set(42)                       # cause propogation
        
    def test_1_EvaluateDuringMOInit(self):
        "Once-asked Lazy 1: Once-asked lazy cells are eval'd during MO init."
        #TODO: Make a real test
        pass

    def test_2_NoEvalOnPropogation(self):
        "Once-asked Lazy 2: Once-asked lazy cells are not evaluated when changes propogate to them"
        self.failUnless(self.a.value == 5)   # sneaky exam doesn't cause eval

    def test_3_EvalOnRead(self):
        "Once-asked Lazy 3: Once-asked lazy cells with changed called cells evaluate when called"
        self.failUnless(self.a.get() == 47)  # standard exam causes eval

class CellTypeTests_UntilAskedLazy(unittest.TestCase):
    def setUp(self):
        cells.reset()
        self.x = cells.InputCell(None, "x", 4)
        self.a = cells.UntilAskedLazyCell(None, "a",
                                     rule=lambda s,p: self.x.get() + 1)
        self.a.get(init=True)          # establish dependencies, a = 5
        self.x.set(42)                 # cause propogation
        
    def test_1_EvalOnRead(self):
        "Until-asked Lazy 1: Until-asked lazys with changed called cells are evaluated when called"
        self.failUnless(self.a.value == 5)   # sneaky exam doesn't cause eval
        self.failUnless(self.a.get() == 43)  # standard exam causes eval

    def test_2_ActsNormalAfterEval(self):
        "Until-asked Lazy 2: Until-asked lazys act like normal rule cells after initial evaluation"
        self.failUnless(self.a.value == 5)   # sneaky exam doesn't cause eval
        self.failUnless(self.a.get() == 43)  # standard exam causes eval
        self.x.set(5)                        # cause another propogation
        self.failUnless(self.a.value == 6)   # should have caused a's evaluation

class CellTypeTests_AlwaysLazy(unittest.TestCase):
    def test_1_NoEvalOnPropogation(self):
        "Always Lazy 1: Always lazys never evaluate on change propogation"
        cells.reset()
        x = cells.InputCell(None, "x", 4)
        a = cells.AlwaysLazyCell(None, "a", rule=lambda s,p: x.get() + (p or 1))

        a.get()                         # establish dependencies
        x.set(42)                       # cause propogation
        self.failUnless(a.value == 5)   # sneaky exam doesn't cause lazy eval
        self.failUnless(a.get() == 47)  # standard eval causes lazy eval
        x.set(5)                        # cause another propogation
        self.failUnless(a.value == 47)  # yadda yadda...
        self.failUnless(a.get() == 52)

if __name__ == "__main__":
    unittest.main()
