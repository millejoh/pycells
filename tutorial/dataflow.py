#!/usr/bin/env python

import unittest, sys
sys.path += "../"
import cells

MAIN = False

# The first step in any cells project is your model object. Subclass!
class Rectangle(cells.ModelObject):
    # there are several ways to add cells to your model object. the first
    # is to use the fun2cell decorator:
    @cells.fun2cell()           # (we'll talk about its parameters later)
    # cell functions need a specific signature. the `self` here acts just like
    # a standard class's method's `self` -- that is, it refers to this model obj
    def length(self, prev):     # it builds a cell named the same as your func
        return self.width * 2   # and uses the function to produce its values
    
    # you can also use a package function to build cells
    width = cells.makecell(name="width") # (this name=... business will change)

    def _widthcalc(self, prev):
        return self.length / 2

    # PyCells also does some magic with init names; if a keyword argument to
    # init matches a cell, it overrides the class-level definition. If you pass
    # in a callable, PyCells assumes you want to make that cell a RuleCell and
    # use the passed callable as the backing function for that cell. If you pass
    # in a hash with specific keys, it uses those as arguments for the cell.
    def __init__(self, width=_widthcalc, *args, **kwargs):
        # Here, we're overriding the "width" cell's initialization with the passed
        # function, and using the _widthcalc function as a default. Silly, but
        # illustrative.
        cells.ModelObject.__init__(self, width=width, *args, **kwargs)

        
class Test(unittest.TestCase):
    testnum = "01a"

    def runTest(self):
        # So now, let's use the model object we defined above. First, let's get
        # an instance of it:
        if MAIN: print "Building rectangle."
        rect = Rectangle(length=42)
        # Note that we overrode lenth's initialization; instead of a RuleCell,
        # the length cell is now a ValueCell.

        # We can now get the value of width, which calculated in the background
        # during initialization:
        if MAIN: print "Rectangle.width =", str(rect.width)
        self.failUnless(rect.width == 21)

        # The calculations happen whenever we alter length, though:
        if MAIN: print "Setting Rectangle.length to 1000"
        rect.length = 1000              # We can set the cell's value as if it 
        if MAIN: print "Rectangle.length =", str(rect.length) # were a standard
        self.failUnless(rect.length == 1000)                  # attribute.

        # And, as you can see, width keeps up:
        if MAIN: print "Rectangle.width =", str(rect.width)
        self.failUnless(rect.width == 500)

if __name__ == "__main__":
    MAIN = True
    t = Test()
    t.runTest()
