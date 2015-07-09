"""
run the following for help

  python bin/runpygg.py --help
"""
import os
import click
import re
import subprocess
import random
import csv
from collections import defaultdict

quote1re = re.compile("\"")
quote2re = re.compile("'")

class GGStatement(object):
  def __init__(self, _name, *args, **kwargs):
    self.name = _name
    self.args = args
    self.kwargs = kwargs


  def to_stmts(self):
    return GGStatements([self])

  def __add__(self, o):
    if not o: return self.to_stmts()
    return self.to_stmts() + o.to_stmts()


  @staticmethod
  def to_r(o):
    try:
      return o.r
    except:
      pass

    return str(o)

  @property
  def r(self):
    args = map(GGStatement.to_r, self.args)
    kw2s = lambda (k,v): "%s=%s" % (k, GGStatement.to_r(v))
    kwargs = map(kw2s, self.kwargs.iteritems())

    all_args = args + kwargs
    all_args = filter(bool, all_args)
    all_args = ", ".join(all_args)
    cmd = "%s(%s)" % (self.name, all_args)
    return cmd

  def __str__(self):
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
    if not o: return self
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
    return " + ".join(map(GGStatement.to_r, self.stmts))

  def __str__(self):
    return self.r

  def save(self, name, *args, **kwargs):
    return ggsave(name, self, *args, **kwargs)




###################################################
#
#  Specialized expressions that must be in Python
#
###################################################


def data_sql(db, sql):
  """
  Load file using RPostgreSQL
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
    'db_name' : db,
    'query' : sql
  }

def data_csv(fname, *args, **kwargs):
  "Load csv file using read.csv"
  # wrap file name into R string text
  fname = '"%s"' % fname
  return "data = %s" % GGStatement("read.csv", fname, *args, **kwargs).r

def data_dataframe(df, *args, **kwargs):
  "export data frame as csv file, then read it in R"
  fname = "/tmp/_pygg_data.csv"
  df.to_csv(fname, sep=',', encoding='utf-8')
  kwargs["sep"] = ","
  return data_csv("%s" % fname, *args, **kwargs)

def data_py(o, *args, **kwargs):
  """
  converts python object into R Dataframe definition
  converts following data structures:

    row oriented list of dictionaries:

        [ { 'x': 0, 'y': 1, ...}, ... ]

    col oriented dictionary of lists

        { 'x': [0,1,2...], 'y': [...], ... }


  if the dataset is larger than 100 records, it is written to 
  a csv file and loaded using data_csv

  @param o python object to convert
  @param args argument list to pass to data.frame
  @param kwargs keyword args to pass to data.frame
  @return expression to define data.frame object and set it to variable "data"
        
        data = data.frame(cbind(..yourdata..), *args, **kwargs)
  """

  try:
    from pandas import DataFrame
    if isinstance(df, DataFrame):
      return data_dataframe(o, *args, **kwargs)
  except:
    pass

  def totext(v): 
    " translate a python base value into R text "
    if v is None: 
      return "NA"
    if isinstance(v, basestring): 
      v = quote1re.sub("\\\"", v)
      v = quote2re.sub("\\'", v)
      return "'%s'" % v
    return str(v)

  def l2rtext(l):
    "translate list of python primitives into list definition in R"
    return "c(%s)" % ", ".join(map(totext, l))

  # convert row to col
  if isinstance(o, list):
    newo = defaultdict(list)
    keys = set()
    map(keys.update, [d.keys() for d in o])
    for d in o:
      for key in keys:
        newo[key].append(d.get(key, None))
    o = newo

  # write to CSV file
  if len(o) > 0 and len(o.values()[0]) > 100:
    fname = "/tmp/pygg_%s.csv" % random.randint(0, 2<<32)
    with file(fname, "w") as f:
      keys = o.keys()
      writer = csv.DictWriter(f, fieldnames=keys)
      writer.writeheader()
      for rowidx in range(len(o.values()[0])):
        row = {key: o[key][rowidx] for key in keys}
        writer.writerow(row)
    return data_csv(fname, *args, **kwargs)


  # convert into R code that creates the data.frame
  defs = []
  for col, vals in o.iteritems():
    stmt = "%s = %s" % (col, l2rtext(vals))
    defs.append(stmt)
  data_arg = "cbind(%s)" % ", ".join(defs)

  return "data = %s" % GGStatement("data.frame", data_arg, *args, **kwargs).r



###################################################
#
#  Facets use R formulas x ~ y.  We need custom API for them
#  e.g., facet_grid(x, y, ...)
#
###################################################


def facet_wrap(x, y, *args, **kwargs):
  if not x and not y: 
    print "WARN: facet_wrap got x=None, y=None"
    return None
  if not x: x = ""
  if not y: y = "."

  facets = "%s~%s" % (x,y)
  return GGStatement("facet_wrap", facets, *args, **kwargs)


def facet_grid(x, y, *args, **kwargs):
  facets = filter(bool, [x, y])
  if not facets:
    print "WARN: facet_grid got x=None, y=None"
    return None
  facets = "%s~" % "+".join(facets)

  if not x: x = "."
  if not y: y = "."

  facets = "%s~%s" % (x,y)
  return GGStatement("facet_grid", facets, *args, **kwargs)


###################################################
#
#  ggsave talks to the external world, so needs custom support
#
###################################################



def ggsave(name, plot, *args, **kwargs):
  """
  @param name output file name.  if None, don't run R command
  @param kwargs keyword args to pass to ggsave.  The following are special
          keywords for the python save method

    prefix: string containing R code to run before the ggplot command
    quiet:  if Truthy, don't print out R program string

  """
  kwdefaults = {
    'width': 10,
    'height': 8,
    'scale': 1
  }
  keys_to_rm = ["prefix", "quiet"]
  varname = "p"
  header = "library(ggplot2)"

  kwargs = dict([(k,v) for k,v in kwargs.items() if v is not None])
  prefix = kwargs.get('prefix', '')
  quiet = kwargs.get("quiet", False)
  for key in keys_to_rm:
    if key in kwargs: del kwargs[key]
  kwdefaults.update(kwargs)
  kwargs = kwdefaults

  prog = "%(header)s\n%(prefix)s\n%(varname)s = %(prog)s" % {
    'header': header,
    'prefix': prefix,
    'varname' : varname,
    'prog': plot.r
  }

  if name:
    stmt = GGStatement("ggsave", "'%s'" % name, varname, *args, **kwargs)
    prog = "%s\n%s" % (prog, stmt.r)

  if not quiet:
    print prog
    print

  if not name: return prog

  # Run the generated R code
  FNULL = None
  if quiet:
    FNULL = open(os.devnull, 'w')
  input_cmd = ["echo", prog]
  input_proc = subprocess.Popen(input_cmd, stdout=subprocess.PIPE)
  r_cmd = "R --no-save --quiet"
  subprocess.call(r_cmd, 
                  stdin=input_proc.stdout, 
                  stdout=FNULL,
                  stderr=subprocess.STDOUT,
                  shell=True)
  return prog








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
