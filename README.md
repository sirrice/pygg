pyplot
=================

ggplot2 syntax in python.  Actually wrapper around Wickham's ggplot2 in R

Particularly good if you have preprocessed CSVs or Postgres data to render.  Passable
support for simple data in python lists, dictionaries, and panda DataFrame objects

pyplot allows you to use ggplot2 syntax nearly verbatim in Python,
and execute the ggplot program in R.  Since this is just a wrapper
and passes all arguments to the R backend, it is almost completely
API compatible.  

For a nearly exhaustive list of supported ggplot2 functions, see [`pyplot/gen_cmd.py`](https://github.com/sirrice/pyplot/blob/master/pyplot/gen_cmds.py)





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
install.packages("RPostgreSQL")
```
        


Install

```bash
pip install pyplot
```

Command line usage 

```bash
runpyplot.py --help
runpyplot.py -c "ggplot('diamonds', aes('carat', 'price')) + geom_point()" -o test.pdf
runpyplot.py -c "ggplot('diamonds', aes('carat', 'price')) + geom_point()" -csv foo.csv

```

For Python usage, see [`tests/example.py`](https://github.com/sirrice/pyplot/blob/master/tests/example.py)

```python
from pyplot import *

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
We get around this with the `prefix` argument to `ggsave`, which prepends
an arbitrary string to the generated R program.  For example, the following
will read a CSV file into `data` before plotting `data`:

        p = ggplot(data, aes(...)) + geom_point()
        ggsave(p, "out.pdf", prefix="data=read.csv('foo.csv')")

In addition, we provide several convenience functions that generate
the appropriate R code for common python dataset formats: 

* **csv file**: if you have a CSV file already

        prefix = data_csv("file.csv")

* **python object**: if your data is a python object in columnar (`{x: [1,2], y: [3,4]}`)
  or row (`[{x:1,y:3}, {x:2,y:4}]`) format

        prefix = data_py({x: [1,2], y:[3,4]})

* **pandas dataframe**: if your data is a `pandas` data frame object

        prefix = data_dataframe(df)

* **PostgresQL**: if your data is stored in a postgres database

        prefix = data_sql('DBNAME', 'SELECT * FROM ...')

### String arguments

By default, the library directly prints a python string argument into the 
R code string.  For example the following python code to set the x axis label
would generate incorrect R code:

        # python code
        scales_x_continuous(name="special label")

        # generated R code
        scales_x_continuous(name=special label)

You'll need to explicitly wrap these types of strings (inteded as R strings)
in a layer of quotes.  For convenience, we automaticall provide wrapping
for common functions:

        # "filename.pdf" is wrapped
        ggsave(p, "filename.pdf")

        # "data.csv" is wrapped
        data_csv("data.csv")

        # string values passed to data_py are naively wrapped



Questions 
===============

Alternatives

* **[yhat's ggplot](http://ggplot.yhathq.com/)**:  yhat's
port of ggplot is really awesome.  It runs everything natively in
python, works with numpy data structures, and renders using matplotlib.
`pyplot` exists partly due to personal preference, and partly because
the R version of ggplot2 is more mature, and its layout algorithms are
really really good.

* **[pyggplot](http://pypi.python.org/pypi/pyggplot/)**: Pyggplot does not adhere
strictly to R's ggplot syntax but pythonifies it, making it harder to transpose
ggplot2 examples. Also pyggplot requires rpy2.

