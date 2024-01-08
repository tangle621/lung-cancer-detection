from typing import List, Optional

from pydantic import BaseModel, BaseSettings, Extra, root_validator

from mindsdb.integrations.handlers.utilities.validation_utilities import ParameterValidationUtilities


class TwelveLabsHandlerModel(BaseModel):
    """
    Model for the Twelve Labs handler.

    Attributes
    ----------

    index_name : str
        Name of the index to be created or used.

    engine_id : str, Optional
        ID of the engine. If not provided, the default engine is used.

    api_key : str, Optional
        API key for the Twelve Labs API. If not provided, attempts will be made to get the API key from the following sources:
            1. From the engine storage.
            2. From the environment variable TWELVE_LABS_API_KEY.
            3. From the config.json file.

    index_options : List[str]
        List of that specifies how the platform will process the videos uploaded to this index. This will have no effect if the index already exists.

    addons : List[str], Optional
        List of addons that should be enabled for the index. This will have no effect if the index already exists.

    video_urls : List[str], Optional
        List of video URLs to be indexed. Either video_urls, video_files, video_urls_column or video_files_column should be provided.

    video_urls_column : str, Optional
        Name of the column containing video URLs to be indexed. Either video_urls, video_files, video_urls_column or video_files_column should be provided.

    video_files : List[str], Optional
        List of video files to be indexed. Either video_urls, video_files, video_urls_column or video_files_column should be provided.

    video_files_column : str, Optional
        Name of the column containing video files to be indexed. Either video_urls, video_files, video_urls_column or video_files_column should be provided.

    task : str, Optional
        Task to be performed.

    search_options : List[str], Optional
        List of search options to be used for searching. This will only be required if the task is search.

    query_column : str, Optional
        Name of the column containing the query to be used for searching. This will only be required if the task is search. Each query will be run against the entire index, not individual videos.

    For more information, refer the API reference: https://docs.twelvelabs.io/reference/api-reference
    """

    index_name: str
    engine_id: Optional[str] = None
    api_key: Optional[str] = None
    index_options: List[str]
    addons: List[str] = []
    video_urls: Optional[List[str]] = None
    video_urls_column: Optional[str] = None
    video_files: Optional[List[str]] = None
    video_files_column: Optional[str] = None
    task: str = None
    search_options: Optional[List[str]] = None
    query_column: Optional[str] = None

    class Config:
        extra = Extra.forbid

    @root_validator(pre=True, allow_reuse=True, skip_on_failure=True)
    def check_param_typos(cls, values):
        """
        Root validator to check if there are any typos in the parameters.

        Parameters
        ----------
        values : Dict
            Dictionary containing the attributes of the model.

        Raises
        ------
        ValueError
            If there are any typos in the parameters.
        """

        ParameterValidationUtilities.validate_parameter_spelling(cls, values)

        return values

    @root_validator(allow_reuse=True, skip_on_failure=True)
    def check_for_video_urls_or_video_files(cls, values):
        """
        Root validator to check if video_urls or video_files have been provided.

        Parameters
        ----------
        values : Dict
            Dictionary containing the attributes of the model.

        Raises
        ------
        ValueError
            If neither video_urls, video_files, video_urls_column nor video_files_column have been provided.

        """

        video_urls = values.get("video_urls")
        video_urls_column = values.get("video_urls_column")
        video_files = values.get("video_files")
        video_files_column = values.get("video_files_column")

        if not video_urls and not video_files and not video_urls_column and not video_files_column:
            raise ValueError(
                "Neither video_urls, video_files, video_urls_column nor video_files_column have been provided. Please provide one of them."
            )

        return values

    @root_validator(allow_reuse=True, skip_on_failure=True)
    def check_for_task_specific_parameters(cls, values):
        """
        Root validator to check if task has been provided along with the other relevant parameters for each task.

        Parameters
        ----------
        values : Dict
            Dictionary containing the attributes of the model.

        Raises
        ------
        ValueError
            If the relevant parameters for the task have not been provided.
        """

        task = values.get("task")

        if task == "search":
            search_options = values.get("search_options")
            if not search_options:
                raise ValueError(
                    "search_options have not been provided. Please provide search_options."
                )

            # search options should be a subset of index options
            index_options = values.get("index_options")
            if not set(search_options).issubset(set(index_options)):
                raise ValueError(
                    "search_options should be a subset of index_options."
                )

            query_column = values.get("query_column")
            if not query_column:
                raise ValueError(
                    "query_column has not been provided. Please provide query_column."
                )

        else:
            raise ValueError(
                f"task {task} is not supported. Please provide a valid task."
            )

        return values


class TwelveLabsHandlerConfig(BaseSettings):
    """
    Configuration for Twelve Labs handler.

    Attributes
    ----------

    BASE_URL : str
        Base URL for the Twelve Labs API.

    DEFAULT_ENGINE : str
        Default engine for the Twelve Labs API.

    DEFAULT_WAIT_DURATION : int
        Default wait duration when polling video indexing tasks created via the Twelve Labs API.
    """

    BASE_URL = "https://api.twelvelabs.io/v1.1"
    DEFAULT_ENGINE = "marengo2.5"
    DEFAULT_WAIT_DURATION = 5


twelve_labs_handler_config = TwelveLabsHandlerConfig()
