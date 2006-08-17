#!/usr/bin/env python

"""
CellQL Testing
"""

import cellql, cells
import unittest
import os
from pysqlite2 import dbapi2 as sqlite

TESTDB = "TestDB"

class Sqlite_CellQLTests(unittest.TestCase):
    def tearDown(self):
	cells.cell.DEBUG = False
	os.unlink(TESTDB)
	
    def test_Init(self):
	con = cellql.Database(connection="sqlite://" + TESTDB)	
	self.failIf(con.connected is False)

    def test_SubclassInit(self):
	class TestDB(cellql.Database):
	    pass
	
	con = TestDB(connection="sqlite://" + TESTDB)
	self.failIf(con.connected is False)

    def test_SubclassWithTable(self):
	class Test(cellql.Table):
	    pass
	    
	class TestDB(cellql.Database):
	    connection = cells.makecell(value="sqlite://" + TESTDB)

	db = TestDB()
	db.addtable(Test)
	self.failUnless(list(db.tables["Test"].rows) == [])

    def test_TableWithIntegerColumn(self):
	class Test(cellql.Table):
	    i = cellql.integer(value=0)

	class TestDB(cellql.Database):
	    connection = cells.makecell(value="sqlite://" + TESTDB)

	db = TestDB()
	db.make_kid(Test)
	self.failUnless("i" in [ _.name for _ in db.tables["Test"].columns ])

    def test_CellQLTableCreatesDBTable(self):
	class Test(cellql.Table):
	    i = cellql.integer(value=0)

	class TestDB(cellql.Database):
	    connection = cells.makecell(value="sqlite://" + TESTDB)

	db = TestDB()
	db.addtable(Test)

	con = sqlite.connect(TESTDB)
	cur = con.cursor()
	try:
	    cur.execute("select * from Test")
	except sqlite.OperationalError, e:
	    self.fail("Caught OperationalError: " + str(e))
	
    def test_CreatedTableHasCellQLColumn(self):
	class Test(cellql.Table):
	    i = cellql.integer(value=0)

	class TestDB(cellql.Database):
	    connection = cells.makecell(value="sqlite://" + TESTDB)

	db = TestDB()
	db.addtable(Test)

	con = sqlite.connect(TESTDB)
	cur = con.cursor()
	try:
	    cur.execute("select i from Test")
	except sqlite.OperationalError, e:
	    self.fail("Caught OperationalError: " + str(e))

    def test_InsertingValueReflectedInDB(self):
	class Test(cellql.Table):
	    i = cellql.integer(value=0)

	class TestDB(cellql.Database):
	    connection = cells.makecell(value="sqlite://" + TESTDB)

	db = TestDB()
	db.addtable(Test)	
	newrow = Test()
	newrow.i.value = 5
	db.tables["Test"].rows.append(newrow)

	con = sqlite.connect(TESTDB)
	cur = con.cursor()
	cur.execute("select i from Test")
	l = cur.fetchall()
	self.failUnless(len(l) == 1)
	self.failUnless(l[0][0] == 5)

    def test_InsertingMultipleValues(self):
	class Test(cellql.Table):
	    i = cellql.integer(value=0)
	    j = cellql.integer(value=0)

	class TestDB(cellql.Database):
	    connection = cells.makecell(value="sqlite://" + TESTDB)

	db = TestDB()
	db.addtable(Test)	
	newrow = Test()
	newrow.i.value = 5
	newrow.j.value = 42
	db.tables["Test"].rows.append(newrow)

	con = sqlite.connect(TESTDB)
	cur = con.cursor()
	cur.execute("select i, j from Test")
	l = cur.fetchall()
	self.failUnless(len(l) == 1)
	self.failUnless(l[0][0] == 5)
	self.failUnless(l[0][1] == 42)

    def test_RetrievingRowsFromExtantDB(self):
	class Test(cellql.Table):
	    i = cellql.integer(value=0)

	class TestDB(cellql.Database):
	    connection = cells.makecell(value="sqlite://" + TESTDB)

	con = sqlite.connect(TESTDB)
	cur = con.cursor()
	cur.execute("CREATE TABLE Test (i INTEGER, " + \
		    "pk INTEGER PRIMARY KEY)")
	con.commit()
	cur.execute("INSERT INTO Test (i, pk) VALUES (5, 0)")
	cur.execute("INSERT INTO Test (i, pk) VALUES (42, 1)")
	con.commit()

	db = TestDB()
	db.addtable(Test)
	self.failUnless(len(db.tables["Test"].rows) == 2)
	row = db.tables["Test"].rows[0]
	print "--->", row.i.value
	self.failUnless(row.i.value == 5)
	row = db.tables["Test"].rows[1]
	self.failUnless(row.i.value == 42)

    def test_ModifyExtantRow(self):
	class Test(cellql.Table):
	    i = cellql.integer(value=0)

	class TestDB(cellql.Database):
	    connection = cells.makecell(value="sqlite://" + TESTDB)

	# first i'll manually create a db
	con = sqlite.connect(TESTDB)
	cur = con.cursor()
	cur.execute("CREATE TABLE Test (i INTEGER, " + \
		    "pk INTEGER PRIMARY KEY)")
	con.commit()
	cur.execute("INSERT INTO Test (i, pk) VALUES (5, 0)")
	cur.execute("INSERT INTO Test (i, pk) VALUES (42, 1)")
	con.commit()

	cellql.DEBUG = True

	# then i'll get a cellql db object
	db = TestDB()
	db.addtable(Test)	# and connect it to the premade table

	# and show the connection found the extant rows
	self.failIf(db.tables["Test"].rows[0] is None)

	# now i'll make a new row
	newrow = Test()
	newrow.i.value = 13

	# and insert it into the db at a currently-occupied position
	db.tables["Test"].rows[0] = newrow

	# now i'll go in the back door again to see if it was
	# reflected in the actual db
	cur.execute("SELECT i FROM Test WHERE pk=0")
	l = cur.fetchall()
	self.failUnless(len(l) == 1)
	self.failUnless(l[0][0] == 13)
	# tada!	
	
	
if __name__ == "__main__":
    unittest.main()
