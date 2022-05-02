""" -----------------------------------------------------
# TECHNOGIX
# -------------------------------------------------------
# Copyright (c) [2022] Technogix SARL
# All rights reserved
# -------------------------------------------------------
# Class to manage deployment secrets from keepass database
# -------------------------------------------------------
# Nadège LEMPERIERE, @17 october 2021
# Latest revision: 17 october 2021
# --------------------------------------------------- """

# System includes
from logging import getLogger
from os import path, makedirs, getenv
from json import dumps

# Pykeepass includes
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError

# Local includes
from orchestrator.utils import load_and_parse_json_file

# Logging configuration
log = getLogger('config')

# pylint: disable=C0301, C0321
class Configuration :
    """ Workflow configuration class"""

    m_configuration             = None
    m_configuration_path        = None

    m_keepass                   = None

    m_parameters                = None
    m_secrets                   = None
    m_non_secrets               = None
    m_paths                     = None
    m_workflows                 = None

    def __init__(self) :
        """ Constructor """

        self.m_configuration        = {}
        self.m_configuration_path   = None

        self.m_keepass              = None
        self.m_aws_ad_domain        = None
        self.m_aws_ad_password      = None

        self.m_parameters           = {}
        self.m_secrets              = {}
        self.m_non_secrets          = {}
        self.m_paths                = {}
        self.m_workflows            = {}

    def exists_in_parameters(self, topic) :
        """ Tests if parameters are given for a topic """

        result = (topic in self.m_parameters)

        return result

    def get_workflow(self, name) :
        """ Workflow accessor
        ---
        name    (str)  : Name of the workflow to retrieve
        ---
        Returns (dict) : Select workflow
        """

        result = ''
        if not name in self.m_workflows : raise Exception('Workflow ' + name + ' not found in configuration')
        result = self.m_workflows[name]

        return result

    def get_path(self, name) :
        """ Path accessor
        ---
        name    (str) : Name of the path to retrieve
        ---
        Returns (str) : Selected path
        """

        result = ''
        if not self.m_paths or not name in self.m_paths : raise Exception('Path ' + name + ' not found in configuration')
        result = self.m_paths[name]

        return result

    def get_subnets(self) :
        """ Subnets accessor
        ---
        Returns (list) : List of the deployment subnets
        """

        result = self.m_workflows['subnets']

        return result

    def get_parameter(self, topic):
        """ Parameters (secrets and non secrets) accessor
        ---
        topic   (str) : Topic from which parameters shall be retrieved
        ---
        Returns (dict) : Parameters for the selected topic
        """

        result = None

        if self.m_parameters and topic in self.m_parameters : result = self.m_parameters[topic]
        else : raise Exception('Configuration contains no topic ' + topic)

        return result

    def get_secrets(self, topic):
        """ Secrets accessor
        ---
        topic   (str) : Topic from which secrets shall be retrieved
        ---
        Returns (dict) : Secrets for the selected topic
        """

        result = None

        if self.m_secrets and topic in self.m_secrets : result = self.m_secrets[topic]
        else : raise Exception('Secrets contains no topic ' + topic)

        return result

    def get_non_secrets(self, topic):
        """ Non secrets accessor
        ---
        topic   (str) : Topic from which non secret parameters shall be retrieved
        ---
        Returns (dict) : Parameters for the selected topic
        """

        result = None

        if self.m_non_secrets and topic in self.m_non_secrets : result = self.m_non_secrets[topic]
        else : raise Exception('Non secrets contains no topic ' + topic)

        return result

    def load_file(self, filename, env) :
        """ Configure deployment from configuration file
        ---
        filename (str) : path to the json file containing configuration
        env      (str) : platform deployment stage to address
        """

        is_status_ok = True

        try :

            self.m_configuration_path = path.split(filename)[0]
            # Read json file
            self.m_configuration = load_and_parse_json_file(filename, '----- ')
            self.m_configuration['parameters']['environment'] = env

            if is_status_ok : is_status_ok = self.build_paths()
            if is_status_ok : is_status_ok = self.build_workflows()

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok

    def load_secrets(self, database, key) :
        """ Read deployment secrets from keepass database
        ---
        database (str) : The input keepass database to extract values from
        key      (str) : The input keepass database key file or master key
        """
        is_status_ok = True

        try:
            if path.isfile(key) :
                log.debug('Opening database with keyfile')
                self.m_keepass = PyKeePass(database, keyfile=key)
            else :
                log.debug('Opening database with master key in environment variable %s', key)
                self.m_keepass = PyKeePass(database, password=getenv(key))

        except CredentialsError as exc :
            log.error('Credentials error : %s',str(exc))
            is_status_ok = False
        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok

    def set_parameters(self, username = None) :
        """ Gather parameters from different sources
        ---
        username (str) : The user to retrieve aws access keys and secret keys from
        """

        is_status_ok = True

        try:

            # Reading aws credentials from database
            if username is not None :
                lpath = ['engineering-environment','aws','aws-' + username + '-access-key']
                entry = self.m_keepass.find_entries_by_path(lpath)
                if entry is None :
                    raise Exception('Entry ' + '/'.join(lpath) + ' not found')
                self.m_parameters['aws'] = {}
                self.m_parameters['aws']['username'] = getattr(entry,'username')
                self.m_parameters['aws']['password'] = getattr(entry,'password')
                self.m_secrets['aws'] = {}
                self.m_secrets['aws']['username'] = getattr(entry,'username')
                self.m_secrets['aws']['password'] = getattr(entry,'password')

            # Reading general parameters
            self.m_parameters['global'] = {}
            self.m_non_secrets['global'] = {}
            self.m_secrets['global'] = {}
            if 'parameters' in self.m_configuration :
                for key in self.m_configuration['parameters'] :
                    self.m_parameters['global'][key] = self.m_configuration['parameters'][key]
                    self.m_non_secrets['global'][key] = self.m_configuration['parameters'][key]

            # Load the workflow keys
            if 'keys' in self.m_workflows :
                for topic in self.m_workflows['keys'] :
                    if not topic in self.m_parameters : self.m_parameters[topic] = {}
                    if not topic in self.m_secrets : self.m_secrets[topic] = {}
                    if not topic in self.m_non_secrets : self.m_non_secrets[topic] = {}
                    for key in self.m_workflows['keys'][topic] :
                        if self.m_workflows['keys'][topic][key]['type'] == 'secret' :
                            self.m_parameters[topic][key] = self.read_secret(self.m_workflows['keys'][topic][key]['entry'])
                            self.m_secrets[topic][key] = self.read_secret(self.m_workflows['keys'][topic][key]['entry'])
                        elif self.m_workflows['keys'][topic][key]['type'] == 'value' :
                            self.m_parameters[topic][key] = self.m_workflows['keys'][topic][key]['value']
                            self.m_non_secrets[topic][key] = self.m_workflows['keys'][topic][key]['value']
                        elif self.m_workflows['keys'][topic][key]['type'] == 'file' :
                            self.m_parameters[topic][key] = self.read_file(self.m_configuration_path + '/' + self.m_workflows['keys'][topic][key]['name'])
                            self.m_non_secrets[topic][key] = self.read_file(self.m_configuration_path + '/' + self.m_workflows['keys'][topic][key]['name'])
                        else :  raise Exception('Unmanaged key type ' + self.m_workflows['keys'][topic][key]['type'] + ' for key ' + key)

        except CredentialsError as exc :
            log.error('Credentials error : %s',str(exc))
            is_status_ok = False
        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok

    def check(self) :
        """ Check configuration file stucture """

        is_status_ok = True

        try :
            # Look for mandatory variables
            if 'global'         not in self.m_parameters : raise Exception('Missing global parameters')
            if 'topic'          not in self.m_parameters['global'] : raise Exception('Missing topic in configuration file')
            if 'region'         not in self.m_parameters['global'] : raise Exception('Missing region in configuration file')
            if 'environment'    not in self.m_parameters['global'] : raise Exception('Missing environment in configuration file')
            if 'contact'        not in self.m_parameters['global'] : raise Exception('Missing contact in configuration file')

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok


    def build_paths(self) :
        """ Read paths from configuration file """

        result = True

        self.m_paths = {}

        if 'paths' in self.m_configuration :
            for pth in self.m_configuration['paths'] :
                self.m_paths[pth] = self.m_configuration_path + '/' + self.m_configuration['paths'][pth]

            if 'states' in self.m_configuration['paths'] and not path.exists(self.m_configuration['paths']['states']) :
                makedirs(self.m_configuration['paths']['states'])

        return result

