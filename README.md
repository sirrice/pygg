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

        # on osx
        brew install R

        # on unix e.g., ubuntu
        sudo apt-get install R

* install ggplot2 (run the following in the R shell)

        install.packages("ggplot2") 
        install.packages("RPostgreSQL")
        


Install

        pip install pyplot

Usage (command line and in Python)

        pyplot.py --help
        

Also, see `tests/example.py` for example Python usage


Questions 
===============


**Why not use [yhat's ggplot](http://ggplot.yhathq.com/)?**:  yhat's
port of ggplot is really awesome.  It runs everything natively in
python, works with numpy data structures, and renders using matplotlib.
`pyplot` exists partly due to personal preference, and partly because
the R version of ggplot2 is more mature, and its layout algorithms are
really really good.