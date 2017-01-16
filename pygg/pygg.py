"""
run the following for help

  python bin/runpygg.py --help
"""
import os
import re
import subprocess
import csv
import tempfile
from six import iteritems

import pandas

quote1re = re.compile('"')
quote2re = re.compile("'")

R_IMAGE_SIZE = 7            # in inches
IPYTHON_IMAGE_SIZE = 800    # in pixels

def esc(mystr):
    """Escape string so that it remains a string when converted to R"""
    return '"{}"'.format(quote2re.sub("\\'", quote1re.sub("\\\"", mystr)))

def is_escaped(s):
    quotes = ["'", '"']
    for q in quotes:
        if s.startswith(q) and s.endswith(q):
            return True
    return False


def _to_r(o, as_data=False, level=0):
    """Helper function to convert python data structures to R equivalents

    TODO: a single model for transforming to r to handle
    * function args
    * lists as function args
    """
    if o is None:
        return "NA"
    if isinstance(o, str):
        return o
    if hasattr(o, "r"):
        # bridge to @property r on GGStatement(s)
        return o.r
    elif isinstance(o, bool):
        return "TRUE" if o else "FALSE"
    elif isinstance(o, (list, tuple)):
        inner = ",".join([_to_r(x, True, level+1) for x in o])
        return "c({})".format(inner) if as_data else inner
    elif isinstance(o, dict):
        inner = ",".join(["{}={}".format(k, _to_r(v, True, level+1))
                         for k, v in sorted(iteritems(o), key=lambda x: x[0])])
        return "list({})".format(inner) if as_data else inner
    return str(o)


class GGStatement(object):
    def __init__(self, _name, *args, **kwargs):
        self.name = _name
        self.args = args
        self.data = None
        self.kwargs = kwargs

    def to_stmts(self):
        return GGStatements([self])

    def __add__(self, o):
        if not o:
            return self.to_stmts()
        return self.to_stmts() + o.to_stmts()

    @property
    def r(self):
        """Convert this GGStatement into its R equivalent expression"""
        r_args = [_to_r(self.args), _to_r(self.kwargs)]
        # remove empty strings from the call args
        r_args = ",".join([x for x in r_args if x != ""])
        return "{}({})".format(self.name, r_args)

    def __str__(self):
        """Get a string representation of this object"""
        return self.r

    def save(self, name, *args, **kwargs):
        return ggsave(name, self.to_stmts(), *args, **kwargs)


class GGStatements(object):

    def __init__(self, stmts=None):
        self.stmts = stmts
        if not self.stmts:
            self.stmts = []

    def to_stmts(self):
        return self

    def __add__(self, o):
        if not o:
            return self
        stmts = list(self.stmts)
        try:
            stmts.extend(o.to_stmts().stmts)
        except:
            if isinstance(o, list):
                stmts.extend(o)
            else:
                stmts.append(o)
        return GGStatements(stmts)

    @property
    def data(self):
      for stmt in self.stmts:
        if stmt.data is not None:
          return stmt.data
      return None

    @property
    def r(self):
        return " + ".join(_to_r(x) for x in self.stmts)

    def __str__(self):
        return self.r

    def save(self, name, *args, **kwargs):
        return ggsave(name, self, *args, **kwargs)


###################################################
#
#  Specialized expressions that must be in Python
#
###################################################

class GGData(object):
  def __init__(self, r_commands, fname=None):
      self.r_commands = r_commands
      self.fname = fname


  def __str__(self):
      return self.r_commands


def is_pandas_df(o):
    """Is object o a pandas dataframe?"""
    return isinstance(o, pandas.DataFrame)


def data_sql(db, sql):
    """Load file using RPostgreSQL

    Place to edit if want to add more database backend support

    """
    if not db:
        if sql:
            print("ERR: -db option must be set if using -sql")
        return ""

    cmd = """
    library(RPostgreSQL)
    drv = dbDriver('PostgreSQL')
    con = dbConnect(drv, dbname='%(db_name)s')
    q = "%(query)s"
    data = dbGetQuery(con, q)
    """

    return GGData(cmd % {
        'db_name': db,
        'query': sql
    })


