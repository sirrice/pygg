import unittest
import pandas
import tempfile
import os.path

from io import StringIO

import pygg
import pandas.util.testing as pdt


class IPythonTests(unittest.TestCase):
    """Test IPython integration"""
    def setUp(self):
        """Setup IPython tests, skipping if IPython isn't present"""
        try:
            import IPython
        except ImportError:
            self.skipTest("Couldn't import IPython")

    def testSizing(self):
        """Test that computing R sizes works properly"""
        self.assertAlmostEqual(pygg.size_r_img_inches(width=800, height=800),
                               (pygg.R_IMAGE_SIZE, pygg.R_IMAGE_SIZE))
        self.assertAlmostEqual(pygg.size_r_img_inches(width=400, height=400),
                               (pygg.R_IMAGE_SIZE, pygg.R_IMAGE_SIZE))
        self.assertAlmostEqual(pygg.size_r_img_inches(width=800, height=400),
                               (pygg.R_IMAGE_SIZE, pygg.R_IMAGE_SIZE / 2.))
        self.assertAlmostEqual(pygg.size_r_img_inches(width=400, height=800),
                               (pygg.R_IMAGE_SIZE, pygg.R_IMAGE_SIZE * 2.))

    def testIPython(self):
        """Test that gg_ipython returns a IPython formatted Image"""
        p = pygg.ggplot('diamonds', pygg.aes(x='carat', y='price'))
        p += pygg.geom_point()
        img = pygg.gg_ipython(p, data=None)
        self.assertIsNotNone(img.data)
        self.assertEqual(img.format, "jpeg")
        self.assertEqual(img.width, pygg.IPYTHON_IMAGE_SIZE)
        self.assertEqual(img.height, pygg.IPYTHON_IMAGE_SIZE)

        img = pygg.gg_ipython(p, data=None, width=600, height=400)
        self.assertEqual(img.width, 600)
        self.assertEqual(img.height, 400)

        img = pygg.gg_ipython(p, data=None, width=600)
        self.assertEqual(img.width, 600)
        self.assertEqual(img.height, 600)

