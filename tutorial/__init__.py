import glob

"""Returns a list of unittests on PyCells

Find all modules in the tests directory other than this file. Then 
append a module.Test object to the suite. Order the suite by the objects' 
testnum attribute, and return.
"""
suite = []
    
# we assume all python files in this dir define tests. so, import each in turn,
# and get their tests ...
for modulename in glob.glob("tutorial/*.py"):
    if modulename == "tutorial/__init__.py": continue # er, except this one

    # so import the Test class from the module
    modulename = modulename.replace('/', '.')
    modulename = modulename[:-3]
    module = __import__(modulename, globals, locals, ['Test'])
    # and add it to the suite
    suite.append(module.Test())

# ... ordered by their testnum attribute.
suite.sort(cmp=lambda x, y: x.testnum > y.testnum)
