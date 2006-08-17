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

def primary_key(value=0, *args, **kwargs):
    return cells.CellAttr(value=PrimaryKey(value=value), *args, **kwargs)

def string(value="", *args, **kwargs):
    return cells.CellAttr(value=String(value=value), *args, **kwargs)

def blob(value=None, *args, **kwargs):
    return cells.CellAttr(value=Column(value=value), *args, **kwargs)

def real(value=0.0, *args, **kwargs):
    return cells.CellAttr(value=Real(value=value), *args, **kwargs)


class Column(cells.Model):
    value = cells.makecell(value=None)
    name = cells.makecell(value="anonymous")
    table = cells.makecell(value=None)
    translate_from_sql = cells.makecell(value=lambda v: pickle.loads(str(v)))

    @cells.fun2cell()
    def create_column_string(self, prev):
	return self.name + " BLOB"

    @cells.fun2cell()
    def sql_value(self, prev):
	return pickle.dumps(self.value)

    
class Integer(Column):
    value = cells.makecell(value=0)
    translate_from_sql = cells.makecell(value=lambda v: int(v))
    
    @cells.fun2cell()
    def create_column_string(self, prev):
	return self.name + " INTEGER"

    @cells.fun2cell()
    def sql_value(self, prev):
	return str(self.value)


class PrimaryKey(Integer):
    name = cells.makecell(value="pk")
    @cells.fun2cell()
    def create_column_string(self, prev):
	return self.name + " INTEGER PRIMARY KEY"


class String(Column):
    value = cells.makecell(value="")
    translate_from_sql = cells.makecell(value=lambda v: v)

    @cells.fun2cell()
    def create_column_string(self, prev):
	return self.name + " TEXT"

    @cells.fun2cell()
    def sql_value(self, prev):
	return self.value


class Real(Column):
    value = cells.makecell(value=0.0)
    translate_from_sql = cells.makecell(value=lambda v: float(v))

    @cells.fun2cell()
    def create_column_string(self, prev):
	return self.name + " REAL"

    @cells.fun2cell()
    def sql_value(self, prev):
	return str(self.value)
    
    
