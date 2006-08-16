"""
CellQL: A Cells interface to RDBMSs.

CellQL (sell-kwall) is an interface to database management systems.
Currently it only interfaces in a limited way with SQLite, but a more
complete interface to more RDBMS systems is planned.

(A short example of usage will go here.)
"""

import cells
import pickle

DEBUG = False

def _debug(*msgs):
    if DEBUG:
	print " ".join([ str(msg) for msg in msgs ])

def integer(value=0, *args, **kwargs):
    return cells.CellAttr(value=Integer(value=value), *args, **kwargs)

class Column(cells.Model):
    value = cells.makecell(value=None)
    name = cells.makecell(value="anonymous")
    table = cells.makecell(value=None)

    @cells.fun2cell()
    def create_column_string(self, prev):
	return self.name + " BLOB"

    @cells.fun2cell()
    def sql_value(self, prev):
	return pickle.dumps(self.value)

    
class Integer(Column):
    value = cells.makecell(value=0)

    @cells.fun2cell()
    def create_column_string(self, prev):
	return self.name + " INTEGER"

    @cells.fun2cell()
    def sql_value(self, prev):
	return str(self.value)

    
class Table(cells.Family):
    def __init__(self, *args, **kwargs):
	cells.Model.__init__(self, *args, **kwargs)

	for attr in self.__dict__.keys():
	    val = getattr(self, attr)
	    if isinstance(val, Column):
		val.name = attr
		val.table = self
		self.columns.append(val)

    columns = cells.makecell(celltype=cells.ListCell)
    rows = cells.makecell(celltype=cells.ListCell)
    inserted = cells.makecell(value=False)
    
    @cells.fun2cell(celltype=cells.RuleThenInputCell)
    def name(self, prev):
	return self.__class__.__name__
    
    # Sometimes a Table object acts like a Table, and so we need a
    # "create table" string to feed to the RDBMS
    @cells.fun2cell()
    def create_table_string(self, prev):
	collist = [ column.create_column_string for column in self.columns ]
	collist.append(self.name + "_index INTEGER PRIMARY KEY")
	return "CREATE TABLE " + self.name + "(" + ",\n".join(collist) + ")"

    # Other times the Table object acts like a row in a table, so we
    # need an "insert into" string to feed to the RDBMS when this row
    # is created
    @cells.fun2cell()
    def insert_string(self, prev):
	return "INSERT INTO " + self.name + \
	    " (" + ",".join([ _.name for _ in self.columns ]) + ") " + \
	    "VALUES (" + ",".join([ getattr(self, column.name).sql_value
				    for column in self.columns ]) + ")"
    
    @cells.fun2cell()
    def needs_rebuild(self, prev):
	"""Returns boolean if this table needs to be rebuilt in the DB"""
	if not self.parent:
	    return False	# we don't rebuild if there's no DB
				# (that is, if this is a row or only
				# partially initialized)

	cur = self.parent._rawcon.cursor()
	# Does the DB have this table?
	try:
	    s = "select * from " + self.name + " limit 1"
	    _debug(s)
	    cur.execute(s)
	except self.parent._rdbmsmodule.OperationalError:
	    return True	# Nope!
	
	# Are the DB's table's columns in sync with the model's columns?
	if not set([ _.name for _ in self.columns ]) == \
		set([ _[0] for _ in cur.description ]):
	    return True
	# TODO: Hrmph. I need to figure out how to verify each
	# column's datatype in SQL is the same as what's in the Table
	# model.

	# If it passed all the above, it looks right
	return False
     
@Table.observer(attrib="needs_rebuild")
def rebuild_observer(model):
    if model.needs_rebuild:
	cur = model.parent._rawcon.cursor()
	s = model.create_table_string
	_debug(s)
	cur.execute(s)
	model.parent._rawcon.commit()

@Table.observer(attrib="rows")
def insert_new_row(model):
    if model.rows:
	cur = model.parent._rawcon.cursor()
	for uninserted in filter(lambda row: row.inserted == False, model.rows):
	    s = uninserted.insert_string
	    _debug(s)
	    cur.execute(s)
	    
	    uninserted.inserted = True
	model.parent._rawcon.commit()
	
	    
class Database(cells.Family):
    """Class for interaction with a database.

    (Short example of init usage here)
    """
    # Public Non-Cells
    supported_rdbms = ("sqlite",)

    addtable = cells.Family.make_kid

    # Public Cells
    connection = cells.makecell(value="")

    @cells.fun2cell()
    def tables(self, prev):
	d = {}
	for kid in self.kids:
	    d[kid.name] = kid
	    
	return d
	
    @cells.fun2cell()
    def connected(self, prev):
	if self._rawcon:
	    return True
	else:
	    return False

    # Private Cells
    @cells.fun2cell()
    def _contuple(self, prev):
	""" The RDBMS and connection strings. """
	try:
	    rdbms, constring = self.connection.split("://", 1)
	    if rdbms not in self.supported_rdbms:
		raise UnsupportedRDBMSError(
		    "Only the following RDBMSs are supported:",
		    ",".join(self.supported_rdbms))
	    return (rdbms, constring)
	except ValueError:
	    return (None, None)

    @cells.fun2cell()
    def _rdbmsmodule(self, prev):
	""" The appropriate RDBMS module. """
	if not self._contuple[0]:
	    return None
	if self._contuple[0] == "sqlite":
	    from pysqlite2 import dbapi2 as sqlite
	    return sqlite
	    
    @cells.fun2cell()
    def _rawcon(self, prev):
	""" The "raw" connection to the database """
	if self._rdbmsmodule:
	    return self._rdbmsmodule.connect(self._contuple[1])
	else:
	    return None


class UnsupportedRDBMSError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
	
