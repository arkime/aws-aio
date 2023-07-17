import coloredlogs
from contextlib import contextmanager
from datetime import datetime
import logging
import os
from pathlib import Path

class LoggingFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')


# Invisible Unicode character.  Makes figuring out the beginning/end of a log entry much
# easier, given they can contain new line characters themselves.
LINE_SEP = '\u2063'


class LoggingWrangler:
    def __init__(self):
        # This is a bit messy and fragile, but we want to get the get the repo's root directory path on the local host
        this_files_dir = os.path.dirname(os.path.abspath(__file__))
        current_dir_path = Path(this_files_dir)
        repo_root_dir = str(current_dir_path.parent)

        # Our logfile will be in the repo root dir
        self._logfile_path = os.path.join(repo_root_dir, self._default_log_name())

        self._initialize_logging()

    def _initialize_logging(self):
        """
        Write high level logs intended for humans to stdout, and low-level debug logs to a file.
        """

        root_logger = logging.getLogger()
        root_logger.handlers = []  # Make sure we're starting with a clean slate
        root_logger.setLevel(logging.DEBUG)

        # Send INFO+ level logs to stdout, and enable colorized messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = coloredlogs.ColoredFormatter('%(asctime)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # Send DEBUG+ level logs to a timestamped logfile for a historical record of the invocation
        file_handler_timestamped = logging.FileHandler(self._logfile_path, mode='a', encoding='utf8')
        file_handler_timestamped.setLevel(logging.DEBUG)
        file_formatter = LoggingFormatter(f"%(asctime)s - %(name)s - %(message)s{LINE_SEP}")
        file_handler_timestamped.setFormatter(file_formatter)
        root_logger.addHandler(file_handler_timestamped)

    def _default_log_name(self):
        return 'manage_arkime.log'

    @property
    def log_file(self):
        return self._logfile_path

@contextmanager
def set_boto_log_level(log_level = 'INFO'):
    boto_log_level = logging.getLogger('boto').level
    boto_log_level = logging.getLogger('boto3').level
    botocore_log_level = logging.getLogger('botocore').level

    logging.getLogger('boto').setLevel(log_level)
    logging.getLogger('boto3').setLevel(log_level)
    logging.getLogger('botocore').setLevel(log_level)

    yield

    logging.getLogger('boto').setLevel(boto_log_level)
    logging.getLogger('boto3').setLevel(boto_log_level)
    logging.getLogger('botocore').setLevel(botocore_log_level)