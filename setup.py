#!/usr/bin/env python2.7
try:
    from setuptools import setup, find_packages
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
from setuptools import setup, find_packages
import pygg

setup(name="pygg",
      version=pygg.__version__,
      description="ggplot2 syntax for python.  Runs R version of ggplot2 under the covers",
      license="MIT",
      author="Eugene Wu",
      author_email="ewu@cs.columbia.edu",
      url="http://github.com/sirrice/pygg",
      packages = find_packages(),
      include_package_data = True,      
      package_dir = {'pygg' : 'pygg'},
      scripts = [
        'bin/runpygg.py'
      ],
      install_requires = [
        'click'
      ],
      keywords= "")
