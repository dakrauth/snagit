class SnagitError(Exception):
    """Base Snagit Error"""


class ProgramWarning(SnagitError):
    """A program warning occurred."""


class ProgramError(SnagitError):
    """A program error occurred."""


class SnagitQuit(SnagitError):
    """User quits repl"""


class SnagitStopInteration(SnagitError):
    """Used to break out of a content iteration loop"""
