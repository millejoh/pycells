import unittest, sys

sys.path += "../"

import cells

class Rectangle(cells.ModelObject):
    def _widthcalc(self, prev):
        return self.length / 2

    def _lencalc(self, prev):
        return self.width * 2
    
    length = cells.makecell(name="length", function=_lencalc)
    width = cells.makecell(name="width")

    def __init__(self, width=_widthcalc, *args, **kwargs):
        cells.ModelObject.__init__(self, width=width, *args, **kwargs)

# (defobserver len ((self rectangle) new-value old-value old-value-bound-p)
#   ;; Where rectangle is a GUI element, we need to tell the GUI framework
#   ;; to update this area of the screen
#   (setf *gui-told* t)
#   (print (list "tell GUI about" self new-value old-value old-value-bound-p)))
@cells.observer(Rectangle, "length")
def len_observer(new, old, bound):
    global GUI_TOLD
    GUI_TOLD = True
    # since this is running as a test, I don't actually want to print anything
    #print "Tell GUI about", str(new), str(old), str(bound)
    
class Test(unittest.TestCase):
    testnum = "01b"

    def runTest(self):
        # (let* ((*gui-told* nil)
        #        (r (make-instance 'rectangle :len (c-in 42))))
        global GUI_TOLD                 # yuck.
        GUI_TOLD = False
        rect = Rectangle()
        rect.length = 42
        
        #   (cells::ct-assert *gui-told*)
        #   (cells::ct-assert (eql 21 (width r)))
        self.failUnless(GUI_TOLD)
        self.failUnless(rect.width == 21)

        #   (setf *gui-told* nil)
        GUI_TOLD = False
        
        #   (cells::ct-assert (= 1000 (setf (len r) 1000)))
        #   (cells::ct-assert *gui-told*)
        #   (cells::ct-assert (eql 500 (width r))))
        rect.length = 1000
        self.failUnless(rect.length == 1000)
        self.failUnless(GUI_TOLD)
        self.failUnless(rect.width == 500)

