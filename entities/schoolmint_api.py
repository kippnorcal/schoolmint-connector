import json
import logging
import requests

from entities.data_source_objects import DataSource


class SchoolmintAPI:
    """Class for the SchoolMint API connection."""

    def __init__(self, data_source: DataSource):
        """Initialize environment variables used to connect to the API."""
        self.api_data = data_source.api
        self.data_source_type = data_source.source_type

    def request_report(self) -> None:
        """
        Post request to SchoolMint API. This triggers report generation 
        and upload to FTP associated with the report.
        """
        url = f"https://{self.api_data.domain}/api/v2/demand_exports"
        headers = {"Api-Token": self.api_data.api_token}
        body = {"account_email": self.api_data.account_email}
        response = requests.post(url, headers=headers, data=body)
        if response.ok:
            logging.info(f"API respose for {self.data_source_type.value} is successful")
        else:
            j_data = json.loads(response.content.decode())
            logging.info(
                "API Error - "
                + "Error Code: "
                + str(j_data["error_code"])
            )
            logging.info("Error Message: " + j_data["error_msg"])
            response.raise_for_status()
