""" -----------------------------------------------------
# TECHNOGIX
# -------------------------------------------------------
# Copyright (c) [2022] Technogix SARL
# All rights reserved
# -------------------------------------------------------
# Common deployment for technogix secured infrastructure
# Deployment orchestration
# -------------------------------------------------------
# Nadège LEMPERIERE, @04 october 2021
# Latest revision: 04 october 2021
# --------------------------------------------------- """

# System includes
from logging import config, getLogger
from os import path
from sys import path as syspath
from glob import glob

# local includes
from orchestrator.terraform import Terraform
from orchestrator.gitlab import Gitlab
from orchestrator.groups import Group
from orchestrator.config import Configuration
from orchestrator.networks import Networks
from orchestrator.buckets import Buckets

syspath.append(path.normpath(path.join(path.dirname(__file__), './')))

class Orchestrator :
    """ Generic orchestrator class
    """

    m_log                       = getLogger('orchestrator')
    m_workflow                  = None
    m_s3_backend_bucket         = None
    m_s3_backend_path           = None
    m_s3_backend_region         = None
    m_terraform                 = None
    m_gitlab                    = None
    m_group                     = None
    m_configuration             = None
    m_networks                  = None
    m_buckets                   = None
    m_shall_release_credentials = False
    m_shall_destroy             = False
    m_git_version               = 'unmanaged'

    def __init__(self, version = 'unmanaged') :
        """ Constructor
        ----------
        version      (str)  : Repository version associated to the deployment to be set as tag
        """

        self.m_log                          = getLogger('orchestrator')
        self.m_git_version                  = version
        self.m_s3_backend_bucket            = None
        self.m_s3_backend_path              = None
        self.m_s3_backend_region            = None
        self.m_shall_destroy                = False
        self.m_shall_release_credentials    = False
        self.m_terraform                    = Terraform()
        self.m_gitlab                       = Gitlab()
        self.m_group                        = Group()
        self.m_configuration                = Configuration()
        self.m_networks                     = Networks()
        self.m_buckets                      = Buckets()

# pylint: disable=R0201
    def configure_logging(self, filename) :
        """ Configure logging from file
        ----------
        filename      (str)  : Path to the logging configuration file
        """

        is_status_ok = True

        try :
            config.fileConfig(filename)
            self.m_log = getLogger('orchestrator')

        except Exception as exc :
            self.m_log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=R0201

# pylint: disable=C0321
    def configure(self, filename, env, shall_destroy = False) :
        """ Configure deployment from configuration file
        ----------
        filename      (str)  : Path to the json file containing configuration
        env           (str)  : Deployment target environment (prod / preprod / staging / dev / ....)
        shall_destroy (bool) : True if the desployment shall be destroyed rather than created
        """

        is_status_ok = True

        try :
            if is_status_ok : is_status_ok = self.m_configuration.load_file(filename, env)

            # Define the workflow to use for the current processing
            self.m_shall_destroy = shall_destroy
            if is_status_ok and self.m_shall_destroy    :
                self.m_workflow = self.m_configuration.get_workflow('destruction')
            elif is_status_ok                           :
                self.m_workflow = self.m_configuration.get_workflow('deployment')

        except Exception as exc :
            self.m_log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0321

# pylint: disable=C0321, C0301, R0912
    def initialize(self, aws_username = None) :
        """ Prepare for workflow execution
        ---
        aws_username (str) : Identifier of the vault entry in which AWS credentials to use for
                             deployment are set (under aws-<username>-access-key entry)
        """

        is_status_ok = True
        username = ''
        password = ''
        region = ''

        try :
            if is_status_ok : self.m_log.debug('------- Retrieving all parameters from sources')
            if is_status_ok : is_status_ok = self.m_configuration.set_parameters(aws_username)
            if is_status_ok : is_status_ok = self.m_configuration.check()

            if is_status_ok : self.m_log.debug('------- Setting gitlab credentials for terraform modules')
            if is_status_ok : is_status_ok = self.m_gitlab.configure( \
                self.m_configuration.get_parameter('git'))
            if is_status_ok : is_status_ok = self.m_gitlab.set_credentials()
            if is_status_ok : self.m_log.debug('------- Successfully set gitlab credentials')

            if is_status_ok : self.m_log.debug('------- Initializing generic steps')
            if is_status_ok : username = self.m_configuration.get_parameter('aws')['username']
            if is_status_ok : password = self.m_configuration.get_parameter('aws')['password']
            if is_status_ok : region = self.m_configuration.get_parameter('global')['region']
            if is_status_ok : is_status_ok = self.m_networks.configure(username, password, region, self.m_shall_destroy, self.m_configuration.get_subnets())
            if is_status_ok : is_status_ok = self.m_buckets.configure(username, password, region)
            if is_status_ok : is_status_ok = self.m_terraform.configure(username, password, region)

        except Exception as exc :
            self.m_log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0321, C0301, R0912