class TestUnits(unittest.TestCase):
    """Basic unit testing for pygg"""
    def testIsDataFrame(self):
        """Test that is_pandas_df works"""
        df = pandas.read_csv(StringIO(IRIS_DATA_CSV))
        self.assertTrue(pygg.is_pandas_df(df))
        self.assertTrue(pygg.is_pandas_df(df[0:1]))
        self.assertFalse(pygg.is_pandas_df(df.SepalLength))
        self.assertFalse(pygg.is_pandas_df(1))
        self.assertFalse(pygg.is_pandas_df(1.0))
        self.assertFalse(pygg.is_pandas_df([]))
        self.assertFalse(pygg.is_pandas_df([1]))
        self.assertFalse(pygg.is_pandas_df({}))
        self.assertFalse(pygg.is_pandas_df({'a': 1}))

    def check_me(self, stmt, expectation):
        self.assertEquals(stmt.r.replace(" ", ""), expectation)

    def testDataPyWithDF(self):
        df = pandas.DataFrame({'a': [1, 2], 'b': [3, 4]})
        datao = pygg.data_py(df)
        dffile, expr = datao.fname, str(datao)
        iodf = pandas.read_csv(dffile)
        pdt.assert_frame_equal(df, iodf)

    def testDataPyLoadStmtPlain(self):
        df = pandas.DataFrame({'a': [1, 2], 'b': [3, 4]})
        datao = pygg.data_py(df)
        dffile, expr = datao.fname, str(datao)
        self.assertEquals(expr,
                          'data = read.csv("{}",sep=",")'.format(dffile))

    def testDataPyLoadStmtArgs(self):
        df = pandas.DataFrame({'a': [1, 2], 'b': [3, 4]})
        datao = pygg.data_py(df, 1, kwd=2)
        dffile, expr = datao.fname, str(datao)
        expected = 'data = read.csv("{}",1,kwd=2,sep=",")'.format(dffile)
        self.assertEquals(expr, expected)

    def testDataPyWithDict(self):
        src = {'a': [1, 2], 'b': [3, 4]}
        datao = pygg.data_py(src)
        dffile, expr = datao.fname, str(datao)
        iodf = pandas.read_csv(dffile)
        pdt.assert_frame_equal(pandas.DataFrame(src), iodf)

    def testDataPyWithListOfDict(self):
        src = [{'a': 1, 'b': 3}, {'a': 2, 'b': 4}]
        datao = pygg.data_py(src)
        dffile, expr = datao.fname, str(datao)
        iodf = pandas.read_csv(dffile)
        pdt.assert_frame_equal(pandas.DataFrame({'a': [1, 2], 'b': [3, 4]}),
                               pandas.read_csv(dffile))

    def testDataPyWithString(self):
        src = "my.csv"
        datao = pygg.data_py(src)
        dffile, expr = datao.fname, str(datao)
        self.assertEquals(dffile, src)
        self.assertEquals(expr, 'data = read.csv("{}",sep=",")'.format(src))

    def testGGStatementToR(self):
        """Test that GGStatement converts to R properly"""
        self.check_me(pygg.geom_point(), "geom_point()")
        self.check_me(pygg.geom_point(size=1.0), "geom_point(size=1.0)")
        self.check_me(pygg.geom_point(size=1.0, alpha=2.0),
                      "geom_point(alpha=2.0,size=1.0)")

    def testGGStatementsToR(self):
        """Test that GGStatement converts to R properly"""
        self.check_me(pygg.geom_point(), "geom_point()")
        self.check_me(pygg.geom_bar(), "geom_bar()")
        self.check_me(pygg.geom_point() + pygg.geom_bar(),
                      "geom_point()+geom_bar()")
        self.check_me(pygg.geom_bar() + pygg.geom_point(),
                      "geom_bar()+geom_point()")

    def testPython2RTypes(self):
        """Test GGStatement converts many python types properly"""
        self.check_me(pygg.geom_point(a=1), "geom_point(a=1)")
        self.check_me(pygg.geom_point(a=None), "geom_point(a=NA)")
        self.check_me(pygg.geom_point(a=1.0), "geom_point(a=1.0)")
        self.check_me(pygg.geom_point(a=1e-2), "geom_point(a=0.01)")
        self.check_me(pygg.geom_point(a="foo"), 'geom_point(a=foo)')
        self.check_me(pygg.geom_point(a=pygg.esc("foo")), 'geom_point(a="foo")')
        self.check_me(pygg.geom_point(a=True), 'geom_point(a=TRUE)')
        self.check_me(pygg.geom_point(a=False), 'geom_point(a=FALSE)')
        self.check_me(pygg.geom_point(a=[1, 2]), 'geom_point(a=c(1,2))')
        self.check_me(pygg.geom_point(a={'list1': 1, 'list2': 2}),
                      'geom_point(a=list(list1=1,list2=2))')
        self.check_me(pygg.geom_point(1, a=2.0, b=[3, 4],
                                      c={'list1': pygg.esc('s1'), 'list2': 2}),
                      'geom_point(1,a=2.0,b=c(3,4),c=list(list1="s1",list2=2))')

    def testPython2RStringEsc(self):
        """Test GGStatement escapes strings properly"""
        self.check_me(pygg.geom_point(a="b"), 'geom_point(a=b)')
        self.check_me(pygg.geom_point(a='b'), 'geom_point(a=b)')
        self.check_me(pygg.geom_point(a="'b'"), 'geom_point(a=\'b\')')
        self.check_me(pygg.geom_point(a='"b"'), 'geom_point(a="b")')
        self.check_me(pygg.geom_point(a={'k': pygg.esc("v")}),
                                      'geom_point(a=list(k="v"))')
        self.check_me(pygg.geom_point(a=[pygg.esc("a"), pygg.esc("b")]),
                                      'geom_point(a=c("a","b"))')


