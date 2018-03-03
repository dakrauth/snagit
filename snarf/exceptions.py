class SnarfError(Exception):
    '''Base Snarf Error'''


class ProgramWarning(SnarfError):
    '''A program warning occurred.'''


class ProgramError(SnarfError):
    '''A program error occurred.'''


class SnarfQuit(SnarfError):
    '''User quits repl'''
