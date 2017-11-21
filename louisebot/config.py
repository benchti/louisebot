# -*- encoding: utf-8 -*-

"""
Define endpoint to connect to slack
.. code:: ini
    [default]
    ; general configuration: default endpoint
    endpoint=dev
    [dev]
    ; configuration specific to 'dev' endpoint
    bot_id=id
    bot_token=token
The client will successively attempt to locate this configuration file in
1. Current working directory: ``./louisebot.conf``
2. Current user's home directory ``~/.louisebot.conf``
3. System wide configuration ``/etc/louisebot.conf``
This lookup mechanism makes it easy to overload credentials for a specific
project or user.
"""

import os

try:
    from ConfigParser import RawConfigParser, NoSectionError, NoOptionError
except ImportError:  # pragma: no cover
    # Python 3
    from configparser import RawConfigParser, NoSectionError, NoOptionError

__all__ = ['config']

#: Locations where to look for configuration file by *increasing* priority
CONFIG_PATH = [
    '/etc/louisebot.conf',
    os.path.expanduser('~/.louisebot.conf'),
    os.path.realpath('./louisebot.conf'),
]


class ConfigurationManager(object):
    '''
    Application wide configuration manager
    '''
    def __init__(self):
        '''
        Create a config parser and load config from environment.
        '''
        # create config parser
        self.config = RawConfigParser()
        self.config.read(CONFIG_PATH)

    def get(self, section, name):
        '''
        Load parameter ``name`` from configuration, respecting priority order.
        Most of the time, ``section`` will correspond to the current api
        ``endpoint``. ``default`` section only contains ``endpoint`` and
        general configuration.
        :param str section: configuration section or region name. Ignored when
            looking in environment
        :param str name: configuration parameter to lookup
        '''
        # try from specified section/endpoint
        try:
            return self.config.get(section, name)
        except (NoSectionError, NoOptionError):
            pass

        # not found, sorry
        return None

    def read(self, config_file):
        # Read an other config file
        self.config.read(config_file)


#: System wide instance :py:class:`ConfigurationManager` instance
config = ConfigurationManager()
