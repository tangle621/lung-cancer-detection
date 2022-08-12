import datetime as dt
import unittest
import pandas as pd

from mindsdb.utilities.cache import get_cache, RedisCache, FileCache, dataframe_checksum


class TestCashe(unittest.TestCase):

    def test_redis(self):
        cache = RedisCache('predict', max_size=2)

        self.cache_test(cache)

    def test_file(self):
        cache = FileCache('predict', max_size=2)

        self.cache_test(cache)

    def cache_test(self, cache):

        # test save
        df = pd.DataFrame([
            [1, 1.2,'string', dt.datetime.now(), [1,2,3], {1:3}],
            [2, 3.2,'other', dt.datetime(2011, 12, 30), [3], {11:23, 2:3}],
        ], columns=['a', 'b', 'c', 'd', 'e', 'f'])

        # make bigger
        df = pd.concat([df]*100).reset_index()

        name = dataframe_checksum(df)

        cache.set(name, df)

        df2 = cache.get(name)

        assert dataframe_checksum(df) == dataframe_checksum(df2)
        assert list(df.columns) == list(df2.columns)

        # test delete
        cache.delete(name)

        df2 = cache.get(name)
        assert df2 is None

        # test max_size
        # load cache with size 2(max_size) + 5 (buffer)
        cache.set('first', df)
        for i in range(7):
            cache.set(str(i), df)

        # get first
        df2 = cache.get('first')
        assert df2 is None
