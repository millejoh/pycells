#!/usr/bin/env python

import unittest, sys
sys.path += "../"
import cells

"""
A Family object is a type of Model. It provides everything a Model
provides, plus the following:

1. A kids attribute, which holds an ordered sequence of Models.

2. A kid_slots attribute, which is akin to a blueprint for the Models
   in the kids list.

3. If a Model in a kids list defines an attribute which is also
   defined in the kid_slots blueprint, the attribute in kid_slots
   overrides the Model's definition.

4. Provides the following convenience methods:
   * grandparent: the parent's parent, or None
   * kid_number: this Model's position in the parent's kids list
   * previous_sib: the sibiling Model in parent.kids[kid_number - 1]
   * next_sib: the sibiling Model in parent.kids[kid_number + 1]
   
"""

class FamilyTest(unittest.TestCase):
    def setUp(self):
        cells.reset()
        
        class K(cells.Family):
            x = cells.makecell(value=1)
            model_value = cells.makecell(rule=lambda s,p: s.x * 3)
            
        class F(cells.Family):
            kid_slots = cells.makecell(value=K)

        self.F = F
        self.K = K

    def tearDown(self):
        del(self.F)
        del(self.K)
        
    def test_KidsAttrib(self):
        f = self.F()

        for word in ("Eyy", "Bee", "See"):
            class A(cells.Model):
                model_name = cells.makecell(value=word)

            f.make_kid(A)

        self.failUnless(3 == len(f.kids))
        self.failUnless(f.kids[0].model_name == "Eyy")
        self.failUnless(f.kids[1].model_name == "Bee")
        self.failUnless(f.kids[2].model_name == "See")

    def test_KidslotsAttrib(self):
        f = self.F()

        # this class will get all of its attribs from the kid slot
        class A(cells.Model):
            pass

        # model_name will not be overridden
        class B(cells.Model):
            model_name = cells.makecell(value="Bee")

        # this class will have its defined attrib overridden
        class C(cells.Model):
            model_value = cells.makecell(rule=lambda s,p: s.x * 10)

        f.make_kid(A)
        f.make_kid(B)
        f.make_kid(C)

        self.failUnless(f.kids[0].x == 1)
        self.failUnless(f.kids[1].model_name == "Bee")
        self.failUnless(f.kids[2].model_value == 3)

    def test_GrandparentMethod(self):
        f = self.F()
        f.make_kid(self.F)
        f.kids[0].make_kid(self.K)
        self.failUnless(f.kids[0].kids[0].grandparent() is f)

    def test_SiblingMethods(self):
        f = self.F()
        f.make_kid(self.K)
        f.make_kid(self.K)

        kidA = f.kids[0]
        kidB = f.kids[1]

        self.failUnless(kidA.next_sib() is kidB)
        self.failUnlessRaises(cells.FamilyTraversalError, kidB.next_sib)

        self.failUnlessRaises(cells.FamilyTraversalError, kidA.previous_sib)
        self.failUnless(kidB.previous_sib() is kidA)

    def test_PositionMethod(self):
        f = self.F()
        f.make_kid(self.K)
        f.make_kid(self.K)

        kidA = f.kids[0]
        kidB = f.kids[1]

        self.failUnless(kidA.position() == 0)
        self.failUnless(kidB.position() == 1)

if __name__ == "__main__": unittest.main()
    
