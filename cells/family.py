"""
Cell

Cell, and subclasses of Cell.
TODO: More here.
"""

DEBUG = False

import cells
from model import Model

def debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "family".rjust(cells.DECO_OFFSET) + " > ")
    if DEBUG or cells.DEBUG:
        print " ".join(msgs)

class Family(Model):
    _kids = cells.makecell(value=[])
    _kid_slots = cells.makecell(value=cells.Model)

    def __getattr__(self, key):
        # shortstop the default cells
        if key in ("kids", "kid_slots"):
            # and if they don't exist in this object
            if key not in dir(self):
                # copy the default over
                debug("copying default", key, "into this Model")
                object.__setattr__(self, key,
                                   object.__getattribute__(self, "_" + key))

        return object.__getattribute__(self, key)
    
    def make_kid(self, klass):
        self.kids.append(self.kid_instance(klass))

    def add_kid(self, kid):
        kid.parent = self
        self.kids.append(kid)
        
    def kid_instance(self, klass):
        debug("making an instance of", str(klass))
        # first, find the attributes the kid_slots attrib actual wants to
        # define:
        ks_attribs = set(dir(self.kid_slots)) # has a lot of default Model attrs
        md_attribs = set(dir(cells.Model))    # is only default Model attrs
        ks_attribs = ks_attribs.difference(set(dir(cells.Model)))

        # now, do the overrides, bypassing normal getattrs
        for attrib_name in ks_attribs:
            debug("overriding", attrib_name, "in", str(klass))
            setattr(klass, attrib_name, self.kid_slots.__dict__[attrib_name])

        # add any observers the kid_slots class defines:
        klass._observernames.update(self.kid_slots._observernames)

        # XXX: should we memoize all that work here?
        
        # finally, return an instance of that munged class with this obj set
        # as its parent:
        i = klass()
        i.parent = self
        return i

