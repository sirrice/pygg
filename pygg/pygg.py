"""
run the following for help

  python bin/runpygg.py --help
"""
import os
import re
import subprocess
import csv
import tempfile

import pandas

quote1re = re.compile("\"")
quote2re = re.compile("'")


def _to_r(o, as_data=False):
    if o is None:
        return "NA"
    if hasattr(o, "r"):
        # bridge to @property r on GGStatement(s)
        return o.r
    elif isinstance(o, bool):
        return "TRUE" if o else "FALSE"
    elif isinstance(o, (list, tuple)):
        inner = ",".join([_to_r(x, True) for x in o])
        return "c({})".format(inner) if as_data else inner
    elif isinstance(o, dict):
        inner = ",".join(["{}={}".format(k, _to_r(v, True))
                         for k, v in sorted(o.iteritems(), key=lambda x: x[0])])
        return "list({})".format(inner) if as_data else inner
    return str(o)

class GGStatement(object):
    def __init__(self, _name, *args, **kwargs):
        self.name = _name
        self.args = args
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


def is_pandas_df(o):
    """Is object o a pandas dataframe?"""
    return isinstance(o, pandas.DataFrame)


def data_sql(db, sql):
    """Load file using RPostgreSQL

    Place to edit if want to add more database backend support

    """
    if not db:
        if sql:
            print "ERR: -db option must be set if using -sql"
        return ""

    cmd = """
    library(RPostgreSQL)
    drv = dbDriver('PostgreSQL')
    con = dbConnect(drv, dbname='%(db_name)s')
    q = "%(query)s"
    data = dbGetQuery(con, q)
  """

    return cmd % {
        'db_name': db,
        'query': sql
    }


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
    if isinstance(o, basestring):
        fname = o
    else:
        if not is_pandas_df(o):
            # convert incoming data layout to pandas' DataFrame
            o = pandas.DataFrame(o)
        fname = tempfile.NamedTemporaryFile().name
        o.to_csv(fname, sep=',', encoding='utf-8', index=False)
    kwargs["sep"] = '","'
    read_csv_stmt = GGStatement("read.csv", '"%s"' % fname, *args, **kwargs).r
    return fname, "data = {}".format(read_csv_stmt)


###################################################
#
#  Facets use R formulas x ~ y.  We need custom API for them
#  e.g., facet_grid(x, y, ...)
#
###################################################

# TODO -- is this really necessary?  Why can't we pass in a formula as a string?
def facet_wrap(x, y, *args, **kwargs):
    if not x and not y:
        print "WARN: facet_wrap got x=None, y=None"
        return None
    if not x:
        x = ""
    if not y:
        y = "."

    facets = "%s~%s" % (x, y)
    return GGStatement("facet_wrap", facets, *args, **kwargs)


def facet_grid(x, y, *args, **kwargs):
    facets = filter(bool, [x, y])
    if not facets:
        print "WARN: facet_grid got x=None, y=None"
        return None
    facets = "%s~" % "+".join(facets)

    if not x:
        x = "."
    if not y:
        y = "."

    facets = "%s~%s" % (x, y)
    return GGStatement("facet_grid", facets, *args, **kwargs)


###################################################
#
#  ggsave talks to the external world, so needs custom support
#
###################################################


def ggsave(name, plot, data, *args, **kwargs):
    """Save a GGStatements object to destination name

    @param name output file name.  if None, don't run R command
    @param kwargs keyword args to pass to ggsave.  The following are special
            keywords for the python save method

      data: a python data object (list, dict, DataFrame) used to populate
        the `data` variable in R
      prefix: string containing R code to run before the ggplot command
      quiet:  if Truthy, don't print out R program string

    """
    # constants
    kwdefaults = {
        'width': 10,
        'height': 8,
        'scale': 1
    }
    keys_to_rm = ["prefix", "quiet"]
    varname = 'p'

    # process arguments
    prefix = kwargs.get('prefix', '')
    quiet = kwargs.get("quiet", False)
    kwargs = {k: v for k, v in kwargs.iteritems()
              if v is not None and key not in keys_to_rm}
    kwdefaults.update(kwargs)
    kwargs = kwdefaults

    prog = "%(header)s\n%(prefix)s\n%(data)s\n%(varname)s = %(prog)s" % {
        'header': "library(ggplot2)",
        'data': '' if data is None else data_py(data)[1],
        'prefix': prefix,
        'varname': varname,
        'prog': plot.r
    }

    if name:
        stmt = GGStatement("ggsave", "'%s'" % name, varname, *args, **kwargs)
        prog = "%s\n%s" % (prog, stmt.r)

    if not quiet:
        print prog
        print

    if name:
        execute_r(prog, quiet)
    return prog


