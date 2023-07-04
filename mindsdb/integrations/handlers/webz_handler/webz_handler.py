import os
import pandas as pd
from typing import Dict, Any

from dotty_dict import dotty
import webzio

from mindsdb.integrations.handlers.webz_handler.webz_tables import WebzPostsTable, WebzReviewsTable
from mindsdb.integrations.libs.api_handler import APIHandler
from mindsdb.integrations.libs.response import (
    HandlerStatusResponse as StatusResponse,
    HandlerResponse as Response,
)
from mindsdb.utilities import log
from mindsdb.utilities.config import Config
from mindsdb_sql import parse_sql



class WebzHandler(APIHandler):
    """A class for handling connections and interactions with the Webz API.

    """

    AVAILABLE_CONNECTION_ARGUMENTS = ['token']

    def __init__(self, name: str = None, **kwargs):
        """Registers all tables and prepares the handler for an API connection.

        Args:
            name: (str): The handler name to use
        """
        super().__init__(name)

        args = kwargs.get('connection_data', {})
        self.connection_args = self._read_connection_args(name, **args)

        self.client = None
        self.is_connected = False
        self.max_page_size = 100

        self._register_table('posts', WebzPostsTable(self))
        self._register_table('reviews', WebzReviewsTable(self))

    def _read_connection_args(self, name: str = None, **kwargs) -> Dict[str, Any]:
        """ Read the connection arguments by following the order of precedence below:

            1. PARAMETERS object
            2. Environment Variables
            3. MindsDB Config File

        """
        filtered_args = {}
        handler_config = Config().get(f'{name.lower()}_handler', {})
        for k in type(self).AVAILABLE_CONNECTION_ARGUMENTS:
            if k in kwargs:
                filtered_args[k] = kwargs[k]
            elif f'{name.upper()}_{k.upper()}' in os.environ:
                filtered_args[k] = os.environ[f'{name.upper()}_{k.upper()}']
            elif k in handler_config:
                filtered_args[k] = handler_config[k]
        return filtered_args

    def connect(self) -> object:
        """ Set up any connections required by the handler
        Should return output of check_connection() method after attempting
        connection. Should switch self.is_connected.
        Returns:
            HandlerStatusResponse
        """
        if self.is_connected and self.service is not None:
            return webzio

        webzio.config(token=self.connection_args['token'])
        return webzio

    def check_connection(self) -> StatusResponse:
        """ Check connection to the handler
        Returns:
            HandlerStatusResponse
        """
        response = StatusResponse(False)
        try:
            webzio_client = self.connect()
            webzio_client.query('filterWebContent', {"q": 'AI', 'size': 1})
            response.success = True
        except Exception as e:
            response.error_message = f'Error connecting to Webz api: {e}.'

        if response.success is False and self.is_connected is True:
            self.is_connected = False

        return response

    def native_query(self, query: str = None) -> Response:
        """Receive raw query and act upon it somehow.
        Args:
            query (Any): query in native format (str for sql databases,
                dict for mongo, api's json etc)
        Returns:
            HandlerResponse
        """        
        ast = parse_sql(query, dialect='mindsdb')
        return self.query(ast)

    def _parse_post(self, post, endpoint):
        MAPPING_OUTPUT_FIELDS = {
            'filterWebContent': ['language', 'title', 'uuid', 'text', 'url', 'author', 'published', 'updated', 'crawled']
        }
        output_fields = MAPPING_OUTPUT_FIELDS[endpoint]
        dotted_post = dotty(post)
        return {field.replace('.', '_'):dotted_post[field] for field in output_fields}

    def call_webz_api(self, method_name: str = None, params: Dict = None) -> pd.DataFrame:
        """Calls the API method with the given params.

        Returns results as a pandas DataFrame.

        Args:
            method_name (str): Method name to call
            params (Dict): Params to pass to the API call
        """
        if method_name not in ['filterWebContent', 'reviewFilter']:
            raise NotImplementedError('Method name {} not supported by Webz API Handler'.format(method_name))

        client = self.connect()

        left = None
        count_results = None

        data = []

        if 'size' in params:
            count_results = params['size']

        while True:
            if count_results is not None:
                left = count_results - len(data)
                if left == 0:
                    break
                elif left < 0:
                    # got more results that we need
                    data = data[:left]
                    break

                if left > self.max_page_size:
                    params['size'] = self.max_page_size
                else:
                    params['size'] = left

            log.logger.debug(f'Calling Webz API: {method_name} with params ({params})')

            output = client.query(method_name, params) if len(data) == 0 else client.get_next()
            for post in output['posts']:
                data.append(self._parse_post(post, method_name))

        df = pd.DataFrame(data)
        return df
