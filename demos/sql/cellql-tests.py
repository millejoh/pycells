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
	self.failUnless([ _.name for _ in db.tables["Test"].columns ] == ["i"])

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
		    "Test_index INTEGER PRIMARY KEY)")
	con.commit()
	cur.execute("INSERT INTO Test (i, Test_index) VALUES (5, 0)")
	cur.execute("INSERT INTO Test (i, Test_index) VALUES (42, 1)")

	db = TestDB()
	db.loadtable(Test)
	self.failUnless(len(db.tables["Test"].rows) == 2)
	row = db.tables["Test"].rows[0]
	self.failUnless(row.i.value == 5)
	row = db.tables["Test"].rows[1]
	self.failUnless(row.i.value == 42)
	
	
if __name__ == "__main__":
    unittest.main()
