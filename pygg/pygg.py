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
                         for k, v in sorted(iter(o.items()), key=lambda x: x[0])])
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
      custom_stmts: a string containing R code to run after the ggplot object has been created, but before ggsave
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
    custom_stmts = kwargs.get('custom_stmts')
    libs = kwargs.get('libs', [])
    libs = '\n'.join(["library(%s)" % lib for lib in libs])
    quiet = kwargs.get("quiet", False)
    kwargs = {k: v for k, v in kwargs.items()
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

    stmts = [
        "library(ggplot2)",
        libs,
        data_src,
        prefix,
        postfix,
        "%s = %s" % (varname, plot.r),
        custom_stmts
    ]
    stmts = filter(bool, stmts)
    prog = "\n".join(stmts)

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
  xlookup = dict(
      continuous = scale_x_continuous,
      date = scale_x_date,
      datetime = scale_x_datetime,
      discrete = scale_x_discrete,
      log10 = scale_x_log10,
      reverse = scale_x_reverse,
      sqrt = scale_x_sqrt
  )
  ylookup = dict(
      continuous = scale_y_continuous,
      date = scale_y_date,
      datetime = scale_y_datetime,
      discrete = scale_y_discrete,
      log10 = scale_y_log10,
      reverse = scale_y_reverse,
      sqrt = scale_y_sqrt
  )

  xfunc = xlookup.get(xsuffix, scale_x_continuous)
  yfunc = ylookup.get(ysuffix, scale_y_continuous)
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


# generated by make_ggplot2_binding
# ggplot2 library version: 3.3.5
# date: Mon Jul 19 10:35:38 2021
aes = make_ggplot2_binding("aes")
aes_ = make_ggplot2_binding("aes_")
aes_all = make_ggplot2_binding("aes_all")
aes_auto = make_ggplot2_binding("aes_auto")
aes_string = make_ggplot2_binding("aes_string")
after_scale = make_ggplot2_binding("after_scale")
after_stat = make_ggplot2_binding("after_stat")
alpha = make_ggplot2_binding("alpha")
annotate = make_ggplot2_binding("annotate")
annotation_custom = make_ggplot2_binding("annotation_custom")
annotation_logticks = make_ggplot2_binding("annotation_logticks")
annotation_map = make_ggplot2_binding("annotation_map")
annotation_raster = make_ggplot2_binding("annotation_raster")
arrow = make_ggplot2_binding("arrow")
as_label = make_ggplot2_binding("as_label")
as_labeller = make_ggplot2_binding("as_labeller")
autolayer = make_ggplot2_binding("autolayer")
autoplot = make_ggplot2_binding("autoplot")
binned_scale = make_ggplot2_binding("binned_scale")
borders = make_ggplot2_binding("borders")
calc_element = make_ggplot2_binding("calc_element")
combine_vars = make_ggplot2_binding("combine_vars")
continuous_scale = make_ggplot2_binding("continuous_scale")
coord_cartesian = make_ggplot2_binding("coord_cartesian")
coord_equal = make_ggplot2_binding("coord_equal")
coord_fixed = make_ggplot2_binding("coord_fixed")
coord_flip = make_ggplot2_binding("coord_flip")
coord_map = make_ggplot2_binding("coord_map")
coord_munch = make_ggplot2_binding("coord_munch")
coord_polar = make_ggplot2_binding("coord_polar")
coord_quickmap = make_ggplot2_binding("coord_quickmap")
coord_sf = make_ggplot2_binding("coord_sf")
coord_trans = make_ggplot2_binding("coord_trans")
cut_interval = make_ggplot2_binding("cut_interval")
cut_number = make_ggplot2_binding("cut_number")
cut_width = make_ggplot2_binding("cut_width")
derive = make_ggplot2_binding("derive")
discrete_scale = make_ggplot2_binding("discrete_scale")
draw_key_abline = make_ggplot2_binding("draw_key_abline")
draw_key_blank = make_ggplot2_binding("draw_key_blank")
draw_key_boxplot = make_ggplot2_binding("draw_key_boxplot")
draw_key_crossbar = make_ggplot2_binding("draw_key_crossbar")
draw_key_dotplot = make_ggplot2_binding("draw_key_dotplot")
draw_key_label = make_ggplot2_binding("draw_key_label")
draw_key_path = make_ggplot2_binding("draw_key_path")
draw_key_point = make_ggplot2_binding("draw_key_point")
draw_key_pointrange = make_ggplot2_binding("draw_key_pointrange")
draw_key_polygon = make_ggplot2_binding("draw_key_polygon")
draw_key_rect = make_ggplot2_binding("draw_key_rect")
draw_key_smooth = make_ggplot2_binding("draw_key_smooth")
draw_key_text = make_ggplot2_binding("draw_key_text")
draw_key_timeseries = make_ggplot2_binding("draw_key_timeseries")
draw_key_vline = make_ggplot2_binding("draw_key_vline")
draw_key_vpath = make_ggplot2_binding("draw_key_vpath")
dup_axis = make_ggplot2_binding("dup_axis")
el_def = make_ggplot2_binding("el_def")
element_blank = make_ggplot2_binding("element_blank")
element_grob = make_ggplot2_binding("element_grob")
element_line = make_ggplot2_binding("element_line")
element_rect = make_ggplot2_binding("element_rect")
element_render = make_ggplot2_binding("element_render")
element_text = make_ggplot2_binding("element_text")
enexpr = make_ggplot2_binding("enexpr")
enexprs = make_ggplot2_binding("enexprs")
enquo = make_ggplot2_binding("enquo")
enquos = make_ggplot2_binding("enquos")
ensym = make_ggplot2_binding("ensym")
ensyms = make_ggplot2_binding("ensyms")
expand_limits = make_ggplot2_binding("expand_limits")
expand_scale = make_ggplot2_binding("expand_scale")
expansion = make_ggplot2_binding("expansion")
expr = make_ggplot2_binding("expr")
facet_null = make_ggplot2_binding("facet_null")
find_panel = make_ggplot2_binding("find_panel")
flip_data = make_ggplot2_binding("flip_data")
flipped_names = make_ggplot2_binding("flipped_names")
geom_abline = make_ggplot2_binding("geom_abline")
geom_area = make_ggplot2_binding("geom_area")
geom_bar = make_ggplot2_binding("geom_bar")
geom_bin_2d = make_ggplot2_binding("geom_bin_2d")
geom_bin2d = make_ggplot2_binding("geom_bin2d")
geom_blank = make_ggplot2_binding("geom_blank")
geom_boxplot = make_ggplot2_binding("geom_boxplot")
geom_col = make_ggplot2_binding("geom_col")
geom_contour = make_ggplot2_binding("geom_contour")
geom_contour_filled = make_ggplot2_binding("geom_contour_filled")
geom_count = make_ggplot2_binding("geom_count")
geom_crossbar = make_ggplot2_binding("geom_crossbar")
geom_curve = make_ggplot2_binding("geom_curve")
geom_density = make_ggplot2_binding("geom_density")
geom_density_2d = make_ggplot2_binding("geom_density_2d")
geom_density_2d_filled = make_ggplot2_binding("geom_density_2d_filled")
geom_density2d = make_ggplot2_binding("geom_density2d")
geom_density2d_filled = make_ggplot2_binding("geom_density2d_filled")
geom_dotplot = make_ggplot2_binding("geom_dotplot")
geom_errorbar = make_ggplot2_binding("geom_errorbar")
geom_errorbarh = make_ggplot2_binding("geom_errorbarh")
geom_freqpoly = make_ggplot2_binding("geom_freqpoly")
geom_function = make_ggplot2_binding("geom_function")
geom_hex = make_ggplot2_binding("geom_hex")
geom_histogram = make_ggplot2_binding("geom_histogram")
geom_hline = make_ggplot2_binding("geom_hline")
geom_jitter = make_ggplot2_binding("geom_jitter")
geom_label = make_ggplot2_binding("geom_label")
geom_line = make_ggplot2_binding("geom_line")
geom_linerange = make_ggplot2_binding("geom_linerange")
geom_map = make_ggplot2_binding("geom_map")
geom_path = make_ggplot2_binding("geom_path")
geom_point = make_ggplot2_binding("geom_point")
geom_pointrange = make_ggplot2_binding("geom_pointrange")
geom_polygon = make_ggplot2_binding("geom_polygon")
geom_qq = make_ggplot2_binding("geom_qq")
geom_qq_line = make_ggplot2_binding("geom_qq_line")
geom_quantile = make_ggplot2_binding("geom_quantile")
geom_raster = make_ggplot2_binding("geom_raster")
geom_rect = make_ggplot2_binding("geom_rect")
geom_ribbon = make_ggplot2_binding("geom_ribbon")
geom_rug = make_ggplot2_binding("geom_rug")
geom_segment = make_ggplot2_binding("geom_segment")
geom_sf = make_ggplot2_binding("geom_sf")
geom_sf_label = make_ggplot2_binding("geom_sf_label")
geom_sf_text = make_ggplot2_binding("geom_sf_text")
geom_smooth = make_ggplot2_binding("geom_smooth")
geom_spoke = make_ggplot2_binding("geom_spoke")
geom_step = make_ggplot2_binding("geom_step")
geom_text = make_ggplot2_binding("geom_text")
geom_tile = make_ggplot2_binding("geom_tile")
geom_violin = make_ggplot2_binding("geom_violin")
geom_vline = make_ggplot2_binding("geom_vline")
get_alt_text = make_ggplot2_binding("get_alt_text")
get_element_tree = make_ggplot2_binding("get_element_tree")
ggplot_add = make_ggplot2_binding("ggplot_add")
ggproto = make_ggplot2_binding("ggproto")
ggproto_parent = make_ggplot2_binding("ggproto_parent")
ggtitle = make_ggplot2_binding("ggtitle")
guide_axis = make_ggplot2_binding("guide_axis")
guide_bins = make_ggplot2_binding("guide_bins")
guide_colorbar = make_ggplot2_binding("guide_colorbar")
guide_colorsteps = make_ggplot2_binding("guide_colorsteps")
guide_colourbar = make_ggplot2_binding("guide_colourbar")
guide_coloursteps = make_ggplot2_binding("guide_coloursteps")
guide_gengrob = make_ggplot2_binding("guide_gengrob")
guide_geom = make_ggplot2_binding("guide_geom")
guide_legend = make_ggplot2_binding("guide_legend")
guide_merge = make_ggplot2_binding("guide_merge")
guide_none = make_ggplot2_binding("guide_none")
guide_train = make_ggplot2_binding("guide_train")
guide_transform = make_ggplot2_binding("guide_transform")
guides = make_ggplot2_binding("guides")
has_flipped_aes = make_ggplot2_binding("has_flipped_aes")
label_both = make_ggplot2_binding("label_both")
label_bquote = make_ggplot2_binding("label_bquote")
label_context = make_ggplot2_binding("label_context")
label_parsed = make_ggplot2_binding("label_parsed")
label_value = make_ggplot2_binding("label_value")
label_wrap_gen = make_ggplot2_binding("label_wrap_gen")
labeller = make_ggplot2_binding("labeller")
labs = make_ggplot2_binding("labs")
layer = make_ggplot2_binding("layer")
layer_data = make_ggplot2_binding("layer_data")
layer_grob = make_ggplot2_binding("layer_grob")
layer_scales = make_ggplot2_binding("layer_scales")
layer_sf = make_ggplot2_binding("layer_sf")
lims = make_ggplot2_binding("lims")
margin = make_ggplot2_binding("margin")
max_height = make_ggplot2_binding("max_height")
max_width = make_ggplot2_binding("max_width")
merge_element = make_ggplot2_binding("merge_element")
panel_cols = make_ggplot2_binding("panel_cols")
panel_rows = make_ggplot2_binding("panel_rows")
position_dodge = make_ggplot2_binding("position_dodge")
position_dodge2 = make_ggplot2_binding("position_dodge2")
position_fill = make_ggplot2_binding("position_fill")
position_identity = make_ggplot2_binding("position_identity")
position_jitter = make_ggplot2_binding("position_jitter")
position_jitterdodge = make_ggplot2_binding("position_jitterdodge")
position_nudge = make_ggplot2_binding("position_nudge")
position_stack = make_ggplot2_binding("position_stack")
qplot = make_ggplot2_binding("qplot")
quickplot = make_ggplot2_binding("quickplot")
quo = make_ggplot2_binding("quo")
quo_name = make_ggplot2_binding("quo_name")
quos = make_ggplot2_binding("quos")
register_theme_elements = make_ggplot2_binding("register_theme_elements")
rel = make_ggplot2_binding("rel")
remove_missing = make_ggplot2_binding("remove_missing")
render_axes = make_ggplot2_binding("render_axes")
render_strips = make_ggplot2_binding("render_strips")
reset_theme_settings = make_ggplot2_binding("reset_theme_settings")
resolution = make_ggplot2_binding("resolution")
scale_alpha = make_ggplot2_binding("scale_alpha")
scale_alpha_binned = make_ggplot2_binding("scale_alpha_binned")
scale_alpha_continuous = make_ggplot2_binding("scale_alpha_continuous")
scale_alpha_date = make_ggplot2_binding("scale_alpha_date")
scale_alpha_datetime = make_ggplot2_binding("scale_alpha_datetime")
scale_alpha_discrete = make_ggplot2_binding("scale_alpha_discrete")
scale_alpha_identity = make_ggplot2_binding("scale_alpha_identity")
scale_alpha_manual = make_ggplot2_binding("scale_alpha_manual")
scale_alpha_ordinal = make_ggplot2_binding("scale_alpha_ordinal")
scale_color_binned = make_ggplot2_binding("scale_color_binned")
scale_color_brewer = make_ggplot2_binding("scale_color_brewer")
scale_color_continuous = make_ggplot2_binding("scale_color_continuous")
scale_color_date = make_ggplot2_binding("scale_color_date")
scale_color_datetime = make_ggplot2_binding("scale_color_datetime")
scale_color_discrete = make_ggplot2_binding("scale_color_discrete")
scale_color_distiller = make_ggplot2_binding("scale_color_distiller")
scale_color_fermenter = make_ggplot2_binding("scale_color_fermenter")
scale_color_gradient = make_ggplot2_binding("scale_color_gradient")
scale_color_gradient2 = make_ggplot2_binding("scale_color_gradient2")
scale_color_gradientn = make_ggplot2_binding("scale_color_gradientn")
scale_color_grey = make_ggplot2_binding("scale_color_grey")
scale_color_hue = make_ggplot2_binding("scale_color_hue")
scale_color_identity = make_ggplot2_binding("scale_color_identity")
scale_color_manual = make_ggplot2_binding("scale_color_manual")
scale_color_ordinal = make_ggplot2_binding("scale_color_ordinal")
scale_color_steps = make_ggplot2_binding("scale_color_steps")
scale_color_steps2 = make_ggplot2_binding("scale_color_steps2")
scale_color_stepsn = make_ggplot2_binding("scale_color_stepsn")
scale_color_viridis_b = make_ggplot2_binding("scale_color_viridis_b")
scale_color_viridis_c = make_ggplot2_binding("scale_color_viridis_c")
scale_color_viridis_d = make_ggplot2_binding("scale_color_viridis_d")
scale_colour_binned = make_ggplot2_binding("scale_colour_binned")
scale_colour_brewer = make_ggplot2_binding("scale_colour_brewer")
scale_colour_continuous = make_ggplot2_binding("scale_colour_continuous")
scale_colour_date = make_ggplot2_binding("scale_colour_date")
scale_colour_datetime = make_ggplot2_binding("scale_colour_datetime")
scale_colour_discrete = make_ggplot2_binding("scale_colour_discrete")
scale_colour_distiller = make_ggplot2_binding("scale_colour_distiller")
scale_colour_fermenter = make_ggplot2_binding("scale_colour_fermenter")
scale_colour_gradient = make_ggplot2_binding("scale_colour_gradient")
scale_colour_gradient2 = make_ggplot2_binding("scale_colour_gradient2")
scale_colour_gradientn = make_ggplot2_binding("scale_colour_gradientn")
scale_colour_grey = make_ggplot2_binding("scale_colour_grey")
scale_colour_hue = make_ggplot2_binding("scale_colour_hue")
scale_colour_identity = make_ggplot2_binding("scale_colour_identity")
scale_colour_manual = make_ggplot2_binding("scale_colour_manual")
scale_colour_ordinal = make_ggplot2_binding("scale_colour_ordinal")
scale_colour_steps = make_ggplot2_binding("scale_colour_steps")
scale_colour_steps2 = make_ggplot2_binding("scale_colour_steps2")
scale_colour_stepsn = make_ggplot2_binding("scale_colour_stepsn")
scale_colour_viridis_b = make_ggplot2_binding("scale_colour_viridis_b")
scale_colour_viridis_c = make_ggplot2_binding("scale_colour_viridis_c")
scale_colour_viridis_d = make_ggplot2_binding("scale_colour_viridis_d")
scale_continuous_identity = make_ggplot2_binding("scale_continuous_identity")
scale_discrete_identity = make_ggplot2_binding("scale_discrete_identity")
scale_discrete_manual = make_ggplot2_binding("scale_discrete_manual")
scale_fill_binned = make_ggplot2_binding("scale_fill_binned")
scale_fill_brewer = make_ggplot2_binding("scale_fill_brewer")
scale_fill_continuous = make_ggplot2_binding("scale_fill_continuous")
scale_fill_date = make_ggplot2_binding("scale_fill_date")
scale_fill_datetime = make_ggplot2_binding("scale_fill_datetime")
scale_fill_discrete = make_ggplot2_binding("scale_fill_discrete")
scale_fill_distiller = make_ggplot2_binding("scale_fill_distiller")
scale_fill_fermenter = make_ggplot2_binding("scale_fill_fermenter")
scale_fill_gradient = make_ggplot2_binding("scale_fill_gradient")
scale_fill_gradient2 = make_ggplot2_binding("scale_fill_gradient2")
scale_fill_gradientn = make_ggplot2_binding("scale_fill_gradientn")
scale_fill_grey = make_ggplot2_binding("scale_fill_grey")
scale_fill_hue = make_ggplot2_binding("scale_fill_hue")
scale_fill_identity = make_ggplot2_binding("scale_fill_identity")
scale_fill_manual = make_ggplot2_binding("scale_fill_manual")
scale_fill_ordinal = make_ggplot2_binding("scale_fill_ordinal")
scale_fill_steps = make_ggplot2_binding("scale_fill_steps")
scale_fill_steps2 = make_ggplot2_binding("scale_fill_steps2")
scale_fill_stepsn = make_ggplot2_binding("scale_fill_stepsn")
scale_fill_viridis_b = make_ggplot2_binding("scale_fill_viridis_b")
scale_fill_viridis_c = make_ggplot2_binding("scale_fill_viridis_c")
scale_fill_viridis_d = make_ggplot2_binding("scale_fill_viridis_d")
scale_linetype = make_ggplot2_binding("scale_linetype")
scale_linetype_binned = make_ggplot2_binding("scale_linetype_binned")
scale_linetype_continuous = make_ggplot2_binding("scale_linetype_continuous")
scale_linetype_discrete = make_ggplot2_binding("scale_linetype_discrete")
scale_linetype_identity = make_ggplot2_binding("scale_linetype_identity")
scale_linetype_manual = make_ggplot2_binding("scale_linetype_manual")
scale_radius = make_ggplot2_binding("scale_radius")
scale_shape = make_ggplot2_binding("scale_shape")
scale_shape_binned = make_ggplot2_binding("scale_shape_binned")
scale_shape_continuous = make_ggplot2_binding("scale_shape_continuous")
scale_shape_discrete = make_ggplot2_binding("scale_shape_discrete")
scale_shape_identity = make_ggplot2_binding("scale_shape_identity")
scale_shape_manual = make_ggplot2_binding("scale_shape_manual")
scale_shape_ordinal = make_ggplot2_binding("scale_shape_ordinal")
scale_size = make_ggplot2_binding("scale_size")
scale_size_area = make_ggplot2_binding("scale_size_area")
scale_size_binned = make_ggplot2_binding("scale_size_binned")
scale_size_binned_area = make_ggplot2_binding("scale_size_binned_area")
scale_size_continuous = make_ggplot2_binding("scale_size_continuous")
scale_size_date = make_ggplot2_binding("scale_size_date")
scale_size_datetime = make_ggplot2_binding("scale_size_datetime")
scale_size_discrete = make_ggplot2_binding("scale_size_discrete")
scale_size_identity = make_ggplot2_binding("scale_size_identity")
scale_size_manual = make_ggplot2_binding("scale_size_manual")
scale_size_ordinal = make_ggplot2_binding("scale_size_ordinal")
scale_type = make_ggplot2_binding("scale_type")
scale_x_binned = make_ggplot2_binding("scale_x_binned")
scale_x_continuous = make_ggplot2_binding("scale_x_continuous")
scale_x_date = make_ggplot2_binding("scale_x_date")
scale_x_datetime = make_ggplot2_binding("scale_x_datetime")
scale_x_discrete = make_ggplot2_binding("scale_x_discrete")
scale_x_log10 = make_ggplot2_binding("scale_x_log10")
scale_x_reverse = make_ggplot2_binding("scale_x_reverse")
scale_x_sqrt = make_ggplot2_binding("scale_x_sqrt")
scale_x_time = make_ggplot2_binding("scale_x_time")
scale_y_binned = make_ggplot2_binding("scale_y_binned")
scale_y_continuous = make_ggplot2_binding("scale_y_continuous")
scale_y_date = make_ggplot2_binding("scale_y_date")
scale_y_datetime = make_ggplot2_binding("scale_y_datetime")
scale_y_discrete = make_ggplot2_binding("scale_y_discrete")
scale_y_log10 = make_ggplot2_binding("scale_y_log10")
scale_y_reverse = make_ggplot2_binding("scale_y_reverse")
scale_y_sqrt = make_ggplot2_binding("scale_y_sqrt")
scale_y_time = make_ggplot2_binding("scale_y_time")
sec_axis = make_ggplot2_binding("sec_axis")
set_last_plot = make_ggplot2_binding("set_last_plot")
sf_transform_xy = make_ggplot2_binding("sf_transform_xy")
stage = make_ggplot2_binding("stage")
standardise_aes_names = make_ggplot2_binding("standardise_aes_names")
stat = make_ggplot2_binding("stat")
stat_bin = make_ggplot2_binding("stat_bin")
stat_bin_2d = make_ggplot2_binding("stat_bin_2d")
stat_bin_hex = make_ggplot2_binding("stat_bin_hex")
stat_bin2d = make_ggplot2_binding("stat_bin2d")
stat_binhex = make_ggplot2_binding("stat_binhex")
stat_boxplot = make_ggplot2_binding("stat_boxplot")
stat_contour = make_ggplot2_binding("stat_contour")
stat_contour_filled = make_ggplot2_binding("stat_contour_filled")
stat_count = make_ggplot2_binding("stat_count")
stat_density = make_ggplot2_binding("stat_density")
stat_density_2d = make_ggplot2_binding("stat_density_2d")
stat_density_2d_filled = make_ggplot2_binding("stat_density_2d_filled")
stat_density2d = make_ggplot2_binding("stat_density2d")
stat_density2d_filled = make_ggplot2_binding("stat_density2d_filled")
stat_ecdf = make_ggplot2_binding("stat_ecdf")
stat_ellipse = make_ggplot2_binding("stat_ellipse")
stat_function = make_ggplot2_binding("stat_function")
stat_identity = make_ggplot2_binding("stat_identity")
stat_qq = make_ggplot2_binding("stat_qq")
stat_qq_line = make_ggplot2_binding("stat_qq_line")
stat_quantile = make_ggplot2_binding("stat_quantile")
stat_sf = make_ggplot2_binding("stat_sf")
stat_sf_coordinates = make_ggplot2_binding("stat_sf_coordinates")
stat_smooth = make_ggplot2_binding("stat_smooth")
stat_spoke = make_ggplot2_binding("stat_spoke")
stat_sum = make_ggplot2_binding("stat_sum")
stat_summary = make_ggplot2_binding("stat_summary")
stat_summary_2d = make_ggplot2_binding("stat_summary_2d")
stat_summary_bin = make_ggplot2_binding("stat_summary_bin")
stat_summary_hex = make_ggplot2_binding("stat_summary_hex")
stat_summary2d = make_ggplot2_binding("stat_summary2d")
stat_unique = make_ggplot2_binding("stat_unique")
stat_ydensity = make_ggplot2_binding("stat_ydensity")
summarise_coord = make_ggplot2_binding("summarise_coord")
summarise_layers = make_ggplot2_binding("summarise_layers")
summarise_layout = make_ggplot2_binding("summarise_layout")
sym = make_ggplot2_binding("sym")
syms = make_ggplot2_binding("syms")
theme = make_ggplot2_binding("theme")
theme_bw = make_ggplot2_binding("theme_bw")
theme_classic = make_ggplot2_binding("theme_classic")
theme_dark = make_ggplot2_binding("theme_dark")
theme_get = make_ggplot2_binding("theme_get")
theme_gray = make_ggplot2_binding("theme_gray")
theme_grey = make_ggplot2_binding("theme_grey")
theme_light = make_ggplot2_binding("theme_light")
theme_linedraw = make_ggplot2_binding("theme_linedraw")
theme_minimal = make_ggplot2_binding("theme_minimal")
theme_replace = make_ggplot2_binding("theme_replace")
theme_set = make_ggplot2_binding("theme_set")
theme_test = make_ggplot2_binding("theme_test")
theme_update = make_ggplot2_binding("theme_update")
theme_void = make_ggplot2_binding("theme_void")
transform_position = make_ggplot2_binding("transform_position")
unit = make_ggplot2_binding("unit")
update_geom_defaults = make_ggplot2_binding("update_geom_defaults")
update_labels = make_ggplot2_binding("update_labels")
update_stat_defaults = make_ggplot2_binding("update_stat_defaults")
vars = make_ggplot2_binding("vars")
wrap_dims = make_ggplot2_binding("wrap_dims")
xlab = make_ggplot2_binding("xlab")
xlim = make_ggplot2_binding("xlim")
ylab = make_ggplot2_binding("ylab")
ylim = make_ggplot2_binding("ylim")
zeroGrob = make_ggplot2_binding("zeroGrob")
