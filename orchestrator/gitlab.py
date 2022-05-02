""" -----------------------------------------------------
# TECHNOGIX
# -------------------------------------------------------
# Copyright (c) [2022] Technogix SARL
# All rights reserved
# -------------------------------------------------------
# Class to help management of gitlab by python
# Enable the setting of gitlab credentials in configuration
# file and ensure it will be removed for security
# -------------------------------------------------------
# Nadège LEMPERIERE, @04 october 2021
# Latest revision: 04 october 2021
# --------------------------------------------------- """

# System includes
from logging import getLogger
from subprocess import Popen, PIPE
from configparser import ConfigParser

# pylint: disable=R1732
class Gitlab :
    """ Class managing gitlab configuration to retrieve terraform module from their repositories
    """

    m_log                       = getLogger('gitlab')
    m_parser                    = None
    m_shall_remove_credentials  = False
    m_aws_token                 = None
    m_aws_password              = None
    m_github_token              = None
    m_github_password           = None

    def __init__(self) :
        """ Constructor
        """
        self.m_log                       = getLogger('gitlab')
        self.m_parser                    = ConfigParser()
        self.m_shall_remove_credentials  = False
        self.m_aws_token                 = None
        self.m_aws_password              = None
        self.m_github_token              = None
        self.m_github_password           = None

    def __del__(self):
        """ Destructor
        """

        self.m_log.info('-- Removing gitlab credentials')

        if self.m_shall_remove_credentials :
            if not self.remove_credentials() :
                raise Exception('Gitlab credential removal fails. \
                Check your configuration file to remove them manually')

# pylint: disable=C0321
    def configure(self, tokens) :
        """ Sets the credentials for gitlab
        ---
        token    (str) :  Gitlab token to use as https credentials
        password (str) : Password associated to the token
        """

        is_status_ok = True

        if 'aws_token' in tokens        : self.m_aws_token       = tokens['aws_token']
        if 'aws_password' in tokens     : self.m_aws_password    = tokens['aws_password']
        if 'github_token' in tokens     : self.m_github_token    = tokens['github_token']
        if 'github_password' in tokens  : self.m_github_password = tokens['github_password']

        return is_status_ok
# pylint: enable=C0321

    def set_credentials(self) :
        """ Sets the credentials in gitlab configuration files
        """

        is_status_ok = True

        try :

            if self.m_aws_password is not None and self.m_aws_token is not None :
                cmd = 'git config --global url."https://' + self.m_aws_token + \
                      ':' + self.m_aws_password + \
                      '@git-codecommit.eu-west-1.amazonaws.com".insteadOf ' + \
                      'https://git-codecommit.eu-west-1.amazonaws.com'
                self.m_shall_remove_credentials = True
                process = Popen(cmd, stdout=PIPE, shell=True)
                (output,err) = process.communicate()
                self.m_log.debug(output)
                if process.returncode > 0 :
                    self.m_log.error(err)
                    raise Exception('Gitlab configuration failed')

            if self.m_github_password is not None and self.m_github_token is not None :
                cmd = 'git config --global url."https://' + self.m_github_token + \
                      ':' + self.m_github_password + \
                      '@github.com".insteadOf https://github.com'
                self.m_shall_remove_credentials = True
                process = Popen(cmd, stdout=PIPE, shell=True)
                (output,err) = process.communicate()
                self.m_log.debug(output)
                if process.returncode > 0 :
                    self.m_log.error(err)
                    raise Exception('Gitlab configuration failed')

        except Exception as exc :
            self.m_log.error(str(exc))
            is_status_ok = False

        return is_status_ok


    def remove_credentials(self) :
        """ Remove credentials from configuration file
        """
        is_status_ok = True

        try :

            if self.m_aws_password is not None and self.m_aws_token is not None :
                cmd = 'git config --global --remove-section url."https://' + \
                      self.m_aws_token + ':' + self.m_aws_password + \
                      '@git-codecommit.eu-west-1.amazonaws.com"'
                process = Popen(cmd, stdout=PIPE, shell=True)
                (output,err) = process.communicate()
                self.m_log.debug(output)
                if process.returncode > 0 :
                    self.m_log.error(err)
                    raise Exception('Gitlab configuration failed')
                self.m_shall_remove_credentials = False

            if self.m_github_token is not None and self.m_github_password is not None :
                cmd = 'git config --global --remove-section url."https://' + \
                      self.m_github_token + ':' + self.m_github_password + \
                      '@github.com"'
                process = Popen(cmd, stdout=PIPE, shell=True)
                (output,err) = process.communicate()
                self.m_log.debug(output)
                if process.returncode > 0 :
                    self.m_log.error(err)
                    raise Exception('Gitlab configuration failed')
                self.m_shall_remove_credentials = False

        except Exception as exc :
            self.m_log.error(str(exc))
            is_status_ok = False

        return is_status_ok

# pylint: enable=R1732
