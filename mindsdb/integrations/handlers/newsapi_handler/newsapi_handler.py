
from collections import OrderedDict
from typing import Any
from mindsdb_sql.parser import ast

import pandas as pd
from requests import Response
from mindsdb.api.mysql.mysql_proxy.libs.constants.response_type import RESPONSE_TYPE
from mindsdb.integrations.libs.api_handler import APIHandler, APITable, FuncParser
from mindsdb.integrations.libs.base import DatabaseHandler
from mindsdb.integrations.libs.response import HandlerResponse, HandlerStatusResponse
from mindsdb.integrations.utilities.sql_utils import extract_comparison_conditions
from newsapi import NewsApiClient
from mindsdb_sql.parser.ast.base import ASTNode

from mindsdb.microservices_grpc.db.common_pb2 import StatusResponse
import urllib
from mindsdb.utilities.config import Config
import os
from mindsdb.integrations.libs.const import HANDLER_CONNECTION_ARG_TYPE as ARG_TYPE
from mindsdb_sql import parse_sql



class NewsAPIArticleTable(APITable):

    def __init__(self, handler):
        super().__init__(handler)
    
    def select(self, query: ast.Select) -> pd.DataFrame:
        conditions = extract_comparison_conditions(query.where)

        params = {}
        
        
        for op, arg1, arg2 in conditions:

            if arg1 == 'query':
                params['q'] = urllib.parse.quote_plus(arg2)
            elif arg1 == 'sources':
                if len(arg2.split(",")) > 20:
                    raise ValueError("The number of items it sources should be 20 or less")
                else:
                    params[arg1] = arg2
            elif arg1 == 'publishedAt':
                if op == 'Gt' or op == 'GtE':
                    params['from'] = arg2
                if op == 'Lt' or op == 'LtE':
                    params['to'] = arg2
                elif op == 'Eq':
                    params['from'] = arg2
                    params['to'] = arg2
            else:
                params[arg1] = arg2
        
        if query.limit:
            if query.limit.value > 100:
                params['page'], params['page_size'] = divmod(query.limit.value, 100)
                if params['page_size']  == 0:
                    params['page_size'] = 100
                print("Page Size : ", params['page'])
            else: 
                params['page_size'] = query.limit.value
                params['page'] = 1
        else:
            params['page_size'] = 100
            params['page'] = 1
        
        if query.order_by:
            print("Order by : ", query.order_by[0])
            if len(query.order_by) == 1:
                if (str(query.order_by[0])  not in ['relevancy', 'publishedAt']):
                    raise NotImplementedError("Not supported ordering by this field")
                params['sort_by'] = str(query.order_by[0])
            else: 
                raise ValueError("Multiple order by condition is not supported by the API")

        result = self.handler.call_application_api(params=params)

        selected_columns = []
        for target in query.targets:
            if isinstance(target, ast.Star):
                selected_columns = self.get_columns()
                break
            elif isinstance(target, ast.Identifier):
                selected_columns.append(target.parts[-1])
            else:
                raise ValueError(f"Unknown query target {type(target)}")

        return result[selected_columns]
    
    def get_columns(self) -> list:
        return [
            'author',
            'title',
            'description',
            'url',
            'urlToImage',
            'publishedAt',
            'content',
            'source_id',
            'source_name',
            'query',
            'searchIn',
            'domains',
            'excludedDomains',
        ]

class NewsAPIHandler(APIHandler):

    def __init__(self, name: str, **kwargs):
        super().__init__(name)
        print(f"TEST ---- {name}")
        self.api = None
        self._tables = {}

        args = kwargs.get('connection_data', {})
        self.connection_args = {}
        handler_config = Config().get('newsAPI_handler', {})
        
        for k in ['api_key']:
            if k in args:
                self.connection_args[k] = args[k]
            elif f'NEWSAPI_{k.upper()}' in os.environ:
                self.connection_args[k] = os.environ[f'NEWSAPI_{k.upper()}']
            elif k in handler_config:
                self.connection_args[k] = handler_config[k]

        self.is_connected = False
        self.api = self.create_connection()

        article = NewsAPIArticleTable(self)
        self._register_table('article', article)

    def __del__(self):
        if self.is_connected is True:
            self.disconnect()

    def disconnect(self):
        """
        Close any existing connections.
        """

        if self.is_connected is False:
            return

        self.is_connected = False
        return self.is_connected
    
    def create_connection(self):
        return NewsApiClient(**self.connection_args)

    
    def _register_table(self, table_name: str, table_class: Any):
        self._tables[table_name] = table_class

    def get_table(self, table_name: str):
        return self._tables.get(table_name)

    def connect(self) -> HandlerStatusResponse:
        if self.is_connected is True:
            return self.api

        self.api = self.create_connection()

        self.is_connected = True
        return HandlerStatusResponse(success=True)
    
    def check_connection(self) -> HandlerStatusResponse:
        response = HandlerStatusResponse(False)

        try:
            self.connect()
            
            self.api.get_top_headlines()
            response.success = True

        except Exception as e:
            response.error_message = e.message

        return response
    
    def native_query(self, query: Any):

        ast = parse_sql(query, dialect="mindsdb")
        table = self.get_table("article")
        data = table.select(ast)
        print(data)
        return HandlerResponse(
            RESPONSE_TYPE.TABLE,
            data_frame=data
        )
    
    def call_application_api(self, method_name:str = None, params:dict = None) -> pd.DataFrame:
        # This will implement api base on the native query
        # By processing native query to convert it to api callable parameters
        if self.is_connected is False:
            self.connect()
            
        print("Pages : ", params)
        pages = params['page']
        data = []
        print("Pages : ", params)
        
        for page in range(1, pages+1):
            params['page'] = page
            result = self.api.get_everything(**params)
            articles = result['articles']
            for article in articles:
                print("Result : ", articles)
                article['source_id'] = article['source']['id']
                article['source_name'] = article['source']['name']
                del article['source']
                article['query'] = params.get('q')
                article['searchIn'] = params.get('searchIn')
                article['domains'] = params.get('domains')
                article['excludedDomains'] = params.get('exclude_domains')
                data.append(article)
        
        return pd.DataFrame(data=data)
        
connection_args = OrderedDict(
    api_key={
        'type': ARG_TYPE.STR,
        'description': 'The API key for the Airtable API.'
    }
)

connection_args_example = OrderedDict(
    api_key='knlsndlknslk'
)