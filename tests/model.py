#!/usr/bin/env python

import unittest, sys
sys.path += "../"
import cells

"""
And now, the model:

1. Simplifies the creation of cells as attributes; on model instance init, the
   model runs each cell in turn in order to initialize the dependency graph.

2. Allow overriding instance cells at initialization

3. Allow non-cell attributes to be created at init, but disallow changes to
   those attributes after init.

4. Must provide an instance of itself to its RuledCell attributes.

5. Provides an interface for observers to be added to the model.

6. Observers must be allowed to associate with a:
   * model
   * specific attribute (even non-Cell attributes)
   * new value (or, when a user-defined function runs on the new value and
     returns True, the observer runs)
   * type of old value (as above)
   * bound value (that is, if a cell had a previous value)

7. (To research/ask about: post-propogation task queue?)

8. (To research/ask about: all observers run only once per DP change?)

9. A model provides the following cells:
   * model_name: the name of this Model object   
   * model_value: a way to reduce the Model to a single value; returns
     None by default     
   * parent: a way to set a 'parent' Model in a graph of Models -- see
     Family for a bit more about this
     
"""

class SimpleModelTests(unittest.TestCase):
    def setUp(self):
        cells.reset()
        self.a_ran = False
        
        class MyModel(cells.Model):
            x = cells.makecell(value=5)

            @cells.fun2cell()
            def a(modelself, prev):
                self.a_ran = True
                return modelself.x + modelself.offset

            def __init__(self, *args, **kwargs):
                self.offset = 1
                cells.Model.__init__(self, *args, **kwargs)

        self.M = MyModel
        
    def test_ModelCellAttrTests(self):
        "Cell attributes should act like cells"
        # a should have run on init
        m = self.M()
        self.failUnless(self.a_ran)
        m.x = 4                         # should propogate change
        self.failUnless(m.a == 5)       # (proves deps are working)
        # (note that this also shows a's rule is getting the model instance as
        # its first arg)

        # show the set is getting to the cell (which should raise an excep'n)
        raisedflag = False
        try:
            m.a = 5            
        except cells.RuleCellSetError, e:
            return

        self.fail()

    def test_NoSettingNonCells(self):
        "Non-cell attributes of a model should not be settable after init"
        try:
            self.M().offset = 2
        except cells.NonCellSetError, e:
            return

        self.fail()

    def test_OverrideCells(self):
        m = self.M(a=lambda s,p: s.x + s.offset + 10)
        self.failUnless(m.a == 16)

    def test_Inheritance(self):
        self.b_ran = False
        class AnotherModel(self.M):
            @cells.fun2cell()
            def b(model, prev):
                self.b_ran = True
                return model.x + model.a

        n = AnotherModel()
        self.b_ran = False
        self.failUnless(n.x == 5)
        self.failUnless(n.a == 6)
        self.failUnless(n.b == 11)
        self.failIf(self.b_ran)

        # test overriding inherited Cell attrib
        self.modified_a_ran = False
        class YetAnother(self.M):
            @cells.fun2cell()
            def a(modelself, prev):
                self.modified_a_ran = True
                return modelself.x * 10

        o = YetAnother()
        self.modified_a_ran = False
        self.failUnless(o.x == 5)
        self.failUnless(o.a == 50)
        self.failIf(self.modified_a_ran)

        o.x = 1
        self.failUnless(o.x == 1)
        self.failUnless(o.a == 10)
        self.failUnless(self.modified_a_ran)

    def test_hasName(self):
        self.failUnless(self.M().model_name == None)

    def test_hasValue(self):
        self.failUnless(self.M().model_value == None)

    def test_hasParent(self):
        self.failUnless(self.M().parent == None)

                
        
