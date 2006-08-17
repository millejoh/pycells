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
    def setUp(self):
	self.con = sqlite.connect(TESTDB)
	self.cur = self.con.cursor()
    
    def tearDown(self):
	self.cur.close()
	self.con.close()
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

	try:
	    self.cur.execute("select * from Test")
	except sqlite.OperationalError, e:
	    self.fail("Caught OperationalError: " + str(e))
	
    def test_CreatedTableHasCellQLColumn(self):
	class Test(cellql.Table):
	    i = cellql.integer(value=0)

	class TestDB(cellql.Database):
	    connection = cells.makecell(value="sqlite://" + TESTDB)

	db = TestDB()
	db.addtable(Test)

	try:
	    self.cur.execute("select i from Test")
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

	self.cur.execute("select i from Test")
	l = self.cur.fetchall()
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

	self.cur.execute("select i, j from Test")
	l = self.cur.fetchall()
	self.failUnless(len(l) == 1)
	self.failUnless(l[0][0] == 5)
	self.failUnless(l[0][1] == 42)

    def test_RetrievingRowsFromExtantDB(self):
	class Test(cellql.Table):
	    i = cellql.integer(value=0)

	class TestDB(cellql.Database):
	    connection = cells.makecell(value="sqlite://" + TESTDB)

	self.cur.execute("CREATE TABLE Test (i INTEGER, " + \
		    "pk INTEGER PRIMARY KEY)")
	self.con.commit()
	self.cur.execute("INSERT INTO Test (i, pk) VALUES (5, 0)")
	self.cur.execute("INSERT INTO Test (i, pk) VALUES (42, 1)")
	self.con.commit()

	db = TestDB()
	db.addtable(Test)
	self.failUnless(len(db.tables["Test"].rows) == 2)
	row1 = db.tables["Test"].rows[0]
	self.failUnless(row1.i.value == 5)
	row2 = db.tables["Test"].rows[1]
	self.failUnless(row2.i.value == 42)

    def test_SetExtantRow(self):
	class Test(cellql.Table):
	    i = cellql.integer(value=0)

	class TestDB(cellql.Database):
	    connection = cells.makecell(value="sqlite://" + TESTDB)

	# first i'll manually create a db
	self.cur.execute("CREATE TABLE Test (i INTEGER, " + \
		    "pk INTEGER PRIMARY KEY)")
	self.con.commit()
	self.cur.execute("INSERT INTO Test (i, pk) VALUES (5, 0)")
	self.cur.execute("INSERT INTO Test (i, pk) VALUES (42, 1)")
	self.con.commit()

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
	self.cur.execute("SELECT i FROM Test WHERE pk=0")
	l = self.cur.fetchall()
	self.failUnless(len(l) == 1)
	self.failUnless(l[0][0] == 13)
	# tada!

    def test_RowTypesInsertAndRetrieve(self):
	class Test(cellql.Table):
	    s = cellql.string()
	    r = cellql.real()
	    b = cellql.blob()
	    i = cellql.integer()

	db = cellql.Database(connection="sqlite://" + TESTDB)
	db.addtable(Test)

	orig_s = "Foo"
	orig_r = 3.14
	orig_b = { "complex": "objects",
		   "can": "be",
		   "stored in": "blobs!" }
	orig_i = 5
	
	newrow = Test()
	newrow.s.value = orig_s
	newrow.r.value = orig_r
	newrow.b.value = orig_b
	newrow.i.value = orig_i
	db.tables["Test"].rows[0] = newrow

	self.cur.execute("SELECT s,r,b,i FROM Test WHERE pk=0")
	db_s, db_r, db_b, db_i = self.cur.fetchall()[0]

	retrieved_row = Test()
	self.failUnless(orig_s ==
			retrieved_row.s.translate_from_sql(db_s))
	self.failUnless(round(orig_r, 3) ==
			round(retrieved_row.r.translate_from_sql(db_r), 3))
	self.failUnless(orig_i ==
			retrieved_row.i.translate_from_sql(db_i))

	translated_db_b = retrieved_row.b.translate_from_sql(db_b)
	self.failUnless(set(translated_db_b.keys()) == set(orig_b.keys()))
	for key, value in orig_b.iteritems():
	    self.failUnless(translated_db_b[key] == value)
	
	
	
if __name__ == "__main__":
    unittest.main()
