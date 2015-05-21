pyplot
=================

ggplot2 syntax in python.  Actually wrapper around Wickham's ggplot2 in R

pyplot allows you to use ggplot2 syntax nearly verbatim in Python,
and execute the ggplot program in R.  Since this is just a wrapper
and passes all arguments to the R backend, it is almost completely
API compatible.  

For a nearly exhaustive list of supported ggplot2 functions, see `pyplot/gen_cmd.py`





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

For Python usage, see `tests/example.py` 

```python
from pyplot import *

# Example using diamonds dataset (comes with ggplot2)
p = ggplot('diamonds', aes('carat', y='price'))
g = geom_point() + facet_wrap(None, "color")
(p+g).save("test1.pdf")
```


        

Questions 
===============

Alternatives

* **[yhat's ggplot](http://ggplot.yhathq.com/)?**:  yhat's
port of ggplot is really awesome.  It runs everything natively in
python, works with numpy data structures, and renders using matplotlib.
`pyplot` exists partly due to personal preference, and partly because
the R version of ggplot2 is more mature, and its layout algorithms are
really really good.

* **[pyggplot](pypi.python.org/pypi/pyggplot/)?**: Pyggplot does not adhere
strictly to R's ggplot syntax but pythonifies it, making it harder to transpose
ggplot2 examples. Also pyggplot requires rpy2.