class ObserverTests(unittest.TestCase):
    def setUp(self):
        cells.reset()
        self.observerlog = []
        
        class MyModel(cells.Model):
            x = cells.makecell(value=5)
            a = cells.makecell(rule=lambda s,p: int(s.x) + s.offset)
            offset = 2

        # observes whole model
        @MyModel.observer()
        def model_obs(model):
            self.observerlog.append("model")

        # observes an input cell instance
        @MyModel.observer(attrib="x")
        def incell_obs(model):
            self.observerlog.append("x")

        # observes a rule cell instance
        @MyModel.observer(attrib="a")
        def rulecell_obs(model):
            self.observerlog.append("a")

        # observes a non-cell instance
        @MyModel.observer(attrib="offset")
        def noncell_obs(model):
            self.observerlog.append("offset")

        # observe an old value type
        @MyModel.observer(oldvalue=lambda v: type(v) == type(1))
        def oldval_obs(model):
            self.observerlog.append("oldval")
                
        # observe a new value type
        @MyModel.observer(newvalue=lambda v: type(v) == type(1.0))
        def newval_obs(model):
            self.observerlog.append("newval")
            
        self.M = MyModel
        self.m = MyModel()            # this will test the very basics

    def test_ModelObserver(self):
        "Test whole-model observer"
        # a whole model observer should run once, and only once, per
        # perturbation:
        self.observerlog = []
        self.m.x = 2

        self.failUnless(1 == self.observerlog.count("model"))

        # but should not run during reads:
        self.observerlog = []
        self.m.x
        self.failUnless("model" not in self.observerlog)

    def test_InputCellObserver(self):
        "Test the observer for a input cell"
        # cell's observer should run once every time its value changes
        self.observerlog = []
        self.m.x = 2
        self.failUnless(1 == self.observerlog.count("x"))
        # but only when it's value *changes*
        self.observerlog = []
        self.m.x = 2
        self.failIf("x" in self.observerlog)

    def test_RuleCellObserver(self):
        "Test the observer for a rule cell"
        # see above
        self.observerlog = []
        self.m.x = 2
        self.failUnless(1 == self.observerlog.count("a"))
        self.observerlog = []
        self.m.x = 2
        self.failIf("a" in self.observerlog)
        self.observerlog = []
        self.m.x = 2.2            # a's rule trunc's, so this doesn't 
        self.failIf("a" in self.observerlog) # change a's value

    def test_NonCellObserver(self):
        "Verify non-cell observers run at init"
        self.failUnless(1 == self.observerlog.count("offset"))

    def test_OldValueObserver(self):
        "Old value observers should run when the old value of the cell matches what the observer is looking for"
        # right now, x and a both have type(int), which is what the observer
        # is looking for. So:
        self.observerlog = []
        self.m.x = 2.2
        self.failUnless(1 == self.observerlog.count("oldval"))
        self.observerlog = []
        self.m.x = 3.3          # x changes, but its old val was float
        self.failUnless(1 == self.observerlog.count("oldval")) # a's was int

    def test_NewValueObserver(self):
        "New value is just like old value, but new."
        # no, y'see, this one goes to 11...
        self.observerlog = []
        self.m.x = 3
        self.failUnless(1 == self.observerlog.count("oldval"))
        self.observerlog = []
        self.m.x = 2.3
        self.failUnless(1 == self.observerlog.count("oldval"))

    def test_ObserverMultipleObjects(self):
        "Observers should act correctly with multiple instances of a MO"
        # this test is a little different than the others, so
        cells.reset()
        self.observerlog = []
        a = self.M()                    # this should fire the model obs
        b = self.M()                    # as should this
        self.failUnless(2 == self.observerlog.count("model"))
        
    def test_ObserverInheritance(self):
        "Observers should inherit with few surprises."
        class N(self.M):
            # modify an attribute the observers are looking for
            a = cells.makecell(rule=lambda s,p: int(s.x) * s.offset)

        # override one of the observers
        @N.observer(attrib="a")
        def rulecell_obs(model):
            # make it a bit more fonzie
            self.observerlog.append("Eyyy!")

        # and add a new observer
        @N.observer()
        def model2_obs(model):
            self.observerlog.append("model2")

        n = N()

        self.observerlog = []
        n.x = 2
        self.failUnless(1 == self.observerlog.count("Eyyy!"))
        self.failUnless(1 == self.observerlog.count("model2"))
        self.failIf(self.observerlog.count("a"))

            
if __name__ == "__main__":
    unittest.main()
        
        
