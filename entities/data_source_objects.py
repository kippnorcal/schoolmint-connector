from data_source_types import DataSourceTypes
from utils.data_config import DATA_SOURCE_CONFIG

class SourceData:

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
            is_api: bool,
    ):
        self.local_dir = local_dir
        self.sftp_source_dir = sftp_source_dir
        self.source_type = source_type
        self.report_name = report_name
        self.base_file_name = base_file_name
        self.current_year_folder = current_year_folder
        self.historical_folder = historical_folder
        self.sftp_archive_dir = sftp_archive_dir
        self.is_api = is_api

    def generate_download_path(self) -> str:
        pass

    def generate_upload_path(self) -> str:
        pass


def create_source_data_object(source_type: DataSourceTypes) -> SourceData:
    config = DATA_SOURCE_CONFIG[source_type]
    return SourceData(
        local_dir=config("local_dir"),
        sftp_source_dir=config("sftp_source_dir"),
        source_type=config("source_type"),
        report_name=config("report_name"),
        base_file_name=config("base_file_name"),
        current_year_folder=config(),
        historical_folder=config("historical_folder"),
        sftp_archive_dir=config("sftp_archive_dir"),
    )
