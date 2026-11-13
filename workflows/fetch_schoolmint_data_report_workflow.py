import logging
import os
import time
from typing import List

import pandas as pd
from tenacity import *
from gbq_connector import CloudStorageClient

from entities.data_source_objects import DataSource
from entities.ftp import FTP
from schoolmint_api import SchoolmintAPI
from utils.data_config import COLUMN_RENAME_MAP
from utils import helpers


def read_csv_to_df(file_name: str) -> pd.DataFrame:
    if not os.path.isfile(file_name):
        raise Exception(
            f"ERROR: '{file_name}' file does not exist. Most likely problem downloading from sFTP."
        )
    df = pd.read_csv(file_name, sep=",", quotechar='"', doublequote=True, dtype=str, header=0)
    count = len(df.index)
    logging.info(f"Read {count} rows from CSV file '{file_name}'.")
    if int(os.getenv("REJECT_EMPTY_FILES")):
        if count == 0:
            raise Exception(f"ERROR: No data was loaded from CSV file '{file_name}'.")
    return df


def delete_data_files(directory: str) -> None:
    """
    Delete data files (not everything) from the given directory.

    :param directory: Directory that we want to delete data files from
    :type directory: String
    """
    for file in os.listdir(directory):
        if "Data" in file:
            os.remove(os.path.join(directory, file))


def get_latest_file(data_source: DataSource):
    """
    Get the file that matches the given name.
    Reverse sort by modification date in case there are multiple.

    :param filename: Name of the file that we're looking for
    :type filename: String
    :return: Name of the most recently modified file with the given name
    :rtype: String
    """
    logging.info(f"Checking {data_source.local_dir} for files")
    all_files = os.listdir(data_source.local_dir)
    files = sorted(
        all_files,
        key=lambda file: os.path.getmtime(f"{data_source.local_dir}/{file}"),
        reverse=True,
    )
    if files:
        file = files[0]
        logging.info(f"Downloaded '{file}'.")
    else:
        raise Exception(f"Unable to download file.")
    return file


@retry(wait=wait_fixed(30), stop=stop_after_attempt(60))
def download_from_ftp(ftp: FTP, data_source: DataSource):
    """
    Download data files from FTP. It can take some time for SchoolMint
    to upload the reports after the API request, so we use Tenacity retry
    to wait up to 30 min.
    """
    logging.info(f"Attempting to download file from {data_source.sftp_source_dir}")
    time.sleep(30)  # wait to allow the API files to download
    if not ftp.get_latest_file_with_prefix(
        data_source.sftp_source_dir, data_source.local_dir, data_source.report_name
    ):
        raise FileNotFoundError(f"No {data_source.report_name} file found on SFTP")
    file = get_latest_file(data_source)
    return file


def check_for_new_columns(df: pd.DataFrame) -> bool:
    expected_columns = list(COLUMN_RENAME_MAP.values())

    new_columns = helpers.column_diff(df, expected_columns, add_cols=True)

    if new_columns:
        logging.info(f"Found the following new columns:")
        for column in new_columns:
            logging.info(column)
        logging.info("Please add these new columns to the data config.")
        return True
    else:
        return False


def check_for_deleted_columns(df: pd.DataFrame) -> bool:
    expected_columns = list(COLUMN_RENAME_MAP.keys())


    removed_columns = helpers.column_diff(df, expected_columns, remove_cols=True)

    if removed_columns:
        logging.info(f"The following columns appear missing fom the report:")
        for column in removed_columns:
            logging.info(column)
        logging.info("Please update the map in the data_config module to add or remove column.")
        return True
    else:
        return False


def fetch_report(data_sources: list[DataSource], cloud_client: CloudStorageClient):

    ftp = FTP()
    for data_source in data_sources:
        logging.info(f"Processing {data_source.source_type.value} data")
        try:
            if data_source.api:
                ftp.archive_remote_files(data_source.sftp_source_dir)
                ftp.delete_old_archive_files(data_source.sftp_archive_dir)
                logging.info("Getting API data")
                SchoolmintAPI(data_source).request_report()

            if int(os.getenv("DELETE_LOCAL_FILES")):
                delete_data_files(data_source.local_dir)

            logging.info("Downloading Files")
            file = download_from_ftp(ftp, data_source)

            df_file = read_csv_to_df(f"{data_source.local_dir}/{file}")
            df_file["school_year_4_digit"] = data_source.school_year
            check_for_deleted_columns(df_file)
            df_file = df_file.rename(columns=COLUMN_RENAME_MAP)
            if check_for_new_columns(df_file):
                logging.info("Filtering out new columns that are not in the config.")
                df_file = df_file[list(COLUMN_RENAME_MAP.values())]

            bucket = os.getenv("BUCKET")
            cloud_client.load_dataframe_to_cloud_as_csv(bucket, data_source.generate_upload_path(), df_file)
            cloud_client.load_dataframe_to_cloud_as_parquet(bucket, data_source.generate_upload_path(as_parquet=True), df_file)
        finally:
            ftp.close()