# pylint: disable=W0612
    def build_workflows(self) :
        """ Build workflows from configuration """

        result = True

        self.m_workflows = {}

        if 'workflows' in self.m_configuration :

            # If a value ends with .json, replace the value by the file content
            for key in self.m_configuration['workflows'] :
                if  self.m_configuration['workflows'][key].find('.json') == len(self.m_configuration['workflows'][key]) - 5 and \
                    self.m_configuration['workflows'][key].find('.json') > 0 :
                    self.m_workflows[key] = load_and_parse_json_file(self.m_configuration_path + '/' + self.m_configuration['workflows'][key], '----- ')

            if not 'keys'           in self.m_workflows : raise Exception('Missing keys in configuration file')
            if not 'subnets'        in self.m_workflows : raise Exception('Missing subnets in configuration file')
            if not 'deployment'     in self.m_workflows : raise Exception('Missing deployment workflow in configuration file')
            if not 'destruction'    in self.m_workflows : raise Exception('Missing destruction workflow in configuration file')

            for topic in self.m_workflows['subnets'] :
                for key in self.m_workflows['subnets'][topic] :
                    i_subnet = -1
                    for subnet in self.m_workflows['subnets'][topic][key] :
                        i_subnet = i_subnet + 1
                        if 'parameters' in self.m_configuration and 'region' in self.m_configuration['parameters'] :
                            self.m_workflows['subnets'][topic][key][i_subnet]['region'] = self.m_configuration['parameters']['region']

        return result
