import json
import logging

import os
import shutil

import time
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

    # TODO hard Coded IP Address Still... Consider a Search
    def __init__(self, IPAddress = "192.168.1.172:8080", dryRun=False):
        self._log = logging.getLogger()
        self._server = urllib3.PoolManager()

        self._IPAddress = IPAddress
        self._DryRun = dryRun
    # AV Apeture Value
    # TV Shutter Speed
    # ISO

    def _convertFloat(self,
                      fraction: str) -> float:
            try:
                return float(fraction)
            except ValueError:
                num, denom = fraction.split('/')
                try:
                    leading, num = num.split(' ')
                    whole = float(leading)
                except ValueError:
                    whole = 0
                frac = float(num) / float(denom)
                return whole - frac if whole < 0 else whole + frac

    def _GetCamera(self,
                   url: str,
                   retryCount=5,
                   retryDelay=0.1) -> dict:
        """
        Method to GET data from a given URL of a JSON Rest API.
        :return:
        """
        headers = {}
        url = requote_uri(url)
        retVal = None
        while retVal is None and retryCount > 0:
            self._log.debug(f"Getting URL: {url}")
            resp = self._server.request(method="GET", url=url, headers=headers)

            if resp.status == 200:
                retVal = json.loads(resp.data)
            else:
                self._log.debug(f"Query failed with status code: {resp.status}")
                retVal = None
                retryCount -= 1
                time.sleep(retryDelay)
        # end while

        return retVal
    # end _GetCamera

    def _PostCamera(self,
                   url: str,
                   data: dict,
                   retryCount = 5,
                   retryDelay = 0.1) -> bool:
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

            retVal = None
            while retVal is None and retryCount > 0:
                self._log.debug(f"POST to URL: {url}")
                resp = self._server.request(method="POST", url=url, headers=headers, json=data)

                if resp.status == 200:
                    retVal = True
                else:
                    self._log.debug(f"POST Failed with Status Code {resp.status}")
                    time.sleep(retryDelay)
                    retryCount -= 1
                # end if
            # end while
        # end else

        return retVal
    # end _PutCamera

    def _PutCamera(self,
                   url: str,
                   data: dict,
                   retryCount=5,
                   retryDelay=0.1) -> bool:
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

            retVal = None
            while retVal is None and retryCount > 0:
                self._log.debug(f"Putting to URL: {url}")
                resp = self._server.request(method="PUT", url=url, headers=headers, json=data)

                if resp.status == 200:
                    retVal = True
                else:
                    self._log.debug(f"PUT Failed with Status Code {resp.status}")
                    time.sleep(retryDelay)
                    retryCount -= 1
                # end if
        # end else

        return retVal
    # end _PutCamera

    def _DeleteCamera(self,
                      url: str,
                      retryCount=5,
                      retryDelay=0.1):
        """
        TODO WRITE ME
        :param url:
        :return:
        """
        headers = {}
        url = requote_uri(url)

        retVal = None
        while retVal is None and retryCount > 0:
            self._log.debug(f"Deleting URL: {url}")
            resp = self._server.request(method="DELETE", url=url, headers=headers)

            if resp.status == 200:
                retVal = json.loads(resp.data)
            else:
                self._log.debug(f"Query failed with status code: {resp.status}")
                time.sleep(retryDelay)
                retryCount -= 1
        # end while

        return retVal
    # end _DeleteCamera

    def downloadFile(self, saveDirectory, remotePath, removeAfterDownload = False):

        fileName = os.path.join(saveDirectory, remotePath.split('/')[-1])
        url = f"{self._IPAddress}{remotePath}"

        with self._server.request("GET", url, preload_content=False) as resp, open (fileName, 'wb') as f:
            shutil.copyfileobj(resp, f)
        resp.release_conn()

        if removeAfterDownload:
            self._log.info(f"Removing Remote File: {remotePath}")
            self.deleteFile(remotePath)

    def deleteFile(self, remotePath):
        url = f"{self._IPAddress}{remotePath}"
        success = self._DeleteCamera(url)

        return success



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

    def getISOAbility(self, maxISO):
        isos = self.iso['ability']
        isos.remove("auto")
        retVal = []
        for iso in isos:
            if int(iso) <= int(maxISO):
                retVal.append(iso)
        return retVal
    # end getISOAbility

    def getTVAbility(self, maxTV):
        tvs = self.tv['ability']
        retVal = []
        maxTV = self._convertFloat(maxTV.replace('"', ".").rstrip("."))
        for tv in tvs:
            if self._convertFloat(tv.replace('"', ".").rstrip(".")) <= float(maxTV):
                retVal.append(tv)
        return retVal
    # end getISOAbility

    def shoot(self, af=True):
        if self._DryRun == True:
            self._log.info(f"Dry Run Photo with TV: {self.tv['value']}, ISO: {self.iso['value']}")
            success = True
        else:
            url = f"{self._IPAddress}/ccapi/ver100/shooting/control/shutterbutton"
            dataValue = {"af": af}
            success = self._PostCamera(url=url, data=dataValue)
        return success


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
    # end tv

    @property
    def wb(self):
        """
        TODO
        :return:
        """
        url = f"{self._IPAddress}/ccapi/ver100/shooting/settings/wb"
        data = self._GetCamera(url)
        self._log.debug(f"Camera WB Setting {data}")
        return data
    # end wb

    @wb.setter
    def wb(self, value):
        """
        Setter for the White Balance
        :param value:
        :return:
        """
        ability = self.wb["ability"]

        if str(value) in ability:
            self._log.info(f"Setting WB to {value}")
            url = f"{self._IPAddress}/ccapi/ver100/shooting/settings/wb"
            dataValue = {"value": str(value)}
            data = self._PutCamera(url=url, data=dataValue)
        else:
            self._log.warning(f"Unable to set wb Value {value} not within {ability}")
            data = None
        return data

    def getDeviceInformation(self):
        url = f"{self._CCURL}/ver100/deviceinformation"
        data = self._GetBDAPI(url)

    def getDeviceStorage(self):
        # TODO HARD CODED CURRENNTLY
        # url = f"{self._IPAddress}/ccapi/ver110/devicestatus/currentstorage"
        # data = self._GetCamera(url)
        #
        # cardPath = data['path'].replace("\\", "")
        # url = f"{self._IPAddress}{cardPath}"
        # data = self._GetCamera(url)
        url = f"{self._IPAddress}/ccapi/ver110/contents/card1/100CANON"
        data = self._GetCamera(url)['path']

        return data


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


    files = ccapi.getDeviceStorage()
    for f in files:
        print(f"Starting Download of {f} at{datetime.now()}")
        ccapi.downloadFile(saveDirectory=r"C:\eclipse", remotePath=f, removeAfterDownload=True)

    # ccapi._DeleteCamera("http://192.168.1.172:8080/ccapi/ver110/contents/card1/100CANON/IMG_1009.CR3")


    # print(ccapi.battery)
    # iso = ccapi.iso['ability']
    # print(ccapi.av)
    # print(ccapi.tv)

    # ccapi.iso = 100
    # ccapi.tv = '1/250'
    # for i in iso[1:10]:
    #     ccapi.iso = i
    #     ccapi.shoot()
    #     time.sleep(.5)

