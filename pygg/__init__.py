from .ggplot2_functions import ggplot2_functions
from .pygg import make_ggplot2_binding

for f in ggplot2_functions:
    exec('%s = make_ggplot2_binding("%s")' % (f, f))

from .pygg import *

__all__ = ['esc', 'is_escaped', 'ggsave', 'facet_wrap', 'facet_grid'] + ggplot2_functions