def data_py(o, *args, **kwargs):
    """converts python object into R Dataframe definition

    converts following data structures:

      row oriented list of dictionaries:

          [ { 'x': 0, 'y': 1, ...}, ... ]

      col oriented dictionary of lists

          { 'x': [0,1,2...], 'y': [...], ... }

    @param o python object to convert
    @param args argument list to pass to read.csv
    @param kwargs keyword args to pass to read.csv
    @return a tuple of the file containing the data and an
        expression to define data.frame object and set it to variable "data"

    data = read.csv(tmpfile, *args, **kwargs)

    """
    if isinstance(o, str):
        fname = o
    else:
        if not is_pandas_df(o):
            # convert incoming data layout to pandas' DataFrame
            o = pandas.DataFrame(o)
        fname = tempfile.NamedTemporaryFile().name
        o.to_csv(fname, sep=',', encoding='utf-8', index=False)
    kwargs["sep"] = esc(',')
    read_csv_stmt = GGStatement("read.csv", esc(fname), *args, **kwargs).r
    return GGData("data = {}".format(read_csv_stmt), fname=fname)





###################################################
#
#  Facets use R formulas x ~ y.  We need custom API for them
#  e.g., facet_grid(formula, ...)
#
###################################################


def facet_wrap(formula, *args, **kwargs):
    if not formula:
        print("WARN: facet_wrap got None")
        return None

    return GGStatement("facet_wrap", formula, *args, **kwargs)


def facet_grid(formula, *args, **kwargs):
    if not formula:
        print("WARN: facet_grid got None")
        return None

    return GGStatement("facet_grid", formula, *args, **kwargs)


###################################################
#
#  ggsave talks to the external world, so needs custom support
#
###################################################


def ggsave(name, plot, data=None, *args, **kwargs):
    """Save a GGStatements object to destination name

    @param name output file name.  if None, don't run R command
    @param kwargs keyword args to pass to ggsave.  The following are special
            keywords for the python save method

      data: a python data object (list, dict, DataFrame) used to populate
        the `data` variable in R
      libs: list of library names to load in addition to ggplot2
      prefix: string containing R code to run before any ggplot commands (including data loading)
      postfix: string containing R code to run after data is loaded (e.g., if you want to rename variable names)
      quiet:  if Truthy, don't print out R program string

    """
    # constants
    kwdefaults = {
        'width': 10,
        'height': 8,
        'scale': 1
    }
    keys_to_rm = ["prefix", "quiet", "postfix", 'libs']
    varname = 'p'

    # process arguments
    prefix = kwargs.get('prefix', '')
    postfix = kwargs.get('postfix', '')
    libs = kwargs.get('libs', [])
    libs = '\n'.join(["library(%s)" % lib for lib in libs])
    quiet = kwargs.get("quiet", False)
    kwargs = {k: v for k, v in iteritems(kwargs)
              if v is not None and k not in keys_to_rm}
    kwdefaults.update(kwargs)
    kwargs = kwdefaults

    # figure out how to load data in the R environment
    if data is None: data = plot.data

    if data is None:
        # Don't load anything, the data source is already present in R
        data_src = ''
    elif isinstance(data, str) and 'RPostgreSQL' in data:
        # Hack to allow through data_sql results
        data_src = data
    elif isinstance(data, GGData):
        data_src = str(data)
    else:
        # format the python data object
        data_src = str(data_py(data))

    prog = "%(header)s\n%(libs)s\n%(prefix)s\n%(data)s\n%(postfix)s\n%(varname)s = %(prog)s" % {
        'header': "library(ggplot2)",
        'libs': libs,
        'data': data_src,
        'prefix': prefix,
        'postfix': postfix,
        'varname': varname,
        'prog': plot.r
    }

    if name:
        stmt = GGStatement("ggsave", esc(name), varname, *args, **kwargs)
        prog = "%s\n%s" % (prog, stmt.r)

    if not quiet:
        print(prog)
        print()

    if name:
        execute_r(prog, quiet)
    return prog


