#!/usr/bin/env python2.7

try:
  activate_this = './bin/activate_this.py'
  exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))
except:
  pass


import click
from pygg import *


@click.command()
@click.option("-c", help="pygg command")
@click.option("-prefix", help="R commands to prefix")
@click.option("-csv", type=str, help="CSV file to load into var \"data\"")
@click.option("-db", help="Database name if using -sql")
@click.option("-sql", help="SQL query to use as dataset.  Loaded in var \"data\"")
@click.option("-o", help="Output file to save graphic.  Else print program and exit")
@click.option("-w", type=float, default=10, help="width of output file")
@click.option("-h", type=float, default=8, help="height of output file")
@click.option("-scale", type=float, default=1.0, help="scaling of output file")
def main(c, prefix, csv, db, sql, o, w, h, scale):
  """
  ggplot2 syntax in Python.

  Run pygg command from command line

    python pygg -c "ggplot('diamonds', aes('carat', 'price')) + geom_point()"

  Import into your python program to use ggplot

    \b
    from pygg import *
    p = ggplot('diamonds', aes('carat', y='price')) + geom_point()
    p = p + facet_wrap(None, "color")

    \b
    # prefix argument is a string to execute before running ggplot and ggsave commands
    prefix = \"\"\"diamonds =  ...R code to load data...  \"\"\"
    ggsave("test.pdf", p, prefix=prefix)
    # the following is a shorthand
    p.save("test.pdf", prefix=prefix)


  Use convenience, ggsave() takes a data=... keyword argument for common data objects

    \b
    # load from database query
    ggsave(..., data = data_sql('DBNAME', 'SELECT * FROM T'))

    \b
    # load from CSV file.  Takse same arguments as R's read.csv
    ggsave(..., data = "FILENAME.csv")
    # or, to control the seperator :
    ggsave(..., prefix = data_csv("FILENAME", sep=','))

    \b
    # load column or row oriented python object.  Run help(data_py) for more details
    ggsave(..., data = {'x': [0,1,2], 'y': [9,8,7]})
    ggsave(..., data = [{'x': 0, 'y': 1}, {'x': 2, 'y': 3}])

    \b
    df = ...pandas DataFrame object...
    ggsave(..., data = df)


  Example commands

    \b
    python runpygg -db database -sql "SELECT 1 as x, 2 as y" -c "ggplot('data', aes('x', 'y')) + geom_point()" -o test.pdf
    python runpygg -csv mydata.csv -c "ggplot('data', aes(x='attr1', y='attr2')) + geom_point()"


  Caveats: Does not copy and import data between python and R, so pygg only works for SQL or CSV file inputs
  """

  if not c: 
    print("no command.  exiting")
    return

  kwargs = {
    'width': w,
    'height': h,
    'scale': scale,
    'prefix': '\n'.join(filter(bool, [prefix]))
  }

  if csv:
    kwargs['data'] = csv
  else:
    kwargs['data'] = data_sql(db, sql)

  c = "plot = %s" % c
  if o:
    exec(c)
    plot.save(o, **kwargs)
  else:
    print(c)


if __name__ == "__main__":
  main()
