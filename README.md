pygg
=================

ggplot2 syntax in python.  Actually wrapper around Wickham's ggplot2 in R

Particularly good if you have preprocessed CSVs or Postgres data to render.  Passable
support for simple data in python lists, dictionaries, and panda DataFrame objects

pygg allows you to use ggplot2 syntax nearly verbatim in Python,
and execute the ggplot program in R.  Since this is just a wrapper
and passes all arguments to the R backend, it is almost completely
API compatible.  

For a nearly exhaustive list of supported ggplot2 functions, see [`pygg/gen_cmd.py`](https://github.com/sirrice/pygg/blob/master/pygg/gen_cmds.py)





Setup and Usage
===================


Setup

* install R

```bash
# on osx
brew install R

# on unix e.g., ubuntu
sudo apt-get install R
```

* install R packages (run the following in the R shell)

```r
install.packages("ggplot2")
install.packages("RPostgreSQL") # optional
```



Install

```bash
pip install pygg
```

Command line usage

```bash
runpygg.py --help
runpygg.py -c "ggplot('diamonds', aes('carat', 'price')) + geom_point()" -o test.pdf
runpygg.py -c "ggplot('diamonds', aes('carat', 'price')) + geom_point()" -csv foo.csv

```

For Python usage, see [`tests/example.py`](https://github.com/sirrice/pygg/blob/master/tests/example.py)

```python
from pygg import *

# Example using diamonds dataset (comes with ggplot2)
p = ggplot('diamonds', aes('carat', y='price'))
g = geom_point() + facet_wrap(None, "color")
ggsave("test1.pdf", p+g)
```


Quirks to be aware of
=====================

The library performs a simple syntactic translation from python
ggplot objects to R code.  Because of this, there are some quirks
regarding datasets and how we deal with strings.

### Datasets

In R, ggplot directly references the data frame object present in the runtime
(e.g., `ggplot(<datasetname>, aes(...))`.   However, the python
objects being plotted are not directly available in the R runtime.  
We get around by providing a data object `data` argument to `ggsave`, which
converts the data object to a suitable CSV file, writes it to a temp file,
and loads it into the `data` variable in R for use with the ggplot2 functions

For example:

        df = pandas.DataFrame(...)
        p = ggplot(data, aes(...)) + geom_point()
        ggsave(p, "out.pdf", data=df)

In addition, we provide several convenience functions that generate
the appropriate R code for common python dataset formats:

* **csv file**: if you have a CSV file already, provide the filename to data

```
        p = ggplot(data, aes(...)) + geom_point()
        ggsave(p, "out.pdf", data="file.csv")
```

* **python object**: if your data is a python object in columnar (`{x: [1,2], y: [3,4]}`)
  or row (`[{x:1,y:3}, {x:2,y:4}]`) format

```
        p = ggplot(data, aes(...)) + geom_point()
        ggsave(p, "out.pdf", data={'x': [1,2], 'y': [3,4]})
```

* **pandas dataframe**: if your data is a `pandas` data frame object already
  you can just provide the dataframe df directly to data

```
        p = ggplot(data, aes(...)) + geom_point()
        ggsave(p, "out.pdf", data=df)
```

* **PostgresQL**: if your data is stored in a postgres database

```
        p = ggplot(data, aes(...)) + geom_point()
        ggsave(p, "out.pdf", data=data_sql('DBNAME', 'SELECT * FROM ...')
```

* **existing R datasets**: can you refer to any dataframe object

```
        p = ggplot('diamonds', aes(...)) + geom_point()
        ggsave(p, "out.pdf", data=None)
```


### String arguments

By default, the library directly prints a python string argument into the
R code string.  For example the following python code to set the x axis label
would generate incorrect R code:

        # incorrect python code
        scales_x_continuous(name="special label")

        # incorrect generated R code
        scales_x_continuous(name=special label)

        # correct python code
        scales_x_continuous(name="'special label'")

        # correct generated R code
        scales_x_continuous(name='special label')

You'll need to explicitly wrap these types of strings (inteded as R strings)
in a layer of quotes.  For convenience, we automatically provide wrapping
for common functions:

        # "filename.pdf" is wrapped
        ggsave(p, "filename.pdf")

        # string values passed to data_py are naively wrapped



Questions
===============

Alternatives

* **[yhat's ggplot](http://ggplot.yhathq.com/)**:  yhat's
port of ggplot is really awesome.  It runs everything natively in
python, works with numpy data structures, and renders using matplotlib.
`pygg` exists partly due to personal preference, and partly because
the R version of ggplot2 is more mature, and its layout algorithms are
really really good.

* **[pyggplot](http://pypi.python.org/pypi/pyggplot/)**: Pyggplot does not adhere
strictly to R's ggplot syntax but pythonifies it, making it harder to transpose
ggplot2 examples. Also pyggplot requires rpy2.
