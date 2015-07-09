from pygg import *

# Example using diamonds dataset (comes with ggplot2)
p = ggplot('diamonds', aes('carat', y='price', color='color'))
g = geom_point() + facet_wrap(None, "color")
(p+g).save("test1.pdf")


# Example using data from database table.  
p = ggplot('data', aes(x='epoch', y='temp', color='sensor'))
prefix = data_sql("intel", "SELECT epoch, temp, sensor, 1 AS color FROM readingssmall")
(p+g).save("test2.pdf", prefix=prefix)

# Example using python columnar data
p = ggplot('data', aes('x', 'y'))
prefix = data_py({'x': range(10), 'y': range(10, 20)})
ggsave("test3.pdf", p+geom_point(), prefix=prefix, quiet=False)

# Example using python row oriented data
p = ggplot('data', aes('x', 'y'))
prefix = data_py([{'x': i, 'y': i*10} for i in range(10)])
ggsave("test4.pdf", p+geom_point(), prefix=prefix, quiet=False)

# Example using python row oriented data
from pandas import DataFrame
p = ggplot('data', aes('x', 'y'))
prefix = data_dataframe(DataFrame(data={'x': range(10), 'y': range(10)}))
ggsave("test5.pdf", p+geom_point(), prefix=prefix, quiet=False)


