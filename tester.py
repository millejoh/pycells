#!/usr/bin/env python

import tutorial, unittest, cells

tests = unittest.TestSuite()
tests.addTests(tutorial.suite)
runner = unittest.TextTestRunner()    
runner.run(tests)