def gg_ipython(plot, data, width=IPYTHON_IMAGE_SIZE, height=None,
               *args, **kwargs):
    """Render pygg in an IPython notebook

    Allows one to say things like:

    import pygg
    p = pygg.ggplot('diamonds', pygg.aes(x='carat', y='price', color='clarity'))
    p += pygg.geom_point(alpha=0.5, size = 2)
    p += pygg.scale_x_log10(limits=[1, 2])
    pygg.gg_ipython(p, data=None, quiet=True)

    directly in an IPython notebook and see the resulting ggplot2 image
    displayed inline.  This function is print a warning if the IPython library
    cannot be imported.  The ggplot2 image is rendered as a PNG and not
    as a vectorized graphics object right now.

    Note that by default gg_ipython sets the output height and width to
    IPYTHON_IMAGE_SIZE pixels as this is a reasonable default size for a
    browser-based notebook.  Height is by default None, indicating that height
    should be set to the same value as width.  It is possible to adjust
    the aspect ratio of the output by providing non-None values for both
    width and height

    """
    try:
        import IPython.display
        tmp_image_filename = tempfile.NamedTemporaryFile(suffix='.jpg').name
        # Quiet by default
        kwargs['quiet'] = kwargs.get('quiet', True)

        if width is None:
            raise ValueError("Width cannot be None")
        height = height or width
        w_in, h_in = size_r_img_inches(width, height)
        ggsave(name=tmp_image_filename, plot=plot, data=data,
               dpi=600, width=w_in, height=h_in, units=esc('in'),
               *args, **kwargs)
        return IPython.display.Image(filename=tmp_image_filename,
                                     width=width, height=height)
    except ImportError:
        print("Could't load IPython library; integration is disabled")


def size_r_img_inches(width, height):
    """Compute the width and height for an R image for display in IPython

    Neight width nor height can be null but should be integer pixel values > 0.

    Returns a tuple of (width, height) that should be used by ggsave in R to
    produce an appropriately sized jpeg/png/pdf image with the right aspect
    ratio.  The returned values are in inches.

    """
    # both width and height are given
    aspect_ratio = height / (1.0 * width)
    return R_IMAGE_SIZE, round(aspect_ratio * R_IMAGE_SIZE, 2)


def execute_r(prog, quiet):
    """Run the R code prog an R subprocess

    @raises ValueError if the subprocess exits with non-zero status
    """
    FNULL = open(os.devnull, 'w') if quiet else None
    try:
        input_proc = subprocess.Popen(["echo", prog], stdout=subprocess.PIPE)
        status = subprocess.call("R --no-save --quiet",
                                 stdin=input_proc.stdout,
                                 stdout=FNULL,
                                 stderr=subprocess.STDOUT,
                                 shell=True) # warning, this is a security problem
        if status != 0:
            raise ValueError("ggplot2 bridge failed for program: {}."
                             " Check for an error".format(prog))
    finally:
        if FNULL is not None:
            FNULL.close()


###################################################
#
#  Axes are a pain, helper functions
#
###################################################
def axis_labels(xtitle, 
                ytitle, 
                xsuffix="continuous", 
                ysuffix="continuous",
                xkwargs={},
                ykwargs={}):
  """
  Helper function to create reasonable axis labels

  @param xtitle String for the title of the X axis.  Automatically escaped
  @param ytitle String for the title of the Y axis.  Automatically escaped
  @param xsuffix Suffix string appended to "scales_x_" to define the type of x axis
                 Default: "continuous"
  @param ysuffix Suffix string appended to "scales_y_" to define the type of y axis
                 Default: "continuous"
  @param xkwargs keyword arguments to pass to scales_x_* function
  @param xkwargs keyword arguments to pass to scales_x_* function
  @return GGStatements

  For example:
    
      p = ggplot(...)
      p += axis_labels("Dataset Size (MB)", 
                       "Latency (sec)", 
                       "log10",  
                       xkwargs=dict(breaks=[0, 10, 100, 5000]))

  """

  exec("xfunc = scale_x_%s" % xsuffix)
  exec("yfunc = scale_y_%s" % ysuffix)
  return (
    xfunc(name=esc(xtitle), **xkwargs) + 
    yfunc(name=esc(ytitle), **ykwargs)
  )




###################################################
#
#  Code to actually generate the ggplot2 functions
#
###################################################

def make_master_binding():
  """
  wrap around ggplot() call to handle passed in data objects
  """
  ggplot = make_ggplot2_binding("ggplot")
  def _ggplot(data, *args, **kwargs):
    data_var = data
    if not isinstance(data, str):
      data_var = "data"
    else:
      data = None
    stmt = ggplot(data_var, *args, **kwargs)
    stmt.data = data
    return stmt
  return _ggplot


def make_ggplot2_binding(fname):
    def f(*args, **kwargs):
        return GGStatement(fname, *args, **kwargs)
    f.__name__ = fname
    return f

ggplot = make_master_binding()
