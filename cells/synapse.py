import cells

DEBUG = False

def debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "synapse".rjust(cells.DECO_OFFSET) + " > ")
    if DEBUG or cells.DEBUG:
        print " ".join(msgs)

class Synapse(cells.Cell):
    initialized = False
    
    def __new__(cls, owner, name=None, **kwargs):
        # first, check to see if there's already a synapse with this name in
        # the owner Cell
        if not owner.synapse_space.has_key(name): # and if there isn't
            # make one in the owner
            debug("building new synapse '" + name + "' in", str(owner))
            owner.synapse_space[name] = cells.Cell.__new__(cls, owner,
                                                           name=name, **kwargs)

        # finally, return the owner's synapse
        return owner.synapse_space[name]

    def __init__(self, owner, name=None, **kwargs):
        # at this point we're guaranteed to have a Synapse in the
        # owner, and self points at that Synapse. We don't know if
        # it's been initialized, though. so:
        if not self.initialized:
            debug("(re)initializing", name)
            cells.Cell.__init__(self, owner, name=name, **kwargs)
            self.initialized = True
        
    def __call__(self):
        return self.get()

    def run(self):
        debug(self.name, "running")
        # call stack manipulation
        oldcurr = cells.curr
        cells.curr = self

        # the rule run may rewrite the dep graph; prepare for that by nuking
        # c-b links to this cell and calls links from this cell:
        for cell in self.calls:
            debug(self.name, "removing c-b link from", cell.name)
            cell.remove_cb(self)
        self.reset_calls()

        self.dp = cells.dp                             # we're up-to-date
        newvalue = self.rule(self.owner, self.value)   # run the rule
        self.bound = True
        
        # restore old running cell
        cells.curr = oldcurr

        # return changed status
        if self.unchanged_if(self.value, newvalue):
            debug(self.name, "unchanged.")
            return False
        else:
            debug(self.name, "changed.")
            self.last_value = self.value
            self.value = newvalue
            
            return True

    def rule(self, owner, oldvalue):
        return None

class ChangeSynapse(Synapse):
    """A very simple filter. Only returns the new value when it's
    changed by the passed delta
    """
    def __init__(self, owner, name=None, read=None, delta=None, **kwargs):
        debug("init'ing ChangeSynapse")
        if not self.initialized:
            self.readvar, self.delta = read, delta            
        Synapse.__init__(self, owner, name=name, **kwargs)
        self.rule = self.synapse_rule

    def synapse_rule(self, owner, oldvalue):
        debug("running ChangeSynapse rule")
        newval = self.readvar.get()
        if not oldvalue or abs(newval - oldvalue) > self.delta:
            debug("returning new value", str(newval))
            return newval
        else:
            debug("returning old value", str(oldvalue))
            return oldvalue
