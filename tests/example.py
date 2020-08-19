from pygg import *

# Example using diamonds dataset (comes with ggplot2)
p = ggplot('diamonds', aes('carat', y='price', color='color'))
g = geom_point() + facet_wrap(None, "color")
(p+g).save("test1.pdf")

# Example using alternative ggsave syntax and facet_grid
p = ggplot('diamonds', aes('carat', y='price', color='color'))
p += geom_point() 
p += facet_grid("color~cut")
ggsave("test2.pdf", p, width=8, height=6)


# Example using data from postgresql database table.  
# Uncomment if you have the database installed
# p = ggplot('data', aes(x='epoch', y='temp', color='sensor'))
# prefix = data_sql("intel", "SELECT epoch, temp, sensor, 1 AS color FROM readingssmall")
# (p+g).save("test2.pdf", prefix=prefix)

# Example using python columnar data
data = {'x': list(range(10)), 'y': list(range(10, 20))}
p = ggplot(data, aes('x', 'y'))
ggsave("test3.pdf", p+geom_point(), quiet=False)

# Example using python row oriented data
data = [{'x': i, 'y': i*10} for i in range(10)]
p = ggplot(data, aes('x', 'y'))
ggsave("test4.pdf", p+geom_point(), quiet=False)

# Example using python row oriented data
from pandas import DataFrame
data = DataFrame(data={'x': list(range(10)), 'y': list(range(10))})
p = ggplot(data, aes('x', 'y'))
ggsave("test5.pdf", p+geom_point(), quiet=False)


# Example using themes
legend = theme_bw() + theme(**{
  "legend.background": element_blank(), #element_rect(fill=esc("#f7f7f7")),
  "legend.justification":"c(1,0)", "legend.position":"c(1,0)",
  "legend.key" : element_blank(),
  "legend.title":element_blank(),
  "text": element_text(colour = "'#333333'", size=11),
  "axis.text": element_text(colour = "'#333333'", size=11),
  "plot.background": element_blank(),
  "panel.border": element_rect(color=esc("#e0e0e0")),
  "strip.background": element_rect(fill=esc("#efefef"), color=esc("#e0e0e0")),
  "strip.text": element_text(color=esc("#333333"))
})
# libs argument lets you add install.packages statements
ggsave("test6.pdf", p+geom_point()+legend, libs=["grid"], quiet=False)




