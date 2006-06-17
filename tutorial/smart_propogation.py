#!/usr/bin/env python

import unittest, sys, math
sys.path += "../"
import cells

runlog = []
MAIN = False

# So, we showed that the dependency graph can be an arbitrarily
# complex directed acyclic graph, and changes will propogate properly
# through it.  But if a node recalculates, and gets the same value as
# before, there's no need to keep propogating the recalculate command
# down the graph. Once again, let's build a model:
class Rectangle(cells.ModelObject):
    @cells.fun2cell()
    def length(self, prev):
        runlog.append("length")
        return 2 * self.width

    @cells.fun2cell()
    def width(self, prev):
        runlog.append("width")
        return math.floor(self.length / 2)

    @cells.fun2cell()
    def padded_width(self, prev):
        runlog.append("padded_width")
        return self.width + 10

    
# (And get a way to print it nicely)    
def rect_attribs(rect):
    buff = "Rectangle attributes:" 
    buff += "\n      Length = "+ str(rect.length)
    buff += "\n       Width = "+ str(rect.width)
    buff += "\nPadded Width = "+ str(rect.padded_width)
    buff += "\nRun Log:"+ str(runlog)
    return buff


class Test(unittest.TestCase):
    testnum = "02"
    
    def runTest(self):
        global runlog

        # So, one thing we need to show is that observers don't fire
        # if the value didn't change. We'll add an observer which will
        # fail the test if width's old == new
        @Rectangle.observer("width")
        def width_observer(modelobj, new, old, wasbound):
            global runlog
            self.failIf(new == old)
            if MAIN: print "Observing width. Is", str(new) + ", was", str(old)
            runlog.append("width_observer")

        # If that property can be proven, then a good way to show that
        # changes (or lack thereof) are or aren't propogating is to
        # attach an observer to them -- such as this observer on
        # length.
        @Rectangle.observer("length")
        def length_observer(modelobj, new, old, wasbound):
            global runlog
            runlog.append("length_observer")

        # Instantiate the model
        if MAIN: print "Instantiating Rectangle"
        rect = Rectangle(length=42)

        # Once again, show the model works
        self.failUnless(rect.width == 21)
        if MAIN: print rect_attribs(rect)
        
        # Now, check setting a cell doesn't propogate needlessly:
        # length is set, but doesn't change, so nothing should
        # propogate.
        runlog = []
        self.failUnless(rect.length == 42) # length is 42
        rect.length = 42                   # set it to 42
        if MAIN:
            print "Setting length to 42\n"
            print rect_attribs(rect)

        # Of course width isn't going to change:
        self.failUnless(rect.width == 21)
        # But less trivially, it *should not have been recalculated*
        # (and neither should anything else)
        uncalcd = [ "length_observer", "width", "width_observer",
                    "padded_width" ]
        for it in uncalcd:
            if MAIN: print it, "should not have been run"
            self.failIf(it in runlog)

        # Okay, but we also want to prove that propogations stop in
        # the middle of the dependency graph if values don't change as
        # a result of recalculation.
        runlog = []
        self.failUnless(rect.length == 42) # length is 42
        rect.length = 43                   # length changes
        if MAIN:
            print "Setting length to 43\n"
            print rect_attribs(rect)

        # This should have fired both the length observer and the
        # width recalculation.
        calcd = [ "width", "length_observer" ]
        for it in calcd:
            if MAIN: print it, "should have been run"
            self.failIf(it not in runlog)

        # However, width isn't going to change,
        # since its backing function runs `floor(length / 2)`.
        self.failUnless(rect.width == 21)
        
        # So, the propogation should have stopped there: width's
        # observer should not have fired, and padded_width should not
        # have been recalculated:
        uncalcd = [ "width_observer", "padded_width" ]
        for it in uncalcd:
            if MAIN: print it, "should not have been run"
            self.failIf(it in runlog)

        # Finally, let's show there's nothing up the tutorial's
        # sleeves: check setting a cell that should recalc the whole
        # dependency graph does:
        runlog = []
        rect.length = 44
        if MAIN:
            print "Setting length to 44\n"
            print rect_attribs(rect)
        self.failUnless(rect.width == 22)
        calcd = [ "length_observer", "width", "width_observer", "padded_width" ]
        for it in calcd:
            if MAIN: print it, "should have been run"
            self.failIf(it not in runlog)

            
if __name__ == "__main__":
    MAIN = True
    t = Test()
    t.runTest()