# pylint: enable=W0612

    def read_secret(self, key) :
        """ Read secrets in keepass from either a key or a list of keys
        ---
        key (list) : List of keys to retrieve. Each key is given by a dictionary
                     setting the keepass entry name (key) and the keepass entry
                     feature (feature) to retrieve in entry
        ---
        returns    : If the key is a list, then the result is a list of all retrieved values.
                     If it is a single value, then the result is a single value
        """

        result = None

        if isinstance(key, list) :
            result = []
            for keepass_path in key :
                if 'key' in keepass_path and 'feature' in keepass_path :
                    data = self.m_keepass.find_entries_by_path(keepass_path['key'].split('/'))
                    if data is None : raise Exception('Entry ' + keepass_path['key'] + ' not found in keepass')
                    result.append(getattr(data,keepass_path['feature']))
                else : raise Exception('Invalid key : ' + dumps(keepass_path))
        elif isinstance(key, dict) and 'key' in key and 'feature' in key:
            data = self.m_keepass.find_entries_by_path(key['key'].split('/'))
            if data is None : raise Exception('Entry ' + key['key'] + ' not found')
            result = getattr(data, key['feature'])
        else :   raise Exception('Unmanaged name format for key secret ' + key)

        return result

# pylint: disable=R0201
    def read_file(self, filename) :
        """ Read parameters in json files from either a file or a list of files
        ---
        filename (str) : The file to read
        ---
        returns        : If the filename is a list, then the result is a list of all retrieved
                         values. If it is a single value, then the result is a single value
        """
        result = None

        # Load the keys that are files
        if isinstance(filename, list) :
            result = []
            for file in filename:
                result.append(load_and_parse_json_file(file))
        elif isinstance(filename, str) :
            result = load_and_parse_json_file(filename)
        else :   raise Exception('Unmanaged name format for key file ' + filename)

        return result
# pylint: enable=C0301, C0321, R0201
