#!/usr/bin/env python

import celltk
import cells
import re

class CalcInput(celltk.Entry):
    unacceptable = re.compile(r"[^0-9 \+-\.\*/\(\)]")
    
    @cells.fun2cell()
    def cleaned_input(self, prev):
	if self.text and not self.unacceptable.search(self.text):
	    return self.text

	return ""
    
    @cells.fun2cell()
    def value(self, prev):
	if self.cleaned_input:
	    try:
		v = eval(self.cleaned_input)
	    except Exception:
		print "exception caught"
		return "error"
	    print "value is", repr(v)
	    return v
	else:
	    return "No input or error"

@CalcInput.observer(attrib="value")
def outputter(model):
    if model.parent and model.parent.output and model.parent.output.stringvar:
	model.parent.output.stringvar.set(model.value)

class CalculatorWindow(celltk.Window):
    def __init__(self, *args, **kwargs):
	celltk.Window.__init__(self, *args, **kwargs)	
	self.input = CalcInput(parent=self, update_on="write")
	self.output = celltk.Label(parent=self)
	
    title = cells.makecell(value="Calculator Demo")
    input = cells.makecell(value=None)
    output = cells.makecell(value=None)
    
    @cells.fun2cell()
    def kids(self, prev):	
	return [ self.input, self.output ]

if __name__ == "__main__":
    c = CalculatorWindow()
    c.widget.pack()
    c.widget.mainloop()
