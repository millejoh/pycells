#!/usr/bin/env python


import unittest, sys
sys.path += "../"
import cells

"""
There are several types of cells. These are their rules:

Input Cells:
1. Must be 'set'able
2. A set during propogation must defer until the propogation is complete
3. Trying to .run() a input cell raises an exception

DictCells:
1. Act like InputCells
2. Also propogate changes if the hash is changed -- ie, if a key is
   set to a different value.

Rule Cells:
1. Trying to set a rule cell throws an exception

Rule Then Input Cells:
1. Evaluates once at init, sets its value, and then acts like an InputCell

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
2. Does not evaluate during model init

Ephemeral Cells:
1. After propogation, their value is returned to None
"""

class CellTypeTests_Input(unittest.TestCase):
    def setUp(self):
        cells.reset()
        self.x = cells.InputCell(None, 5, name="x")

    def test_1_Settability(self):
        "Input 1: An input cell must be settable"
        try:
            self.x.set(4)
        except Exception as e:
            self.fail()

    def test_2_SetDuringPropogation(self):
        "Input 2: A set during propogation must defer until propogation is complete"
        a = cells.RuleCell(None, lambda s,p: self.x.getvalue() * 3, name="a")

        self.captured_x = None
        def d_rule(s,p):
            self.x.set(2)
            if not self.captured_x:
                self.captured_x = self.x.value
            return a.getvalue()
        d = cells.RuleCell(None, d_rule, name="d")

        # establish dependencies.
        d.getvalue()                         # x.value = 2, now.
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
    def test_1a_Nonsettability(self):
        "Rule 1: Rule cells may not be set"
        cells.reset()
        x = cells.RuleCell(None, lambda s,p: 0, name="x")
        self.failUnlessRaises(cells.RuleCellSetError, x.set, 5)

class CellTypeTests_RuleThenInput(unittest.TestCase):
    def test_1b_RunRaisesAfterEval(self):
        """Rule 1: 1. Evaluates once at init, sets its value, and then
        acts like an InputCell.
        """
        cells.reset()
        x = cells.RuleThenInputCell(None, rule=lambda s,p: 0, name="x")
        x.getvalue()
        self.failUnlessRaises(cells.InputCellRunError, x.run)

class CellTypeTests_OnceAskedLazy(unittest.TestCase):
    def setUp(self):
        cells.reset()
        self.x = cells.InputCell(None, 4, name="x")
        self.a = cells.OnceAskedLazyCell(None, name="a",
                                         rule=lambda s,p: self.x.getvalue()+(p or 1))

        self.a.getvalue()                         # establish dependencies
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
        self.failUnless(self.a.getvalue() == 47)  # standard exam causes eval

class CellTypeTests_UntilAskedLazy(unittest.TestCase):
    def setUp(self):
        cells.reset()
        self.x = cells.InputCell(None, 4, name="x")
        self.a = cells.UntilAskedLazyCell(None, name="a",
                                     rule=lambda s,p: self.x.getvalue() + 1)
        self.a.getvalue(init=True)          # establish dependencies, a = 5
        self.x.set(42)                 # cause propogation

    def test_1_EvalOnRead(self):
        "Until-asked Lazy 1: Until-asked lazys with changed called cells are evaluated when called"
        self.failUnless(self.a.value == 5)   # sneaky exam doesn't cause eval
        self.failUnless(self.a.getvalue() == 43)  # standard exam causes eval

    def test_2_ActsNormalAfterEval(self):
        "Until-asked Lazy 2: Until-asked lazys act like normal rule cells after initial evaluation"
        self.failUnless(self.a.value == 5)   # sneaky exam doesn't cause eval
        self.failUnless(self.a.getvalue() == 43)  # standard exam causes eval
        self.x.set(5)                        # cause another propogation
        self.failUnless(self.a.value == 6)   # should have caused a's evaluation

class CellTypeTests_AlwaysLazy(unittest.TestCase):
    def test_1_NoEvalOnPropogation(self):
        "Always Lazy 1: Always lazys never evaluate on change propogation"
        cells.reset()
        x = cells.InputCell(None, 4, name="x")
        a = cells.AlwaysLazyCell(None, name="a",
                                 rule=lambda s,p: x.getvalue() + (p or 1))

        a.getvalue()                         # establish dependencies
        x.set(42)                       # cause propogation
        self.failUnless(a.value == 5)   # sneaky exam doesn't cause lazy eval
        self.failUnless(a.getvalue() == 47)  # standard eval causes lazy eval
        x.set(5)                        # cause another propogation
        self.failUnless(a.value == 47)  # yadda yadda...
        self.failUnless(a.getvalue() == 52)

    def test_2_NoEvalOnInit(self):
        "Always Lazy 2: Does not evaluate during model init"
        cells.reset()
        ran_flag = False

        def a_rule(self, prev):
            ran_flag = True
            return self.x + 2

        class M(cells.Model):
            x = cells.makecell(value=3)
            a = cells.makecell(rule=a_rule, celltype=cells.AlwaysLazyCell)

        m = M()
        self.failIf(ran_flag)
        self.failUnless(m.a == 5)

class CellTypeTests_DictTests(unittest.TestCase):
    def setUp(self):
        cells.reset()
        self.x = cells.DictCell(None, name="x")

    def test_1_DictCellSettable(self):
        try:
            self.x.set({'blah': 'blah blippity bloo'})
        except Exception as e:
            self.fail()

    def test_2_RunRaises(self):
        self.failUnlessRaises(cells.InputCellRunError, self.x.run)

    def test_3_ChangingKeyValuePropogates(self):
        def y_rule(model, prev):
            return self.x.keys()

        y = cells.Cell(None, name="y", rule=y_rule)
        y.getvalue()                         # establish deps
        self.failUnless(y.getvalue() == [])  # no keys in x yet
        self.x['foo'] = 'blah blah'     # cause propogation
        self.failUnless(y.getvalue() == ['foo'])

class CellTypeTests_Ephemerals(unittest.TestCase):
    def test_Ephemeral(self):
        x = cells.InputCell(None, name="x", value=None, ephemeral=True)
        y = cells.RuleCell(None, name="y", rule=lambda s,p: x.getvalue())
        y.getvalue()		# establish dep
        s = "Foobar"
        x.set(s)		# propogate change
        self.failUnless(y.getvalue() == s) # y should have got the new value
        self.failUnless(x.getvalue() is None) # but x should be back to None

if __name__ == "__main__":
    unittest.main()