# pylint: disable=C0321, C0301
    def empty_buckets(self, step, state) :
        """ Empty all the s3 buckets mentioned in the terraform state file under the "bucket" output
        ---
        step       (str) : unused parameter - for method genericity
        state      (str) : terraform state file to get s3 backend coordinates from
        """
        is_status_ok = True

        try :
            if is_status_ok : env = self.m_configuration.get_parameter('global')['environment']
            if is_status_ok : filename = self.m_configuration.get_path('states') + '/' + state + '.' + env + '.tfstate'
            if is_status_ok : is_status_ok = self.m_buckets.empty_buckets(filename, self.m_configuration.get_parameter('global')['account'], self.m_configuration.get_parameter(step)['service_principal'])

        except Exception as exc :
            self.m_log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0321, C0301

# pylint: disable=C0321, W0613, C0301
    def copy_states_to_backend(self, step, state) :
        """ Copy states to remote backend after deployment is over
        ---
        step       (str) : unused parameter - for method genericity
        state      (str) : terraform state file to get s3 backend coordinates from
        """

        is_status_ok = True

        try :
            # Retrieve s3 backend configuration from state file

            if is_status_ok : env = self.m_configuration.get_parameter('global')['environment']
            if is_status_ok : backend_file = self.m_configuration.get_path('states') + '/' + state + '.' + env + '.tfstate'
            if is_status_ok and path.isfile(backend_file) :
                if is_status_ok : files = glob(self.m_configuration.get_path('states') + '/*.tfstate')
                if is_status_ok : is_status_ok = self.m_buckets.upload_states(files, backend_file)
                if is_status_ok : files = glob(self.m_configuration.get_path('states') + '/*.json')
                if is_status_ok : is_status_ok = self.m_buckets.upload_states(files, backend_file)

        except Exception as exc :
            self.m_log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0321, W0613, C0301

# pylint: disable=C0321, W0613, C0301
    def define_networks(self, step) :
        """ Allocate all the cidr ranges to the infrastructure subnets
        ---
        step       (str) : unused parameter - for method genericity
        """

        is_status_ok = True

        try :
            if is_status_ok : env = self.m_configuration.get_parameter('global')['environment']
            if is_status_ok : state_file = self.m_configuration.get_path('states') + '/' + self.m_workflow['network']['tasks'][0]['state'] + '.' + env + '.tfstate'
            if is_status_ok : is_status_ok = self.m_networks.compute(state_file)

        except Exception as exc :
            self.m_log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0321, W0613, C0301

