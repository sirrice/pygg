pygg
=================

ggplot2 syntax in python.  Actually wrapper around Wickham's ggplot2 in R

Particularly good if you have preprocessed CSVs or Postgres data to render.  Passable
support for simple data in python lists, dictionaries, and panda DataFrame objects

pygg allows you to use ggplot2 syntax nearly verbatim in Python,
and execute the ggplot program in R.  Since this is just a wrapper
and passes all arguments to the R backend, it is almost completely
API compatible.  

For a nearly exhaustive list of supported ggplot2 functions, see [`bin/make_ggplot2_functions.R`](https://github.com/sirrice/pygg/blob/master/bin/make_ggplot2_functions.R).





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
install.packages("RPostgreSQL")   # optional
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
ggsave("test1.pdf", p+g, data=None)
```


Details, Utils, and Quirks
=====================

The library performs a simple syntactic translation from python
ggplot objects to R code.  Because of this, there are some quirks
regarding datasets and how we deal with strings.

### Datasets

In R, ggplot directly references the data frame object present in the runtime
(e.g., `ggplot(<datasetname>, aes(...))`.   However, the python
objects being plotted are not directly available in the R runtime.  
`pygg` provides two ways of loading datasets from Python into R.

The primary way is to explicitly pass the data object  to `ggsave` using its `data` keyword argument.
`ggsave` then converts the data object to a suitable CSV file, writes it to a temp file,
and loads it into the `data` variable in R for use with the ggplot2 functions

For example (notice that the string `"data"` is passed to `ggplot()`):

        df = pandas.DataFrame(...)
        p = ggplot("data", aes(...)) + geom_point()
        ggsave("out.pdf", p, data=df)

In addition, we provide several convenience functions that generate
the appropriate R code for common python dataset formats:

* **csv file**: if you have a CSV file already, provide the filename to data

```
        p = ggplot("data", aes(...)) + geom_point()
        ggsave("out.pdf", p, data="file.csv")

        # or more explicitly, pass a wrapped object that represents the csv file:

        ggsave("out.pdf", p, data=data_py("file.csv"))

```

* **python object**: if your data is a python object in columnar (`{x: [1,2], y: [3,4]}`)
  or row (`[{x:1,y:3}, {x:2,y:4}]`) format

```
        p = ggplot("data", aes(...)) + geom_point()
        ggsave("out.pdf", p, data={'x': [1,2], 'y': [3,4]})
```

* **pandas dataframe**: if your data is a `pandas` data frame object already
  you can just provide the dataframe df directly to data

```
        p = ggplot("data", aes(...)) + geom_point()
        ggsave("out.pdf", p, data=df)
```

* **PostgresQL**: if your data is stored in a postgres database

```
        p = ggplot("data", aes(...)) + geom_point()
        ggsave("out.pdf", p, data=data_sql('DBNAME', 'SELECT * FROM ...')
```

* **existing R datasets**: can you refer to any R dataframe object using the
  first argument to `ggplot()`

```
        p = ggplot('diamonds', aes(...)) + geom_point()
        ggsave("out.pdf", p, data=None)
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

        # less convenient but more explicit alternative syntax
        scales_x_continuous(name=pygg.esc('special label'))


You'll need to explicitly wrap these types of strings (intended as R strings)
in a layer of quotes.  For convenience, we automatically provide wrapping
for common functions:

        # "filename.pdf" is wrapped
        ggsave("filename.pdf", p)

### Convenience Functions


##### Passing data to `ggplot()` directly

It feels silly to pass a dummy `"data"` string to `ggplot()` and then pass the object to
`ggsave`.  We have extended the `ggplot()` call so it recognizes _non string python data objects_
and uses the data object by default during the `ggsave` call:

        df = pandas.DataFrame(...)
        p = ggplot(df, aes(...)) + geom_point()
        ggsave("out.pdf", p)

        p = ggplot(dict(x=[0,1], y=[3,4]), aes(x='x', y='y')) + geom_point()
        ggsave("out.pdf", p)

Note that unlike `ggsave`, it is not smart enough to distinguish string arguments that
are R variable names and file names.  Thus, the following will likely lead to an error because it
assumes the R variable `data.csv` exists in the environment when in reality it's the name of a csv file 
to be loaded:

        p = ggplot("data.csv", aes(x='x', y='y')) + geom_point()
        ggsave("out.pdf", p)

Simply wrap the filename with a `data_py()` call:

        p = ggplot(data_py("data.csv"), aes(x='x', y='y')) + geom_point()
        ggsave("out.pdf", p)


##### Axis Labels

`axis_labels()` is a shortcut for setting the x and y axis titles and scale types.
The following names the x axis `"Dataset Size (MB)"`and sets it to log scale,
names the y axis `"Latency (sec)"`and is by default continuous scale, and
sets the breaks for the x axis to `[0, 10, 100, 5000]`:

        p = ggplot(...)
        p += axis_labels("Dataset Size (MB)", 
                        "Latency (sec)", 
                        "log10",  
                        xkwargs=dict(breaks=[0, 10, 100, 5000]))



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

* **[plotnine](https://github.com/has2k1/plotnine)**: another implementation of ggplot2 in Python
