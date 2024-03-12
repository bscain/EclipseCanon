import argparse
import io
import json
import logging
import os

import datetime
import smtplib
import ssl
import urllib3
import yaml

# from email.message import EmailMessage
from requests.utils import requote_uri
from datetime import datetime, timedelta

_logfile = "ccapi.log"


class CCAPI(object):
    """
    The Cannon Connect API is designed to operate with the REST interface on the Canon EoS cameras.
    """

    _IPAddress = "192.168.1.172:8080" # TODO HARD CODED

    def __init__(self):
        self._log = logging.getLogger()
        self._server = urllib3.PoolManager()

    # AV Apeture Value
    # TV Shutter Speed
    # ISO

    def _GetCamera(self,
                   url: str) -> dict:
        """
        Method to GET data from a given URL of a JSON Rest API.
        :return:
        """
        headers = {}
        url = requote_uri(url)
        self._log.debug(f"Getting URL: {url}")
        resp = self._server.request(method="GET", url=url, headers=headers)

        if resp.status == 200:
            retVal = json.loads(resp.data)
        else:
            self._log.warning(f"Query failed with status code: {resp.status}")
            retVal = None

        return retVal
    # end _GetCamera

    def _PutCamera(self,
                   url: str,
                   data: dict) -> bool:
        """
        Method to Put data to the given URL of a JSON Rest API.
        :param url: The full url to POST data to
        :param data: The data to be posted
        :return: A boolean indicating if a status 200 was returned from the server indicating success
        """
        if self._server is None:
            retVal = None
        else:
            headers = {}
            headers['Content-Type'] = "application/json"

            self._log.debug(f"Putting to URL: {url}")
            resp = self._server.request(method="PUT", url=url, headers=headers, json=data)

            if resp.status != 200:
                self._log.warning(f"PUT Failed with Status Code {resp.status}")
            # end if
            retVal = resp.status == 200
        # end else

        return retVal
    # end _PutCamera

    @property
    def av(self):
        url = f"{self._IPAddress}/ccapi/ver100/shooting/settings/av"
        data = self._GetCamera(url)
        self._log.debug(f"Camera Aperture Setting {data}")
        return data
    # end av

    @av.setter
    def av(self, value):
        url = f"{self._IPAddress}/ccapi/ver100/shooting/settings/iso"
        data = self._GetCamera(url)
        self._log.debug(f"Camera ISO Setting {data}")
        return data

    @property
    def battery(self):
        url = f"http://{self._IPAddress}/ccapi/ver100/devicestatus/battery"
        data = self._GetCamera(url)
        self._log.debug(f"Camera Battery Status {data}")
        return data
    # end battery

    @property
    def iso(self):
        url = f"{self._IPAddress}/ccapi/ver100/shooting/settings/iso"
        data = self._GetCamera(url)
        self._log.debug(f"Camera ISO Setting {data}")
        return data
    # end ISO

    @iso.setter
    def iso(self, value):
        ability = self.iso["ability"]

        if str(value) in ability:
            self._log.info(f"Setting ISO to {value}")
            url = f"{self._IPAddress}/ccapi/ver100/shooting/settings/iso"
            dataValue = {"value": str(value)}
            data = self._PutCamera(url=url, data=dataValue)
        else:
            self._log.warning(f"Unable to set ISO Value {value} not within {ability}")
            data = None
        return data

    @property
    def tv(self):
        """
        Setter for the Exposure (a.k.a. TV) value of the shot
        :return:
        """
        url = f"{self._IPAddress}/ccapi/ver100/shooting/settings/tv"
        data = self._GetCamera(url)
        self._log.debug(f"Camera ISO Setting {data}")
        return data
    # end ISO

    @tv.setter
    def tv(self, value):
        """
        Setter for the Exposure Time (a.k.a. TV) time
        :param value:
        :return:
        """
        ability = self.tv["ability"]

        if str(value) in ability:
            self._log.info(f"Setting Exposure (a.k.a., TV to {value}")
            url = f"{self._IPAddress}/ccapi/ver100/shooting/settings/tv"
            dataValue = {"value": str(value)}
            data = self._PutCamera(url=url, data=dataValue)
        else:
            self._log.warning(f"Unable to set TV Value {value} not within {ability}")
            data = None
        return data

    def getDeviceInformation(self):
        url = f"{self._CCURL}/ver100/deviceinformation"
        data = self._GetBDAPI(url)

# end CCAPI


def setupLogging(verbose: bool,
                 logFile: str) -> logging.Logger:
    """
    Set up basic Logging for the system which logs to both the console and the given log file
    :param verbose: If true Verbose debug logging will be enabled, otherwise log level is infomation only
    :param logFile: The path to the log file to dump the log data to.
    :return: The constructed logger
    """
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    rootLogger = logging.getLogger()

    if verbose is True:
        rootLogger.setLevel(logging.DEBUG)
    else:
        rootLogger.setLevel(logging.INFO)

    fileHandler = logging.FileHandler(logFile)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

    return rootLogger
# end setupLogging

if __name__ == "__main__":

    setupLogging(verbose=True, logFile=_logfile)
    ccapi = CCAPI()

    print(ccapi.battery)
    print(ccapi.iso)
    print(ccapi.av)
    print(ccapi.tv)

    ccapi.iso = 100
    ccapi.tv = '30"'
