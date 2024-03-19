import argparse
import datetime
import io
import logging
import pause
import yaml

from CCAPI import CCAPI
from datetime import datetime, timedelta, timezone

class EclipseCanon(object):

    def __init__(self, config):
        self._log = logging.getLogger()
        self._config = config

        self._C1 = datetime.strptime(cfg['Eclipse']['c1'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self._C2 = datetime.strptime(cfg['Eclipse']['c2'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self._C3 = datetime.strptime(cfg['Eclipse']['c3'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self._C4 = datetime.strptime(cfg['Eclipse']['c4'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self._Max = datetime.strptime(cfg['Eclipse']['max'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    # end __init__

    def _EnableDebugMode(self):
        """
        A function to overwrite the configured time using relative times instead of absolute from the configuration
        :return:
        """
        now = datetime.now(timezone.utc)
        self._C1 = now + timedelta(seconds=10)
        self._C2 = self._C1 + timedelta(hours=1, minutes=23)
        self._C3 = self._C2 + timedelta(minutes=3, seconds=58)
        self._C4 = self._C3 + timedelta(hours=1, minutes=23)

    def getPhase(self):
        #TODO CONSIDER TIME AFTER C3
        now = datetime.now(timezone.utc)
        tC2 = self._C2 - now
        retVal = None

        if now < self._C1:
            retVal = "PRE"
        elif self._C1 < now and now < self._C2 and tC2.seconds > 10:
            retVal = "C1"
        elif now > self._C1 and now < self._C2 and tC2.seconds <= 10:
            retVal = "BEADS"
        elif self._C2 < now and self._C3 > now:
            retVal = "C2"
        elif self._C3 < now and self._C4 > now:
            retVal = "C3"
        elif now > self._C4:
            retVal = "POST"

        return retVal
    # end getPhase

    def getWakeTime(self):
        """
        :return:
        """
        now = datetime.now(timezone.utc)
        tC2 = self._C2 - now

        if now < self._C1:
            wake = self._C1
        elif now > self._C1 and now < self._C2 and tC2.seconds > 17:
            # In C1 with more than 17 seconds to C2, sleep for 6 seconds
            wake = datetime.now() + timedelta(seconds=self._config['Walk']['C1Delay'])
        elif now > self._C1 and tC2.seconds < 17:
            # If we are within 17 seconds of C2, wake 10 seconds before it
            wake = self._C2 + timedelta(seconds=-10)
        elif now > self._C3:
            # If we are within C3, sleep for 6 seconds
            wake = datetime.now() + timedelta(seconds=self._config['Walk']['C3Delay'])

        return wake
    # end getWakeTime


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

def parseArguments():
    parser = argparse.ArgumentParser(
        prog="Eclipse Canon",
        description="Eclipse Photography software for CCAPI compatible software"
    )

    parser.add_argument("configuration",
                        help="The configuration file that contains the C1, C2, C3, C4 times as well as the camera settings")

    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        default=False,
                        help="Verbose settings enables debug logging")

    parser.add_argument("-l", "--logFile",
                        default="eclipsecanon.log",
                        help="The Log File Location")

    parser.add_argument("-dR", "--DryRun",
                        default=True,
                        help="Dry Run, don't take photos")

    args = parser.parse_args()
    return args


def parseConfig(configFile: str):
    with io.open(configFile, "r") as stream:
        cfg = yaml.safe_load(stream)
    return cfg


if __name__ == "__main__":
    args = parseArguments()
    log = setupLogging(verbose=args.verbose, logFile=args.logFile)
    cfg = parseConfig(args.configuration)

    ec = EclipseCanon(config=cfg)
    ec._EnableDebugMode()

    ccapi = None

    if 'CCAPI' not in cfg:
        log.error("Missing CCAPI Configuration")
    elif 'IPAddress' not in cfg['CCAPI']:
        log.error("Missing IPAddress in CCAPI Configuration Section")
    else:
        ccapi = CCAPI(IPAddress=cfg['CCAPI']['IPAddress'], dryRun=False)

    if "Configuration" not in cfg:
        log.error("Missing Configuration setting from configuration file")
    elif cfg['Configuration'] == "Walk":
        log.info("Walk Configuration")
        while ec.getPhase() == "PRE":
            wake = ec.getWakeTime()
            log.info(f"Waiting for C1 at {wake}")
            pause.until(wake)

        ##################################
        # C1 Settings
        ##################################
        ccapi.iso = cfg['Walk']['C1ISO']
        ccapi.tv = cfg['Walk']['C1Shutter']
        while ec.getPhase() == "C1":
            log.info(f"Capturing C1 at {datetime.now()}")
            ccapi.shoot(af=False)
            if cfg['Walk']['EnableDownload']:
                # Attemps to download the last two photos that were taken.
                files = ccapi.getDeviceStorage()[:2]
                for f in files:
                    log.info(f"Downloading {f}")
                    ccapi.downloadFile(saveDirectory=cfg['Walk']['DownloadDirectory'],
                                       remotePath=f,
                                       removeAfterDownload=cfg['Walk']['RemoveAfterDownload'])
            pause.until(ec.getWakeTime())
        ##################################
        # Baily's Beads Settings
        ##################################
        ccapi.iso = cfg['Walk']['BeadsISO']
        ccapi.tv = cfg['Walk']['BeadsShutter']
        while ec.getPhase() == "BEADS":
            log.info(f"Capturing Beads at {datetime.now()}")
            ccapi.shoot(af=False)

        ##################################
        # C2 Settings (Totality)
        ##################################
        while ec.getPhase() == "C2":
            isos = ccapi.getISOAbility(maxISO=800)
            log.info(f"ISO Capability: {isos}")
            tvs = ccapi.getTVAbility(maxTV='3"')
            log.info(f"TV Capability: {tvs}")

            photos = 0
            for iso in isos:
                ccapi.iso = iso
                for tv in tvs:
                    ccapi.tv = tv
                    log.info(f"Capturing Totality at {datetime.now()} with Setting TV: {tv}   ISO: {iso}")
                    ccapi.shoot(af=False)
                    photos += 1
                    if ec.getPhase() != "C2":
                        log.info("Totality Ended moving on")
                        break
                else:
                    continue # Only executed if the loop did NOT break
                break
            else:
                continue
                # end for
            break
            # end for

            log.debug(f"Photos Taken: {photos}")

        ##################################
        # C3 Settings
        ##################################
        ccapi.iso = cfg['Walk']['C3ISO']
        ccapi.tv = cfg['Walk']['C3Shutter']
        while ec.getPhase() == "C3":
            log.info(f"Capturing C3 at {datetime.now()}")
            ccapi.shoot(af=False)
            if cfg['Walk']['EnableDownload']:
                # Attemps to download the last two photos that were taken.
                files = ccapi.getDeviceStorage()[:2]
                for f in files:
                    log.info(f"Downloading {f}")
                    ccapi.downloadFile(saveDirectory=cfg['Walk']['DownloadDirectory'],
                                       remotePath=f,
                                       removeAfterDownload=cfg['Walk']['RemoveAfterDownload'])
            pause.until(ec.getWakeTime())

        # If Enable Download turned on, download the rest of the files that have not had
        # the opportunity to be pulled off the camera
        if cfg['Walk']['EnableDownload']:
            files = ccapi.getDeviceStorage()
            for f in files:
                log.info(f"Downloading {f}")
                ccapi.downloadFile(saveDirectory=cfg['Walk']['DownloadDirectory'],
                                   remotePath=f,
                                   removeAfterDownload=cfg['Walk']['RemoveAfterDownload'])

    elif cfg['Configuration'] == "Cameras":
        log.info("Cameras Configuration")
    else:
        log.error("Invalid Configuration Setting")
