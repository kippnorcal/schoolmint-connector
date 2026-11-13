import logging
import os
import sys
import traceback
from typing import List

from job_notifications import create_notifications
from gbq_connector import CloudStorageClient
from gbq_connector import DbtClient

from entities.data_source_objects import create_source_data_object
from entities.data_source_objects import SourceData
from entities.data_source_types import DataSourceTypes
from utils import runtime_args
from workflows import add_historical_columns_workflow
from workflows import fetch_schoolmint_data_report_workflow
from workflows import generate_schema_workflow
from workflows import rename_historical_columns


logging.basicConfig(
    handlers=[
        logging.FileHandler(filename="app.log", mode="w+"),
        logging.StreamHandler(sys.stdout),
    ],
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %I:%M:%S%p %Z",
)
logging.getLogger("paramiko").setLevel(logging.ERROR)

args = runtime_args.get_runtime_args()

notifications = create_notifications("Schoomint Connector", "mailgun")


def _set_up_data_source_objects() -> List[SourceData]:
    data_sources = []
    for _type in DataSourceTypes:
        ds = create_source_data_object(_type)
        ds.school_year = args.school_year
        data_sources.append(ds)
    return data_sources


def main():
    school_year = args.school_year
    cloud_client = CloudStorageClient()
    rename_map = dict(args.rename_hist_column or [])

    if args.dbt_refresh:
        notifications.extend_job_name(f" - {args.school_year} w/dbt refresh")
        sources = _set_up_data_source_objects()
        fetch_regional_data_report_workflow.fetch_report(sources, cloud_client)
        logging.info("Running dbt snapshot")
        dbt_conn = DbtClient()
        dbt_conn.run_job()
    elif args.add_historical_columns:
        notifications.extend_job_name(f" - Add new cols to hist SM files")
        logging.info("Adding new columns to historical SM files")
        add_historical_columns_workflow.run_workflow(school_year, cloud_client)
    elif args.semt_refresh:
        notifications.extend_job_name(f" - {args.school_year} w/SEMT refresh")
        sources = _set_up_data_source_objects()
        fetch_regional_data_report_workflow.fetch_report(sources, cloud_client)
        job_id = os.getenv("SEMT_JOB_ID")
        logging.info("Refreshing the SEMT datasource")
        dbt_conn = DbtClient()
        dbt_conn.run_job(job_id=job_id)
    elif args.generate_schema:
        notifications.extend_job_name(f" - Generate JSON Schema")
        logging.info("Generating JSON Schema")
        generate_schema_workflow.generate_schema(school_year, cloud_client)
    elif rename_map:
        notifications.extend_job_name(f" - Renaming Hist Columns")
        rename_historical_columns.run_workflow(cloud_client, rename_map)
    else:
        notifications.extend_job_name(f" - {args.school_year}")
        sources = _set_up_data_source_objects()
        fetch_regional_data_report_workflow.fetch_report(sources, cloud_client)


if __name__ == "__main__":
    try:
        main()
        notifications.notify()
    except Exception as e:
        logging.exception(e)
        stack_trace = traceback.format_exc()
        failure_email_address = os.getenv("FAILURE_EMAIL")
        if failure_email_address is not None:
            notifications.simple_email(
                from_address=os.getenv("FROM_ADDRESS"),
                to_address=failure_email_address,
                subject="BigQuery Schoolmint Connector - Failed",
                body="See #data_notifications for details."
            )
        notifications.notify(error_message=stack_trace)
