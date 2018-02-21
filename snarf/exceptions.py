class SnarfError(Exception):
    '''Base Snarf Error'''


class ProgramWarning(core.SnarfError):
    '''A program warning occurred.'''


class ProgramError(core.SnarfError):
    '''A program error occurred.'''

