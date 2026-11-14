from typing import Union
from dataclasses import dataclass

from .data_source_types import DataSourceTypes
from utils.data_config import DATA_SOURCE_CONFIG


@dataclass
class ApiData:
    domain: str
    account_email: str
    api_token: str


class DataSource:

    def __init__(
            self: str,
            local_dir: str,
            sftp_source_dir: str,
            source_type: DataSourceTypes,
            report_name: str,
            base_file_name: str,
            current_year_folder: str,
            historical_folder: str,
            sftp_archive_dir: str,
            api: Union[ApiData, None],
            school_year: Union[None, str] = None,
    ):
        self.local_dir = local_dir
        self.sftp_source_dir = sftp_source_dir
        self.source_type = source_type
        self.report_name = report_name
        self.base_file_name = base_file_name
        self.current_year_folder = current_year_folder
        self.historical_folder = historical_folder
        self.sftp_archive_dir = sftp_archive_dir
        self.api = api
        self.school_year = school_year

    def generate_download_path(self) -> str:
        pass

    def generate_upload_path(self, as_parquet: bool = False) -> str:
        if as_parquet:
            return f"{self.current_year_folder}/{self.base_file_name}_{self.school_year}.parquet"
        else:
            return f"{self.current_year_folder}/{self.base_file_name}_{self.school_year}.csv"


def create_source_data_object(source_type: DataSourceTypes) -> DataSource:
    config = DATA_SOURCE_CONFIG[source_type]

    api_data = config.get("api_connection")
    api_object = None
    if api_data is not None:
        api_object = ApiData(**api_data)

    return DataSource(
        local_dir=config.get("local_dir"),
        sftp_source_dir=config.get("sftp_source_dir"),
        source_type=config.get("source_type"),
        report_name=config.get("report_name"),
        base_file_name=config.get("base_file_name"),
        current_year_folder=config.get("current_year_folder"),
        historical_folder=config.get("historical_folder"),
        sftp_archive_dir=config.get("sftp_archive_dir"),
        api=api_object
    )
