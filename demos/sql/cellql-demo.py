#!/usr/bin/env python

"""
CellQL Demo
===========

CellQL (pronounced "sell-kwull") is (well, will be) an interface to
several popular RDBMSs including SQLite, MySQL, PostgreSQL, and
Oracle. (Currently it supports SQLite, and only somewhat.)

This file is meant as a demo of the current state of the CellQL
library and something of a tutorial of its use, as it's currently
poorly documented.

Notice all those qualifications and parenthetical statements?
Good. CellQL is just a silly little diversion right now. I'm *really*
interested in making it something worth using, but for now it's just a
silly little thing to stick in the demos directory.
"""

import cellql
import copy

# I'm going to start with constructing the tables for the DB. Well,
# the table, as this demo's just going to deal with one. We use
# cellql.Table as a base class for tables:
class Contacts(cellql.Table):
    # Now let's add columns. First, the ever-popular name fields:
    fname = cellql.string()
    lname = cellql.string()

    # And, heck, an age might be good:
    age = cellql.integer()

    # And a free-form dictionary of phone numbers
    phone = cellql.blob()

print "Connecting to database..."

# We connect to the DB through a cellql.Database object. Handing it a
# connection string (which is, of course, a Cell) connects it to the
# RDBMS & database of our choice. We're going to use sqlite, as it's
# the only RDBMS supported by CellQL, and connect to the demo.sqlite
# database file in the local directory. You could connect to an
# arbitrary file on your filesystem with sqlite:///path/to/sqlite/file
db = cellql.Database(connection="sqlite://demo.sqlite")

# Now we'll tell the db to use the contacts table we defined above...
db.addtable(Contacts)

# When this connects, it runs some logic. If there's currently a table
# in the database named the same as the class just added, CellQL
# verifies the table's structure matches the classes. If it does, it
# makes the contents of that table available; if it doesn't -- or if
# the table doesn't exist -- it (re)creates the table in the database.

# So now we've connected to the db, and there's a table matching the
# Contacts class in the db. (You can do all this in an ipython session,
# then go in behind it at this point to verify the database is being
# built correctly if you don't believe me.)

# First, let's see how many rows are currently in the db:
rowcount = len(db.tables["Contacts"].rows)

# We add rows by creating a copy of the table class we want to add,
# modifying that instance, then pushing it into the database. Like so:
newrow = Contacts()
newrow.fname.value = "Guybrush"
newrow.lname.value = "Threepwood"
newrow.age.value = 17
newrow.phone.value = { "home": "(206) 555-1212",
		       "work": "(206) 543-2109" }
db.tables["Contacts"].rows.append(newrow)

# This will push a row into the database, automatically assigning it
# an index which we can use to retrieve it. Hey, that rowcount
# variable will come in handy here:
retrievedrow = db.tables["Contacts"].rows[rowcount]

# Now we can modify it...
retrievedrow.age.value = 21
phones = copy.copy(retrievedrow.phone.value)
phones["cell"] = "(206) 987-6543"
retrievedrow.phone.value = phones

# and push it back into the database, which will update the row in
# question:
db.tables["Contacts"].rows[rowcount] = retrievedrow

# This has a long ways to go, especially in regards to fitting with
# cells, but the framework is there and cellularity should be a
# relatively easy thing to add in the future.