class RowList(cells.ListCell):
    def __init__(self, *args, **kwargs):
	cells.ListCell.__init__(self, *args, **kwargs)
	self.db = None    # will be set by Table at Table-init time
	self.table = None	# same here.
	
    def _onchanges(self):
	if self.owner: self.owner._run_observers(self)
	self.propogate()

    def _pregets(self):
	if cells.cellenv.curr:   # (curr == None when not propogating)
            cells.cellenv.curr.add_calls(self)
            self.add_called_by(cells.cellenv.curr)

        self.updatecell()

    def _should_defer(self, name, argtuple):
        _debug(self.name, "wonders if it should defer a", name)
        if cells.cellenv.curr_propogator:       # if a propogation is happening
            _debug(self.name, "sees in-progress propogation; deferring set.")
            # defer the set
            cells.cellenv.deferred_sets.append((self, (name, argtuple)))
	    return True
	
	return False
	
    # "get"-ish calls
    def count(self, v):
	# unimplemented
	return 0

    def index(self, v, start=None, stop=None):
	self._pregets()
	if start is None: start = 0

	# TODO: implement some sort of cache here
	self._pregets()
	cur = self.db._rawcon.cursor()

	s = "SELECT " + ", ".join([_.name for _ in self.table.columns]) +\
	    " FROM " + self.table.name + " WHERE pk>=" + str(start)
	if stop is not None:
	    s += " AND pk < " + str(stop)
	s += "LIMIT 1"
	
	_debug("__getitem__ asks:", s)
	cur.execute(s)
	r = list(cur.fetchone())
	_debug("__getitem__ retrieved:", r)

	newtable = self.table.__class__()

	for column in self.table.columns:
	    trans_v = column.translate_from_sql(r.pop(0))
	    getattr(newtable, column.name).value = trans_v

	return newtable

    def __getitem__(self, k):
	# TODO: implement some sort of cache here
	self._pregets()
	cur = self.db._rawcon.cursor()

	s = "SELECT " + ", ".join([_.name for _ in self.table.columns]) +\
	    " FROM " + self.table.name + " WHERE pk=" + str(k)
	_debug("__getitem__ asks:", s)
	cur.execute(s)
	r = list(cur.fetchone())
	_debug("__getitem__ retrieved:", r)

	newtable = self.table.__class__()

	for column in self.table.columns:
	    trans_v = column.translate_from_sql(r.pop(0))
	    getattr(newtable, column.name).value = trans_v

	return newtable

    def __iter__(self):
	self._pregets()
	return self.value.__iter__()

    def __len__(self):
	self._pregets()
	if self.db:
	    cur = self.db._rawcon.cursor()
	    try:
		s = "SELECT COUNT(pk) FROM " + self.table.name
		_debug("__len__ asks:", s)
		cur.execute(s)
		r = cur.fetchone()
		return int(r[0])
	    except self.db._rdbmsmodule.OperationalError:
		_debug("__len__ sql failed")
		return 0
	    
	else:
	    _debug("__len__ didn't have a db to ask")
	    return 0

    # "set"-ish calls
    def pop(self, index=None):
	"""
	Warning: ListCell.pop() does not act quite like you may expect
	it in certain circumstances. If a pop occurs during a
	propogation, the value will be returned, but the list will not
	be altered until the end of the propogation (thus ensuring all
	cells "see" the same value of this cell during the DP).
	"""
	if not self._should_defer("pop", (index,)):
	    # not deferred, so do a real pop
	    r = self.value.pop(index)
	    self._onchanges()
	else:
	    # deferred. grab the asked-for element of the list
	    if index is None:
		index = -1
	    r = self.value[index]

	return r

    def _make_listfun(name):
	def fn(self, *args, **kwargs):
	    if not self._should_defer(name, (args, kwargs)):
		getattr(self.value, name)(*args, **kwargs)
		cells.cellenv.dp += 1
		self.dp = cells.cellenv.dp
		self._onchanges()
	fn.__name__ = name
	return fn

    def append(self, table):
	if not self._should_defer("append", (table,)):
	    if isinstance(table.__class__, self.table.__class__):
		# XXX: raise a more detailed error regarding type mismatch
		raise Exception()

	    cur = self.db._rawcon.cursor()
	    cur.execute(table.insert_string, table.insert_values)
	    self.db._rawcon.commit()
	    
	    cells.cellenv.dp += 1
	    self.dp = cells.cellenv.dp
	    self._onchanges()

    def extend(self, tables):
	if not self._should_defer("extend", (tables,)):
	    for table in tables:
		if isinstance(table.__class__, self.table.__class__):
		    # XXX: raise a more detailed error regarding type mismatch
		    raise Exception()

		cur = self.db._rawcon.cursor()
		cur.execute(table.insert_string, table.insert_values)
		self.db._rawcon.commit()
	    
	    cells.cellenv.dp += 1
	    self.dp = cells.cellenv.dp
	    self._onchanges()

    def __setitem__(self, i, v):
	if not self._should_defer("__setitem__", (i,v)):
	    if isinstance(v.__class__, self.table.__class__):
		# XXX: raise a more detailed error regarding type mismatch
		raise Exception()

	    v.pk.value = i
	    cur = self.db._rawcon.cursor()
	    # first try to insert that row
	    try:
		_debug("__setitem__ executing:", v.insert_string)
		cur.execute(v.insert_string, v.insert_values)
		self.db._rawcon.commit()
	    except self.db._rdbmsmodule.IntegrityError, e:
		_debug(e)
		# might exist. try to update that pk instead
		_debug("__setitem__ executing:", v.update_string)
		cur.execute(v.update_string)
		self.db._rawcon.commit()
		
    # insert not implemented
    
    remove = _make_listfun("remove")
    reverse = _make_listfun("reverse")
    sort = _make_listfun("sort")
    __add__ = _make_listfun("__add__")
    __iadd__ = _make_listfun("__iadd__")
    __mul__ = _make_listfun("__mul__")
    __rmul__ = _make_listfun("__rmul__")
    __imul__ = _make_listfun("__imul__")
    
    __delitem__ = _make_listfun("__delitem__")
    
    
