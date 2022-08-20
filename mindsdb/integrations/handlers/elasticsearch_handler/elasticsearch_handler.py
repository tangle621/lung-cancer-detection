from typing import Optional
from collections import OrderedDict

import pandas as pd
from elasticsearch import Elasticsearch

from mindsdb_sql import parse_sql
from mindsdb_sql.render.sqlalchemy_render import SqlalchemyRender
from es.elastic.sqlalchemy import ESDialect
from mindsdb.integrations.libs.base_handler import DatabaseHandler

from mindsdb_sql.parser.ast.base import ASTNode

from mindsdb.utilities.log import log
from mindsdb.integrations.libs.response import (
    HandlerStatusResponse as StatusResponse,
    HandlerResponse as Response,
    RESPONSE_TYPE
)
from mindsdb.integrations.libs.const import HANDLER_CONNECTION_ARG_TYPE as ARG_TYPE


class ElasticsearchHandler(DatabaseHandler):
    """
    This handler handles connection and execution of the Airtable statements.
    """

    name = 'elasticsearch'

    def __init__(self, name: str, connection_data: Optional[dict], **kwargs):
        """
        Initialize the handler.
        Args:
            name (str): name of particular handler instance
            connection_data (dict): parameters for connecting to the database
            **kwargs: arbitrary keyword arguments.
        """
        super().__init__(name)
        self.parser = parse_sql
        self.dialect = 'elasticsearch'
        self.connection_data = connection_data
        self.kwargs = kwargs

        self.connection = None
        self.is_connected = False

    def __del__(self):
        if self.is_connected is True:
            self.disconnect()

    def connect(self) -> StatusResponse:
        """
        Set up the connection required by the handler.
        Returns:
            HandlerStatusResponse
        """

        if self.is_connected is True:
            return self.connection

        self.connection = Elasticsearch(
            hosts=self.connection_data['hosts'].split(','),
            cloud_id=self.connection_data['cloud_id'],
            basic_auth=(self.connection_data['username'], self.connection_data['password'])
        )
        self.is_connected = True

        return self.connection

    def disconnect(self):
        """
        Close any existing connections.
        """

        if self.is_connected is False:
            return

        self.connection.close()
        self.is_connected = False
        return self.is_connected

    def check_connection(self) -> StatusResponse:
        """
        Check connection to the handler.
        Returns:
            HandlerStatusResponse
        """

        response = StatusResponse(False)
        need_to_close = self.is_connected is False

        try:
            self.connect()
            response.success = True
        except Exception as e:
            log.error(f'Error connecting to Elasticsearch {self.connection_data["hosts"]}, {e}!')
            response.error_message = str(e)
        finally:
            if response.success is True and need_to_close:
                self.disconnect()
            if response.success is False and self.is_connected is True:
                self.is_connected = False

        return response

    def native_query(self, query: str) -> StatusResponse:
        """
        Receive raw query and act upon it somehow.
        Args:
            query (str): query in native format
        Returns:
            HandlerResponse
        """

        need_to_close = self.is_connected is False

        connection = self.connect()

        try:
            response = connection.sql.query(body={'query': query})
            records = response['rows']
            columns = response['columns']

            new_records = True
            while new_records:
                try:
                    if response['cursor']:
                        response = connection.sql.query(body={'query': query, 'cursor': response['cursor']})

                        new_records = response['rows']
                        records = records + new_records
                except Exception as e:
                    new_records = False

            if records:
                response = Response(
                    RESPONSE_TYPE.TABLE,
                    data_frame=pd.DataFrame(
                        records,
                        columns=[column['name'] for column in columns]
                    )
                )
        except Exception as e:
            log.error(f'Error running query: {query} on {self.connection_data["database"]}!')
            response = Response(
                RESPONSE_TYPE.ERROR,
                error_message=str(e)
            )

        if need_to_close is True:
            self.disconnect()

        return response

    def query(self, query: ASTNode) -> StatusResponse:
        """
        Receive query as AST (abstract syntax tree) and act upon it somehow.
        Args:
            query (ASTNode): sql query represented as AST. May be any kind
                of query: SELECT, INTSERT, DELETE, etc
        Returns:
            HandlerResponse
        """

        renderer = SqlalchemyRender(ESDialect)
        query_str = renderer.get_string(query, with_failback=True)
        return self.native_query(query_str)