#!/usr/bin/env python

import unittest, sys

sys.path += "../"

import cells

class Rectangle(cells.ModelObject):
    def _widthcalc(self, prev):
        return self.length / 2

    def _lencalc(self, prev):
        return self.width * 2
    
    length = cells.makecell(initarg="length", initform=_lencalc)
    width = cells.makecell(initarg="width", initform=_widthcalc)
        
class Test(unittest.TestCase):
    testnum = "01a"

    def runTest(self):
        # (let ((r (make-instance 'rectangle :len (c-in 42))))
        rect = Rectangle()
        rect.length = 42
        # (cells::ct-assert (eql 21 (width r)))
        self.failUnless(rect.width == 21)
        # ;; make sure we did not break SETF, which must return the value set
        # (cells::ct-assert (= 1000 (setf (len r) 1000)))
        rect.length = 1000
        self.failUnless(rect.length == 1000)        
        # ;; make sure new value propagated
        # (cells::ct-assert (eql 500 (width r))))
        self.failUnless(rect.width == 500)