class Table(cells.Family):
    def __init__(self, *args, **kwargs):
	cells.Family.__init__(self, *args, **kwargs)

	self.rows.db = self.parent
	self.rows.table = self
	
	# build column list
	for attr in self.__dict__.keys():
	    val = getattr(self, attr)
	    if isinstance(val, (Column, PrimaryKey)):
		val.name = attr
		val.table = self
		self.columns.append(val)

	self.ready = True

	_debug(self.name, "has columns", list(self.columns))

    # TODO: Make the primary key not-hardcoded:
    pk = primary_key()
    columns = cells.makecell(celltype=cells.ListCell)
    ready = cells.makecell(value=False)
    rows = cells.makecell(celltype=RowList)
    inserted = cells.makecell(value=False)
    
    @cells.fun2cell(celltype=cells.RuleThenInputCell)
    def name(self, prev):
	return self.__class__.__name__
    
    # Sometimes a Table object acts like a Table, and so we need a
    # "create table" string to feed to the RDBMS
    @cells.fun2cell()
    def create_table_string(self, prev):
	colnames = [ column.create_column_string for column in self.columns ]
	if colnames:
	    return "CREATE TABLE " + self.name + \
		"(" + ",\n".join(colnames) + ")"
	else:
	    return ""

    # Other times the Table object acts like a row in a table, so we
    # need an "insert into" string to feed to the RDBMS when this row
    # is created
    @cells.fun2cell()
    def insert_string(self, prev):
	return " ".join(("INSERT INTO", self.name, "(",
			 ",".join([ _.name for _ in self.columns ]),
			 ") VALUES (",
			 ",".join(['?'] * len(self.columns)),
			 ")"))

    # we'll also need a list of values for the rdbms to use with the
    # insert string
    @cells.fun2cell()
    def insert_values(self, prev):
	return [ _.sql_value for _ in self.columns ]

    # We'll also need an update string when objects change
    @cells.fun2cell()
    def update_string(self, prev):
	return " ".join(("UPDATE", self.name, "SET",
			 ",".join([ col.name + "=" + col.sql_value
				    for col in self.columns]),
			 "WHERE pk=" + str(self.pk.sql_value)))
			
@Table.observer(attrib=("ready", "create_table_string"))
def rebuild_observer(model):    
    if model.ready:
	if not model.parent:
	    return	# we don't rebuild if there's no DB
			# (that is, if this is a row or only
			# partially initialized)
	
	cur = model.parent._rawcon.cursor()
	# Does the DB have this table?
	try:
	    s = "SELECT * FROM " + model.name + " LIMIT 1"
	    cur.execute(s)
	    # Yes.
	    # Are the DB's table's columns in sync with the model's columns?
	    if set([ _.name for _ in model.columns ]) == \
		    set([ _[0] for _ in cur.description ]):
		_debug(set([ _.name for _ in model.columns ]), "==",
		       set([ _[0] for _ in cur.description ]))
		# Yes. Don't rebuild.
		return
	except model.parent._rdbmsmodule.OperationalError:
	    pass
		
	# TODO: Hrmph. I need to figure out how to verify each
	# column's datatype in SQL is the same as what's in the Table
	# model.

	_debug("Rebuilding table", model.name)
	cur = model.parent._rawcon.cursor()
	s = model.create_table_string
	if s:
	    _debug("executing:", s)
	    cur.execute(s)
	    model.parent._rawcon.commit()

@Table.observer(attrib="rows")
def insert_new_row(model):
    if model.rows:
	cur = model.parent._rawcon.cursor()
	for uninserted in filter(lambda row: row.inserted == False, model.rows):
	    pos = model.rows.index(uninserted)
	    uninserted.index = pos
	    s = uninserted.insert_string
	    _debug(s)
	    cur.execute(s)
	    
	    uninserted.inserted = True
	model.parent._rawcon.commit()

@Table.observer(attrib="create_table_string")
def debug_obs(model):
    _debug("create table string is now", repr(model.create_table_string))
	    
class Database(cells.Family):
    """Class for interaction with a database.

    (Short example of init usage here)
    """
    # Public Non-Cells
    supported_rdbms = ("sqlite",)

    addtable = cells.Family.make_kid

    def __del__(self):
	self._rawcon.close()

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

@Database.observer(attrib="kids")
def ko(model):
    _debug("DB has tables", list(model.kids))

@Database.observer(attrib="tables")
def to(model):
    _debug("DB's table dict is", dict(model.tables))


class UnsupportedRDBMSError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
	
