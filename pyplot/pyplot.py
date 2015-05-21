import click
import subprocess

class GGStatement(object):
  def __init__(self, name, *args, **kwargs):
    self.name = name
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
    return self.to_stmts().save(name, *args, **kwargs)


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
    stmts.extend(o.to_stmts().stmts)
    return GGStatements(stmts)

  @property
  def r(self):
    return " + ".join(map(GGStatement.to_r, self.stmts))

  def __str__(self):
    return self.r

  def save(self, name, *args, **kwargs):
    kwdefaults = {
      'width': 10,
      'height': 8,
      'scale': 1
    }
    keys_to_rm = ["prefix"]
    varname = "p"
    header = "library(ggplot2)"


    kwargs = dict([(k,v) for k,v in kwargs.items() if v is not None])
    prefix = kwargs.get('prefix', '')
    for key in keys_to_rm:
      if key in kwargs: del kwargs[key]
    kwdefaults.update(kwargs)
    kwargs = kwdefaults



    prog = "%(header)s\n%(prefix)s\n%(varname)s = %(prog)s" % {
      'header': header,
      'prefix': prefix,
      'varname' : varname,
      'prog': self.r
    }

    if name:
      stmt = GGStatement("ggsave", "'%s'" % name, varname, *args, **kwargs)
      prog = "%s\n%s" % (prog, stmt.r)

    print prog
    print

    if not name: return prog

    # Run the generated R code
    input_cmd = ["echo", prog]
    input_proc = subprocess.Popen(input_cmd, stdout=subprocess.PIPE)
    r_cmd = "R --no-save --quiet"
    subprocess.call(r_cmd, 
                    stdin=input_proc.stdout, 
                    #stderr=subprocess.STDOUT,
                    shell=True)
    return prog



def mkfunc(fname):
  def f(*args, **kwargs):
    return GGStatement(fname, *args, **kwargs)
  f.__name__ = fname
  return f


ggplot = mkfunc("ggplot")
aes = mkfunc("aes")
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
guides = mkfunc("guides")
guide_legend = mkfunc("guide_legend")
guide_colourbar = mkfunc("guide_colourbar")
scale_alpha = mkfunc("scale_alpha")
scale_area = mkfunc("scale_area")
scale_colour_brewer = mkfunc("scale_colour_brewer")
scale_color_brewer = mkfunc("scale_color_brewer")
scale_fill_brewer = mkfunc("scale_fill_brewer")
scale_colour_gradient = mkfunc("scale_colour_gradient")
scale_color_gradient = mkfunc("scale_color_gradient")
scale_fill_gradient = mkfunc("scale_fill_gradient")
scale_size = mkfunc("scale_size")
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
position_dodge = mkfunc("position_dodge")
position_fill = mkfunc("position_fill")
position_identity = mkfunc("position_identity")
position_stack = mkfunc("position_stack")
position_jitter = mkfunc("position_jitter")

def data_sql(db, sql):
  if not db:
    if sql:
      print "ERR: -db option must be set if using -sql"
    return ""


  cmd = """
library(RPostgreSQL)
library(RColorBrewer)
cbPalette <- brewer.pal(8, "Dark2")
drv = dbDriver('PostgreSQL')
con = dbConnect(drv, dbname='%(db_name)s')
q = "%(query)s"
data = dbGetQuery(con, q)
  """ % {
    'db_name' : db,
    'query' : sql
  }
  return cmd

def data_csv(fname, *args, **kwargs):
  return "data = %s" % GGStatement("read.csv", fname, *args, **kwargs).r


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

    