def execute_r(prog, quiet):
    """Run the R code prog an R subprocess"""
    with open(os.devnull, 'w') if quiet else None as FNULL:
        input_proc = subprocess.Popen(["echo", prog], stdout=subprocess.PIPE)
        subprocess.call("R --no-save --quiet",
                        stdin=input_proc.stdout,
                        stdout=FNULL,
                        stderr=subprocess.STDOUT,
                        shell=True)


# TODO -- remove gen_cmds and put the building code right here
def mkfunc(fname):
    def f(*args, **kwargs):
        return GGStatement(fname, *args, **kwargs)
    f.__name__ = fname
    return f

ggplot = mkfunc("ggplot")
qplot = mkfunc("qplot")
factor = mkfunc("factor")
geom_jitter = mkfunc("geom_jitter")
geom_line = mkfunc("geom_line")
geom_path = mkfunc("geom_path")
geom_pointrange = mkfunc("geom_pointrange")
geom_point = mkfunc("geom_point")
geom_quantile = mkfunc("geom_quantile")
geom_rect = mkfunc("geom_rect")
geom_ribbon = mkfunc("geom_ribbon")
geom_segment = mkfunc("geom_segment")
geom_rug = mkfunc("geom_rug")
geom_step = mkfunc("geom_step")
geom_text = mkfunc("geom_text")
geom_tile = mkfunc("geom_tile")
geom_violin = mkfunc("geom_violin")
geom_vlin = mkfunc("geom_vlin")
geom_polygon = mkfunc("geom_polygon")
geom_abline = mkfunc("geom_abline")
geom_area = mkfunc("geom_area")
geom_bar = mkfunc("geom_bar")
geom_bin2d = mkfunc("geom_bin2d")
geom_blank = mkfunc("geom_blank")
geom_boxplot = mkfunc("geom_boxplot")
geom_contour = mkfunc("geom_contour")
geom_crossbar = mkfunc("geom_crossbar")
geom_density = mkfunc("geom_density")
geom_density2d = mkfunc("geom_density2d")
geom_dotplot = mkfunc("geom_dotplot")
geom_errorbar = mkfunc("geom_errorbar")
geom_errorbarh = mkfunc("geom_errorbarh")
geom_freqpoly = mkfunc("geom_freqpoly")
geom_hex = mkfunc("geom_hex")
geom_histogram = mkfunc("geom_histogram")
geom_hline = mkfunc("geom_hline")
geom_vline = mkfunc("geom_vline")
stat_bin = mkfunc("stat_bin")
stat_bin2d = mkfunc("stat_bin2d")
stat_bindot = mkfunc("stat_bindot")
stat_binhex = mkfunc("stat_binhex")
stat_boxplot = mkfunc("stat_boxplot")
stat_contour = mkfunc("stat_contour")
stat_density = mkfunc("stat_density")
stat_density2d = mkfunc("stat_density2d")
stat_ecdf = mkfunc("stat_ecdf")
stat_function = mkfunc("stat_function")
stat_identify = mkfunc("stat_identify")
stat_qq = mkfunc("stat_qq")
stat_quantile = mkfunc("stat_quantile")
stat_smooth = mkfunc("stat_smooth")
stat_spoke = mkfunc("stat_spoke")
stat_sum = mkfunc("stat_sum")
stat_summary = mkfunc("stat_summary")
stat_unique = mkfunc("stat_unique")
stat_ydensity = mkfunc("stat_ydensity")
expand_limits = mkfunc("expand_limits")
guides = mkfunc("guides")
guide_legend = mkfunc("guide_legend")
guide_colourbar = mkfunc("guide_colourbar")
scale_alpha = mkfunc("scale_alpha")
scale_alpha_continuous = mkfunc("scale_alpha_continuous")
scale_alpha_discrete = mkfunc("scale_alpha_discrete")
scale_area = mkfunc("scale_area")
scale_colour_brewer = mkfunc("scale_colour_brewer")
scale_color_brewer = mkfunc("scale_color_brewer")
scale_fill_brewer = mkfunc("scale_fill_brewer")
scale_colour_gradient = mkfunc("scale_colour_gradient")
scale_color_gradient = mkfunc("scale_color_gradient")
scale_color_continuous = mkfunc("scale_color_continuous")
scale_color_gradient = mkfunc("scale_color_gradient")
scale_colour_continuous = mkfunc("scale_colour_continuous")
scale_fill_continuous = mkfunc("scale_fill_continuous")
scale_fill_gradient = mkfunc("scale_fill_gradient")
scale_colour_gradient2 = mkfunc("scale_colour_gradient2")
scale_color_gradient2 = mkfunc("scale_color_gradient2")
scale_fill_gradient2 = mkfunc("scale_fill_gradient2")
scale_colour_gradientn = mkfunc("scale_colour_gradientn")
scale_color_gradientn = mkfunc("scale_color_gradientn")
scale_fill_gradientn = mkfunc("scale_fill_gradientn")
scale_colour_grey = mkfunc("scale_colour_grey")
scale_color_grey = mkfunc("scale_color_grey")
scale_fill_grey = mkfunc("scale_fill_grey")
scale_colour_hue = mkfunc("scale_colour_hue")
scale_color_discrete = mkfunc("scale_color_discrete")
scale_color_hue = mkfunc("scale_color_hue")
scale_colour_discrete = mkfunc("scale_colour_discrete")
scale_fill_discrete = mkfunc("scale_fill_discrete")
scale_fill_hue = mkfunc("scale_fill_hue")
scale_identity = mkfunc("scale_identity")
scale_alpha_identity = mkfunc("scale_alpha_identity")
scale_color_identity = mkfunc("scale_color_identity")
scale_colour_identity = mkfunc("scale_colour_identity")
scale_fill_identity = mkfunc("scale_fill_identity")
scale_linetype_identity = mkfunc("scale_linetype_identity")
scale_shape_identity = mkfunc("scale_shape_identity")
scale_size_identity = mkfunc("scale_size_identity")
scale_manual = mkfunc("scale_manual")
scale_alpha_manual = mkfunc("scale_alpha_manual")
scale_color_manual = mkfunc("scale_color_manual")
scale_colour_manual = mkfunc("scale_colour_manual")
scale_fill_manual = mkfunc("scale_fill_manual")
scale_linetype_manual = mkfunc("scale_linetype_manual")
scale_shape_manual = mkfunc("scale_shape_manual")
scale_size_manual = mkfunc("scale_size_manual")
scale_size = mkfunc("scale_size")
scale_size_continuous = mkfunc("scale_size_continuous")
scale_size_discrete = mkfunc("scale_size_discrete")
scale_linetype = mkfunc("scale_linetype")
scale_linetype_continuous = mkfunc("scale_linetype_continuous")
scale_linetype_discrete = mkfunc("scale_linetype_discrete")
scale_shape = mkfunc("scale_shape")
scale_shape_continuous = mkfunc("scale_shape_continuous")
scale_shape_discrete = mkfunc("scale_shape_discrete")
scale_x_continuous = mkfunc("scale_x_continuous")
scale_x_log10 = mkfunc("scale_x_log10")
scale_x_reverse = mkfunc("scale_x_reverse")
scale_x_sqrt = mkfunc("scale_x_sqrt")
scale_y_continuous = mkfunc("scale_y_continuous")
scale_y_log10 = mkfunc("scale_y_log10")
scale_y_reverse = mkfunc("scale_y_reverse")
scale_y_sqrt = mkfunc("scale_y_sqrt")
scale_x_date = mkfunc("scale_x_date")
scale_y_datetime = mkfunc("scale_y_datetime")
scale_x_datetime = mkfunc("scale_x_datetime")
scale_y_datetime = mkfunc("scale_y_datetime")
scale_x_discrete = mkfunc("scale_x_discrete")
scale_y_discrete = mkfunc("scale_y_discrete")
xlim = mkfunc("xlim")
ylim = mkfunc("ylim")
coord_fixed = mkfunc("coord_fixed")
coord_flip = mkfunc("coord_flip")
coord_map = mkfunc("coord_map")
coord_polar = mkfunc("coord_polar")
coord_trans = mkfunc("coord_trans")
label_both = mkfunc("label_both")
label_bquote = mkfunc("label_bquote")
label_parsed = mkfunc("label_parsed")
label_value = mkfunc("label_value")
position_dodge = mkfunc("position_dodge")
position_fill = mkfunc("position_fill")
position_identity = mkfunc("position_identity")
position_stack = mkfunc("position_stack")
position_jitter = mkfunc("position_jitter")
annotate = mkfunc("annotate")
annotation_custom = mkfunc("annotation_custom")
annotation_logticks = mkfunc("annotation_logticks")
annotation_map = mkfunc("annotation_map")
annotation_raster = mkfunc("annotation_raster")
borders = mkfunc("borders")
add_theme = mkfunc("add_theme")
calc_element = mkfunc("calc_element")
element_blank = mkfunc("element_blank")
element_line = mkfunc("element_line")
element_rect = mkfunc("element_rect")
element_text = mkfunc("element_text")
theme = mkfunc("theme")
theme_bw = mkfunc("theme_bw")
theme_grey = mkfunc("theme_grey")
theme_classic = mkfunc("theme_classic")
aes = mkfunc("aes")
aes_all = mkfunc("aes_all")
aes_auto = mkfunc("aes_auto")
aes_string = mkfunc("aes_string")
geom_smooth = mkfunc("geom_smooth")
ggtitle = mkfunc("ggtitle")