class TestIntegration(unittest.TestCase):
    """Basic unit testing for pygg"""
    def testE2E(self):
        """Test end-to-end creation of figures with outputs to pdf and png"""
        p = pygg.ggplot('diamonds', pygg.aes(x='carat', y='price', color='clarity'))
        p += pygg.geom_point(alpha=0.5, size = .75)
        p += pygg.scale_x_log10()
        p += pygg.theme_bw()

        self.check_ggsave(p, None, ext=".pdf")
        self.check_ggsave(p, None, ext=".png")
        self.check_ggsave(p, None, ext=".jpg")

    def testPandasDF(self):
        data = pandas.read_csv(StringIO(IRIS_DATA_CSV))
        self.assertIsInstance(data, pandas.DataFrame)
        p = pygg.ggplot('data',
                        pygg.aes(x='SepalLength', y='PetalLength', color='Name'))
        p += pygg.geom_point()
        p += pygg.geom_smooth()
        p += pygg.ggtitle(pygg.esc('Test title'))
        self.check_ggsave(p, data)

    def testPandasDFggplot(self):
        data = pandas.read_csv(StringIO(IRIS_DATA_CSV))
        self.assertIsInstance(data, pandas.DataFrame)
        p = pygg.ggplot(data,
                        pygg.aes(x='SepalLength', y='PetalLength', color='Name'))
        p += pygg.geom_point()
        p += pygg.geom_smooth()
        p += pygg.ggtitle(pygg.esc('Test title'))
        self.check_ggsave(p)

    def testBasicDataggplot(self):
        data = dict(x=range(10), y=range(10))
        p = pygg.ggplot(data, pygg.aes(x='x', y='y'))
        p += pygg.geom_point()
        p += pygg.geom_smooth()
        p += pygg.ggtitle(pygg.esc('Test title'))
        self.check_ggsave(p)

    def testBasicDataggplot(self):
        data = [dict(x=x, y=y) for x, y in zip(range(10), range(10))]
        p = pygg.ggplot(data, pygg.aes(x='x', y='y'))
        p += pygg.geom_point()
        p += pygg.geom_smooth()
        p += pygg.ggtitle(pygg.esc('Test title'))
        self.check_ggsave(p)

    def testLimits(self):
        p = pygg.ggplot('diamonds', pygg.aes(x='carat', y='price', color='clarity'))
        p += pygg.geom_point(alpha=0.5, size = .75)
        p += pygg.scale_x_log10(limits=[1, 2])
        self.check_ggsave(p, None)

    def testFacets1(self):
        p = pygg.ggplot('diamonds', pygg.aes(x='carat', y='price'))
        p += pygg.geom_point()
        p += pygg.facet_grid("clarity~.")
        self.check_ggsave(p, None)

    def testFacets2(self):
        p = pygg.ggplot('diamonds', pygg.aes(x='carat', y='price'))
        p += pygg.geom_point()
        p += pygg.facet_wrap("~clarity")
        self.check_ggsave(p, None)

    def testLibs(self):
        p = pygg.ggplot('diamonds', pygg.aes(x='carat', y='price'))
        p += pygg.geom_point()
        tmpfile = tempfile.NamedTemporaryFile(suffix='.pdf').name
        pygg.ggsave(tmpfile, p, data=None, libs=['grid'], quiet=True)
        self.assertTrue(os.path.exists(tmpfile))
        self.assertTrue(os.path.getsize(tmpfile) > 0)

    def testNativeRDataset(self):
        p = pygg.ggplot('diamonds', pygg.aes(x='carat', y='carat')) + pygg.geom_point()
        self.check_ggsave(p, None)

    def check_ggsave(self, plotobj, data=None, ext='.pdf'):
        tmpfile = tempfile.NamedTemporaryFile(suffix=ext).name
        pygg.ggsave(tmpfile, plotobj, data=data, quiet=True)
        self.assertTrue(os.path.exists(tmpfile))
        self.assertTrue(os.path.getsize(tmpfile) > 0)

    def testBadGGPlotFails(self):
        p = pygg.ggplot('diamonds', pygg.aes(x='MISSING')) + pygg.geom_point()
        with self.assertRaises(ValueError):
            tmpfile = tempfile.NamedTemporaryFile(suffix=".png").name
            pygg.ggsave(tmpfile, p, data=None, quiet=True)


