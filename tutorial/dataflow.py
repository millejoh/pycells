#!/usr/bin/env python

import unittest, sys

sys.path += "../"

import cells

MAIN = False

class Rectangle(cells.ModelObject):
    def _widthcalc(self, prev):
        return self.length / 2

    def _lencalc(self, prev):
        return self.width * 2
    
    length = cells.makecell(name="length", function=_lencalc)
    width = cells.makecell(name="width")

    def __init__(self, width=_widthcalc, *args, **kwargs):
        cells.ModelObject.__init__(self, width=width, *args, **kwargs)
        
        
class Test(unittest.TestCase):
    testnum = "01a"

    def runTest(self):
        # (let ((r (make-instance 'rectangle :len (c-in 42))))
        if MAIN: print "Building rectangle."
        rect = Rectangle(length=42)
        # (cells::ct-assert (eql 21 (width r)))
        if MAIN: print "Rectangle.width =", str(rect.width)
        self.failUnless(rect.width == 21)
        # ;; make sure we did not break SETF, which must return the value set
        # (cells::ct-assert (= 1000 (setf (len r) 1000)))
        if MAIN: print "Setting Rectangle.length to 1000"
        rect.length = 1000
        if MAIN: print "Rectangle.length =", str(rect.length)
        self.failUnless(rect.length == 1000)   
        # ;; make sure new value propagated
        # (cells::ct-assert (eql 500 (width r))))
        if MAIN: print "Rectangle.width =", str(rect.width)
        self.failUnless(rect.width == 500)

if __name__ == "__main__":
    MAIN = True
    t = Test()
    t.runTest()
