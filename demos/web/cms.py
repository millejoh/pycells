#!/usr/bin/env python

import cells, BaseHTTPServer, ConfigParser

CellCMSConfig = ConfigParser.ConfigParser()

# the general idea for this thing is that there be a thin shell of
# "normal" python to set up & feed the models which will do the heavy
# lifting & responses.

# let's build the models.
class Page(cells.Model):
    """A model to hold a single page, from request to page generation."""
    request = cells.makecell(value=None) # input

    @cells.fun2cell()
    def output(self, prev):
        """Outputs the final, rendered version of this Page"""
        if not self.request: return
        return "You are:\n" + str(self.request.headers)


class RequestHandler(cells.Model):
    """A model which turns GET requests into formatted content
    
    The idea for this thing is that we build a model for every
    request, then store them in the pages slot. We can use the
    template slot to give each page model the same base instantiation
    """
    def __init__(self):
        cells.Model.__init__(self)
        self.pages = {}
        
    # INPUT CELLS
    config = cells.makecell(value=None)  # handle to the ConfigParser object    
    request = cells.makecell(value=None) # the input for the model
    pages = cells.makecell(value=None)   # Page model storage

    # RULE CELLS
    @cells.fun2cell()
    def request_key(self, prev):
        """Takes a BaseHTTPRequestHandler and makes a page key out of it"""
        if self.request:
            req = self.request
            return (req.client_address, req.command, req.path)
        return None

    @cells.fun2cell()
    def output(self, prev):
        """Outputs the requested page, rendered and ready for the browser."""
        if not self.request_key: return
        return self.pages[self.request_key].output

@RequestHandler.observer(attrib="request_key")
def request_key_obs(self):
    """Builds the Request-to-Page dictionary"""
    # TODO: pages_registry management -- it grows forever, now.
    if not self.request_key: return
        
    page = self.pages.get(self.request_key, None)
    if not page:                    # build a Page if one doesn't exist for
        self.pages[self.request_key] = Page() # this request
        self.pages[self.request_key].request = self.request

    
handler = RequestHandler() # make a new cellular handler
handler.config = CellCMSConfig # and give it its configuration
    
# now let's build the shell. I'm going to use the BaseHTTPServer to
# process the raw requests, and a subclass of the base request handler
# will pass things into the model
class Request(object):
    """Just a container for the RequestHandler's current request data"""
    def __init__(self, request):
        self.client_address = request.client_address
        self.command = request.command
        self.path = request.path
        self.request_version = request.request_version
        self.headers = request.headers
        self.rfile = request.rfile
        self.wfile = request.wfile
                                                  
class CellRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):        
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def do_GET(self):
        handler.request = Request(self) # build a new request object
        print >>self.wfile, handler.output

# Finally, set it moving:
print "Starting server on port", 8082
server_address=('', 8082)
httpd = BaseHTTPServer.HTTPServer(server_address, CellRequestHandler)
print "... server started."
httpd.serve_forever()

