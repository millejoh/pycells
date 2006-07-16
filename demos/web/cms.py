#!/usr/bin/env python

import cells, BaseHTTPServer, ConfigParser, glob, os, re, time, datetime

CellCMSConfig = ConfigParser.ConfigParser()
CellCMSConfig.read('cms.cfg')

class PageCache(object):
    """Builds & stores Page models"""
    def __init__(self):
        self.cache = {}
        
    def __getitem__(self, request):
        # we don't actually want to use the whole request object as the
        # key, just the bits we care about:
        page = self.cache.get(request.path, None)
        
        if not page:           # and if it doesn't exist in the cache, build it
            print "Building page for", request.path
            # XXX: eventually, we'd chose a template based on the request
            page = Page(cache=self, request=request)
            self.cache[request.path] = page # and put it in the cache
        else:                  # if it does exist, make sure its source is curr
            print "Page cache updating mod-time on", request.path
            if page.is_static:
                page.modified = os.stat(page.static_path)[9]
            elif page.is_dynamic:
                page.modified = os.stat(page.dynamic_path)[9]

        print "Cache has", repr(self.cache.keys())

        return page.output

    
class Page(cells.Model):
    def __init__(self, cache, *args, **kwargs):
        self.cache = cache
        self.config = CellCMSConfig
        cells.Model.__init__(self, *args, **kwargs)

    special = re.compile(r"/__.*__")
    cleanpath = re.compile(r"(/([A-Za-z0-9]+\.)*([A-Za-z0-9]*))*(\?.*)?")
    
    # INPUT CELLS
    request = cells.makecell(value=None)
    modified = cells.makecell(value=0)
    built = cells.makecell(value=0)

    # RULE CELLS
    @cells.fun2cell()
    def dirty_path(self, prev):
        if not self.request:
            return "/"
        return self.request.path
    
    @cells.fun2cell()
    def cleaned_path(self, prev):
        if not self.cleanpath.match(self.dirty_path):
            print "Illegal path request:", self.dirty_path
            return "/"
        return self.dirty_path

    @cells.fun2cell()
    def dynamic_path(self, prev):
        return (self.config.get('directories', 'storage') + self.cleaned_path)

    @cells.fun2cell()
    def static_path(self, prev):
        return (self.config.get('directories', 'static') + self.cleaned_path)
    
    is_dynamic = cells.makecell(rule=lambda s,p: glob.glob(s.dynamic_path))
    is_static = cells.makecell(rule=lambda s,p: glob.glob(s.static_path))

    @cells.fun2cell()
    def is_directory(self, prev):
        return os.path.isdir(self.static_path)

    @cells.fun2cell()
    def is_special(self, prev):
        return self.special.match(self.cleaned_path)

    @cells.fun2cell()
    def should_apply_template(self, prev):
        return self.is_dynamic and not self.is_special

    @cells.fun2cell()
    def is_valid(self, prev):
        return self.is_dynamic or self.is_static

    @cells.fun2cell()
    def source(self, prev):
        """Holds the unrendered source data for this Page"""
        if not self.is_valid:
            return "No such file"

        # all we need to do is depend on self.modified and the source
        # will be updated whenever the modification-time is
        # changed. I'm pretty sure this test will always fail.
        if self.modified < self.built:
            return prev
        
        if self.is_directory:           # implies is_static
            currdir = os.getcwd()       # save old dir
            os.chdir(self.static_path)  # change to the requested dir
            out = ["Directory listing:", "------------------------------"]
            out += glob.glob("*")       # get the files here
            os.chdir(currdir)           # change back to the original dir
            return "\n".join(out)

        if self.is_static:              # because of above test, not a dir.
            return open(self.static_path).read()
        
        if self.is_dynamic:
            return open(self.dynamic_path).read()

        else:
            return "Should not have got here!"
    
    @cells.fun2cell()
    def template(self, prev):
        """Applies a template to this Page depending on request type"""
        # (doesn't actually make any choices, currently)
        if self.should_apply_template:
            return Template(cache=self.cache, text=self.source)
        
    @cells.fun2cell()
    def output(self, prev):
        if self.should_apply_template:
            return self.template.render()
        else:
            return self.source

@Page.observer(attrib="source")
def source_obs(self):
    """Each time a new source gets generated, update its built-time
    """
    if self.is_valid:
        self.built = self.modified

@Page.observer(attrib="output")
def out_obs(self):
    print self.cleaned_path, "-- New output"

class Template(object):
    # this could probably be done with one regex. I'm too lazy to figure it out.
    includetag1 = re.compile(r"\<\s*include_resource\s*name\s*=\s*" +\
                             r"'(?P<resource>[^']+)'\s*\/\>")
    includetag2 = re.compile(r'\<\s*include_resource\s*name\s*=\s*' +\
                             r'"(?P<resource>[^"]+)"\s*\/\>')

    def __init__(self, text, cache, template="default.tmpl"):
        self.source = text
        self.cache = cache
        self.template = template

    def render(self):
        print "Running template.output with", repr(self.source[:10])
        rendered = ""
        
        # do resource insertion        
        for line in open(self.template).readlines():
            # by looking for resource inclusion tags
            m = self.includetag1.search(line)
            if not m:
                m = self.includetag2.search(line)

            # loop over the line while we find them
            while m:
                # if the requested resource is "__body__", insert the source
                if m.group(1) == "__body__":
                    replacement = self.source

                # otherwise, just pull from the page cache (which may build
                # another Page)
                else:
                    req = Request(path="/" + m.group(1)) # dummy request
                    replacement = self.cache[req]

                line = line[:m.span()[0]] + replacement + line[m.span()[1]:]
                            
                # look for more resource inclusion tags
                m = self.includetag1.search(line)
                if not m:
                    m = self.includetag2.search(line)

            rendered += line
            
        return rendered

# Make a page cache object
pages = PageCache()

class Request(object):
    """Just a container for the RequestHandler's current request data"""
    def __init__(self, request=None, path=None):
        if request:
            self.client_address = request.client_address
            self.command = request.command
            self.path = request.path
            self.request_version = request.request_version
            self.headers = request.headers
            self.rfile = request.rfile
            self.wfile = request.wfile
        else:
            self.client_address = None
            self.command = None
            self.path = path
            self.request_version = None
            self.headers = None
            self.rfile = None
            self.wfile = None
                                                  
class CellRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        print >>self.wfile, pages[Request(request=self)]

    
# Finally, set the server moving:
print "Starting server at", CellCMSConfig.get('server', 'address'), "on port", \
      CellCMSConfig.get('server', 'port')
server_address=(CellCMSConfig.get('server', 'address'),
                CellCMSConfig.getint('server', 'port'))
httpd = BaseHTTPServer.HTTPServer(server_address, CellRequestHandler)
print "... server started."
httpd.serve_forever()