IRIS_DATA_CSV = u"""SepalLength,SepalWidth,PetalLength,PetalWidth,Name
5.1,3.5,1.4,0.2,Iris-setosa
4.9,3.0,1.4,0.2,Iris-setosa
4.7,3.2,1.3,0.2,Iris-setosa
4.6,3.1,1.5,0.2,Iris-setosa
5.0,3.6,1.4,0.2,Iris-setosa
5.4,3.9,1.7,0.4,Iris-setosa
4.6,3.4,1.4,0.3,Iris-setosa
5.0,3.4,1.5,0.2,Iris-setosa
4.4,2.9,1.4,0.2,Iris-setosa
4.9,3.1,1.5,0.1,Iris-setosa
5.4,3.7,1.5,0.2,Iris-setosa
4.8,3.4,1.6,0.2,Iris-setosa
4.8,3.0,1.4,0.1,Iris-setosa
4.3,3.0,1.1,0.1,Iris-setosa
5.8,4.0,1.2,0.2,Iris-setosa
5.7,4.4,1.5,0.4,Iris-setosa
5.4,3.9,1.3,0.4,Iris-setosa
5.1,3.5,1.4,0.3,Iris-setosa
5.7,3.8,1.7,0.3,Iris-setosa
5.1,3.8,1.5,0.3,Iris-setosa
5.4,3.4,1.7,0.2,Iris-setosa
5.1,3.7,1.5,0.4,Iris-setosa
4.6,3.6,1.0,0.2,Iris-setosa
5.1,3.3,1.7,0.5,Iris-setosa
4.8,3.4,1.9,0.2,Iris-setosa
5.0,3.0,1.6,0.2,Iris-setosa
5.0,3.4,1.6,0.4,Iris-setosa
5.2,3.5,1.5,0.2,Iris-setosa
5.2,3.4,1.4,0.2,Iris-setosa
4.7,3.2,1.6,0.2,Iris-setosa
4.8,3.1,1.6,0.2,Iris-setosa
5.4,3.4,1.5,0.4,Iris-setosa
5.2,4.1,1.5,0.1,Iris-setosa
5.5,4.2,1.4,0.2,Iris-setosa
4.9,3.1,1.5,0.1,Iris-setosa
5.0,3.2,1.2,0.2,Iris-setosa
5.5,3.5,1.3,0.2,Iris-setosa
4.9,3.1,1.5,0.1,Iris-setosa
4.4,3.0,1.3,0.2,Iris-setosa
5.1,3.4,1.5,0.2,Iris-setosa
5.0,3.5,1.3,0.3,Iris-setosa
4.5,2.3,1.3,0.3,Iris-setosa
4.4,3.2,1.3,0.2,Iris-setosa
5.0,3.5,1.6,0.6,Iris-setosa
5.1,3.8,1.9,0.4,Iris-setosa
4.8,3.0,1.4,0.3,Iris-setosa
5.1,3.8,1.6,0.2,Iris-setosa
4.6,3.2,1.4,0.2,Iris-setosa
5.3,3.7,1.5,0.2,Iris-setosa
5.0,3.3,1.4,0.2,Iris-setosa
7.0,3.2,4.7,1.4,Iris-versicolor
6.4,3.2,4.5,1.5,Iris-versicolor
6.9,3.1,4.9,1.5,Iris-versicolor
5.5,2.3,4.0,1.3,Iris-versicolor
6.5,2.8,4.6,1.5,Iris-versicolor
5.7,2.8,4.5,1.3,Iris-versicolor
6.3,3.3,4.7,1.6,Iris-versicolor
4.9,2.4,3.3,1.0,Iris-versicolor
6.6,2.9,4.6,1.3,Iris-versicolor
5.2,2.7,3.9,1.4,Iris-versicolor
5.0,2.0,3.5,1.0,Iris-versicolor
5.9,3.0,4.2,1.5,Iris-versicolor
6.0,2.2,4.0,1.0,Iris-versicolor
6.1,2.9,4.7,1.4,Iris-versicolor
5.6,2.9,3.6,1.3,Iris-versicolor
6.7,3.1,4.4,1.4,Iris-versicolor
5.6,3.0,4.5,1.5,Iris-versicolor
5.8,2.7,4.1,1.0,Iris-versicolor
6.2,2.2,4.5,1.5,Iris-versicolor
5.6,2.5,3.9,1.1,Iris-versicolor
5.9,3.2,4.8,1.8,Iris-versicolor
6.1,2.8,4.0,1.3,Iris-versicolor
6.3,2.5,4.9,1.5,Iris-versicolor
6.1,2.8,4.7,1.2,Iris-versicolor
6.4,2.9,4.3,1.3,Iris-versicolor
6.6,3.0,4.4,1.4,Iris-versicolor
6.8,2.8,4.8,1.4,Iris-versicolor
6.7,3.0,5.0,1.7,Iris-versicolor
6.0,2.9,4.5,1.5,Iris-versicolor
5.7,2.6,3.5,1.0,Iris-versicolor
5.5,2.4,3.8,1.1,Iris-versicolor
5.5,2.4,3.7,1.0,Iris-versicolor
5.8,2.7,3.9,1.2,Iris-versicolor
6.0,2.7,5.1,1.6,Iris-versicolor
5.4,3.0,4.5,1.5,Iris-versicolor
6.0,3.4,4.5,1.6,Iris-versicolor
6.7,3.1,4.7,1.5,Iris-versicolor
6.3,2.3,4.4,1.3,Iris-versicolor
5.6,3.0,4.1,1.3,Iris-versicolor
5.5,2.5,4.0,1.3,Iris-versicolor
5.5,2.6,4.4,1.2,Iris-versicolor
6.1,3.0,4.6,1.4,Iris-versicolor
5.8,2.6,4.0,1.2,Iris-versicolor
5.0,2.3,3.3,1.0,Iris-versicolor
5.6,2.7,4.2,1.3,Iris-versicolor
5.7,3.0,4.2,1.2,Iris-versicolor
5.7,2.9,4.2,1.3,Iris-versicolor
6.2,2.9,4.3,1.3,Iris-versicolor
5.1,2.5,3.0,1.1,Iris-versicolor
5.7,2.8,4.1,1.3,Iris-versicolor
6.3,3.3,6.0,2.5,Iris-virginica
5.8,2.7,5.1,1.9,Iris-virginica
7.1,3.0,5.9,2.1,Iris-virginica
6.3,2.9,5.6,1.8,Iris-virginica
6.5,3.0,5.8,2.2,Iris-virginica
7.6,3.0,6.6,2.1,Iris-virginica
4.9,2.5,4.5,1.7,Iris-virginica
7.3,2.9,6.3,1.8,Iris-virginica
6.7,2.5,5.8,1.8,Iris-virginica
7.2,3.6,6.1,2.5,Iris-virginica
6.5,3.2,5.1,2.0,Iris-virginica
6.4,2.7,5.3,1.9,Iris-virginica
6.8,3.0,5.5,2.1,Iris-virginica
5.7,2.5,5.0,2.0,Iris-virginica
5.8,2.8,5.1,2.4,Iris-virginica
6.4,3.2,5.3,2.3,Iris-virginica
6.5,3.0,5.5,1.8,Iris-virginica
7.7,3.8,6.7,2.2,Iris-virginica
7.7,2.6,6.9,2.3,Iris-virginica
6.0,2.2,5.0,1.5,Iris-virginica
6.9,3.2,5.7,2.3,Iris-virginica
5.6,2.8,4.9,2.0,Iris-virginica
7.7,2.8,6.7,2.0,Iris-virginica
6.3,2.7,4.9,1.8,Iris-virginica
6.7,3.3,5.7,2.1,Iris-virginica
7.2,3.2,6.0,1.8,Iris-virginica
6.2,2.8,4.8,1.8,Iris-virginica
6.1,3.0,4.9,1.8,Iris-virginica
6.4,2.8,5.6,2.1,Iris-virginica
7.2,3.0,5.8,1.6,Iris-virginica
7.4,2.8,6.1,1.9,Iris-virginica
7.9,3.8,6.4,2.0,Iris-virginica
6.4,2.8,5.6,2.2,Iris-virginica
6.3,2.8,5.1,1.5,Iris-virginica
6.1,2.6,5.6,1.4,Iris-virginica
7.7,3.0,6.1,2.3,Iris-virginica
6.3,3.4,5.6,2.4,Iris-virginica
6.4,3.1,5.5,1.8,Iris-virginica
6.0,3.0,4.8,1.8,Iris-virginica
6.9,3.1,5.4,2.1,Iris-virginica
6.7,3.1,5.6,2.4,Iris-virginica
6.9,3.1,5.1,2.3,Iris-virginica
5.8,2.7,5.1,1.9,Iris-virginica
6.8,3.2,5.9,2.3,Iris-virginica
6.7,3.3,5.7,2.5,Iris-virginica
6.7,3.0,5.2,2.3,Iris-virginica
6.3,2.5,5.0,1.9,Iris-virginica
6.5,3.0,5.2,2.0,Iris-virginica
6.2,3.4,5.4,2.3,Iris-virginica
5.9,3.0,5.1,1.8,Iris-virginica
"""

if __name__ == '__main__':
    unittest.main()
