class FileHandler(StreamHandler):
    """File handler for working with log files off of the microcontroller (like
    an SD card)
    :param str filename: The filename of the log file
    :param str mode: Whether to write ('w') or append ('a'); default is to append
    """

    def __init__(self, filename: str, mode: str = "a") -> None:
        # pylint: disable=consider-using-with
        super().__init__(open(filename, mode=mode))

    def close(self) -> None:
        """Closes the file"""
        self.stream.flush()
        self.stream.close()

    def format(self, record: LogRecord) -> str:
        """Generate a string to log
        :param record: The record (message object) to be logged
        """
        return super().format(record) + "\r\n"

    def emit(self, record: LogRecord) -> None:
        """Generate the message and write it to the UART.
        :param record: The record (message object) to be logged
        """
        self.stream.write(self.format(record))