# pylint: disable=R0912, C0321, C0301
    def terraform(self, step_path, state, topic, backend='local') :
        """ Apply a terraform task
        ---
        step_path  (str) : Path in which terraform files are located
        state      (str) : Name of the state file to create from deployment
        topic      (str) : Name of the module associated to the task (to be provided to terraform)
        backend    (str) : Backend type to use for the task (local or s3)
        """

        is_status_ok = True

        try :
            # Create terraform configuration file
            keys = {}
            secrets = {}

            # Add common keys
            if is_status_ok : keys['environment'] = self.m_configuration.get_parameter('global')['environment']
            if is_status_ok : keys['contact_email'] = self.m_configuration.get_parameter('global')['contact']
            if is_status_ok : keys['topic'] = self.m_configuration.get_parameter('global')['topic']
            if is_status_ok : keys['git_version'] = self.m_git_version
            if is_status_ok : keys['module'] = topic

            # Add specific keys from configuration
            if is_status_ok and self.m_configuration.exists_in_parameters(topic) : secrets = self.m_configuration.get_secrets(topic)

            if is_status_ok and self.m_configuration.exists_in_parameters(topic) : keys.update(self.m_configuration.get_non_secrets(topic))
            if is_status_ok and self.m_networks.exists(topic) : keys.update(self.m_networks.get(topic))

            if is_status_ok : output_file = self.m_configuration.get_path('terraform') + '/' + step_path + '/conf.tfvars'
            if is_status_ok : step_dir = self.m_configuration.get_path('terraform') + '/' + step_path
            if is_status_ok : is_status_ok = self.m_terraform.create_configuration_file(output_file, keys)

            # Use terraform
            if is_status_ok and backend == 'local' :
                state_file = self.m_configuration.get_path('states') + '/' + state + '.' + keys['environment'] + '.tfstate'
            elif is_status_ok and backend == 's3' :
                state_file = self.m_s3_backend_path + state + '.' + keys['environment'] + '.tfstate'
            elif is_status_ok : raise Exception('Unmanaged backend type {backend}')

            if not self.m_shall_destroy and is_status_ok :
                is_status_ok = self.m_terraform.apply(step_dir, state_file, self.m_s3_backend_bucket, self.m_s3_backend_region, output_file, variables = secrets, backend = backend)
            elif is_status_ok :
                is_status_ok = self.m_terraform.destroy(step_dir, state_file, self.m_s3_backend_bucket, self.m_s3_backend_region, output_file, variables = secrets, backend = backend)

        except Exception as exc :
            self.m_log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=R0912, C0321, C0301

# pylint: disable=C0321, C0301
    def apply_task(self, task, step) :
        """ Apply a task in workflow
        ---
        task       (str) : Name of the task to perform
        step       (str) : Name of the step to which the task belong
        """

        is_status_ok = True

        try:
            configuration_key = step
            if 'key' in task : configuration_key = task['key']

            if task['type'] == 'terraform' :
                if is_status_ok : is_status_ok = self.terraform(task['path'], task['state'], configuration_key)
            elif task['type'] == 'python' :
                func = getattr(self,task['method'])
                if is_status_ok : is_status_ok = func(step, **task['args'])
            else : raise Exception('Unmanaged task type ' + task['type'])

        except Exception as exc :
            self.m_log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0321, C0301

# pylint: disable=R1702, R0912, C0321, C0301
    def workflow(self, database, key, steps, username = None) :
        """ Apply the workflow specified in the configuration file
        ---
        database   (str) : Path to the keepass database in which secrets are stored
        key        (str) : Vault key file or name of the environment variable in which vault key is stored
        steps      (str) : List of the steps to apply (empty if all steps shall be applied)
        username   (str) : Identifier of the vault entry in which AWS credentials to use for deployment are set (under aws-<username>-access-key entry)
        """

        is_status_ok = True

        try :

            i_step = 2
            if is_status_ok : self.m_log.info('-- %d   - Extracting secrets from database %s', i_step, database) ; i_step = i_step + 1
            if is_status_ok : is_status_ok = self.m_configuration.load_secrets(database, key)

            if is_status_ok : self.m_log.info('-- %d   - Initializing deployment workflow', i_step) ; i_step = i_step + 1
            if is_status_ok : is_status_ok = self.initialize(username)

            for step in self.m_workflow :

                is_mandatory = True in [('mandatory' in task and task['mandatory']) for task in self.m_workflow[step]['tasks']] # One of the task is mandatory
                shall_apply_step = (len(steps) == 0) or (step in steps) or is_mandatory

                if shall_apply_step :

                    suffix = ''
                    if is_mandatory : suffix = '[mandatory]'
                    if is_status_ok : self.m_log.info('-- %d   - %s %s', i_step, self.m_workflow[step]['description'], suffix); i_step = i_step + 1

                    j_step = 1
                    for task in self.m_workflow[step]['tasks'] :

                        shall_apply_task = (len(steps) == 0) or (step in steps) or (is_mandatory and 'mandatory' in task and task['mandatory'])
                        if shall_apply_task :

                            if is_status_ok : self.m_log.info('-- %d.%d - %s %s', i_step - 1, j_step, task['description'], suffix) ; j_step = j_step + 1
                            if is_status_ok : is_status_ok = self.apply_task(task, step)



        except Exception as exc :
            self.m_log.error(str(exc))
            is_status_ok = False

        return is_status_ok

# pylint: enable=R1702, R0912, C0321, C0301
