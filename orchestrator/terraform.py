""" -----------------------------------------------------
# TECHNOGIX
# -------------------------------------------------------
# Copyright (c) [2022] Technogix SARL
# All rights reserved
# -------------------------------------------------------
# Class to help management of terraform by python
# -------------------------------------------------------
# Nadège LEMPERIERE, @04 october 2021
# Latest revision: 04 october 2021
# --------------------------------------------------- """

# System includes
from logging import getLogger
from os import path, remove
from shutil import rmtree
from subprocess import Popen, PIPE
from json import dumps
from functools import reduce
from operator import add

# Logging configuration
log = getLogger('terraform')

class Terraform :
    """ Class managing terraform application """

    m_region = None

    m_access_key = None
    m_secret_key = None

    def __init__(self):
        """ Constructor """
        self.m_region = None
        self.m_access_key = None
        self.m_secret_key = None

    def configure(self, access_key, secret_key, region) :
        """ Configure terraform AWS credentials
        ---
        access_key      (str)  : AWS access key to use for this deployment
        secret_key      (str)  : AWS secret key to use for this deployment
        region          (str)  : AWS region in which the deployment shall occur
        """

        is_status_ok = True

        try :
            self.m_region = region
            self.m_access_key = access_key
            self.m_secret_key = secret_key
        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok

    def create_configuration_file(self, output_file, variables) :
        """ Create terraform configuration file from a list of variables to write
        ---
        output_file (str)  : The configuration file enriched with external or secret parameters
        variables   (dict) : The list of variables (key and value) to add to the configuration file
        """

        is_status_ok = True

        try :

            configuration = reduce(add, self.recurse(variables), "")
            log.info("-------- Writing terraform configuration file %s", output_file)
            log.debug(dumps(configuration))

            with open(output_file,'w', encoding='UTF-8') as configuration_fid:
                configuration_fid.write(configuration)

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok

# pylint: disable=C0301, W0102, R0913, R0914, C0321, R1732
    def apply(self, directory, state, bucket, region, configuration, variables = {}, backend='local') :
        """ Initialize, plan and apply terraform on a given configuration
        ---
        directory     (str) : Working directory for terraform
        state         (str) : State file to use for storage (filename for local backend, s3 object name with path for s3 backend )
        region        (str) : Deployment region for backend configuration
        configuration (str) : Configuration file to use for terraform configuration (tfvars)
        variables     (str) : Additional variables to set via command line (secrets)
        backend       (str) : Local or s3 (shall match the terraform jobs configuration)
        """
        is_status_ok = True

        try :

            other_parameters = ''
            for key in variables :
                other_parameters = other_parameters + ' -var="' + key + '=' + variables[key] + '"'

            tf_data_dir = directory + '/.terraform'
            if path.exists(tf_data_dir) : rmtree(tf_data_dir)
            if path.exists(tf_data_dir + '.lock.hcl') : remove(tf_data_dir + '.lock.hcl')

            log.info("-------- Initializing terraform for backend %s", backend)
            if backend == 'local' :
                cmd = 'terraform init -input=false -backend-config="path=' + state + '"'
            elif backend == 's3' :
                cmd = 'terraform init -input=false -backend-config="bucket=' + bucket + ' -backend-config="key=' + state + '" -backend-config="region=' + region + '""'
            else : raise Exception('Unmanaged backend type ' + backend)
            log.debug('-------- Command : %s', cmd)
            process = Popen(cmd, cwd=directory, stdout=PIPE, shell=True)
            (output,err) = process.communicate()
            log.debug(output)
            if process.returncode > 0 :
                log.error(err)
                raise Exception('Initialization failed')

            log.info("-------- Planning deployment")
            cmd = 'terraform plan -no-color -out=tfplan -input=false -var-file=' + configuration + ' -var="region=' + self.m_region + '" -var="access_key=' + self.m_access_key + '" -var="secret_key=' + self.m_secret_key + '" -state=' + state + other_parameters
            log.debug('-------- Command : %s', cmd)
            process = Popen(cmd, cwd=directory, stdout=PIPE, shell=True)
            (output,err) = process.communicate()
            log.debug(output)
            if process.returncode > 0 :
                log.error(err)
                raise Exception('Planification failed')

            log.info("-------- Executing deployment")
            # Parallelism is set to one to avoid issues when creating acl rules with count.
            cmd = 'terraform apply -no-color -input=false tfplan'
            log.debug('---- Command : %s', cmd)
            process = Popen(cmd , cwd=directory, stdout=PIPE, shell=True)
            (output,err) = process.communicate()
            log.debug(output)
            if process.returncode > 0 :
                log.error(err)
                raise Exception('Application failed')

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0301, W0102, R0913, R0914, C0321, R1732

# pylint: disable=C0301, C0321, W0102, R0913, R0914, R1732
    def destroy(self, directory, state, bucket, region, configuration, variables = {}, backend='local') :
        """ Destroy an existing configuration
        ---
        directory     (str) : Working directory for terraform
        state         (str) : State file to use for storage (filename for local backend, s3 object name with path for s3 backend )
        region        (str) : Deployment region for backend configuration
        configuration (str) : Configuration file to use for terraform configuration (tfvars)
        variables     (str) : Additional variables to set via command line (secrets)
        backend       (str) : Local or s3 (shall match the terraform jobs configuration)
        """

        is_status_ok = True

        try :
            tf_data_dir = directory + '/.terraform'
            if path.exists(tf_data_dir) : rmtree(tf_data_dir)
            if path.exists(tf_data_dir + '.lock.hcl') : remove(tf_data_dir + '.lock.hcl')

            other_parameters = ''
            for key in variables :
                other_parameters = other_parameters + ' -var="' + key + '=' + variables[key] + '"'

            log.info("-------- Initializing terraform for backend %s", backend)
            if backend == 'local' :
                cmd = 'terraform init -input=false -backend-config="path=' + state + '"'
            elif backend == 's3' :
                cmd = 'terraform init -input=false -backend-config="bucket=' + bucket + ' -backend-config="key=' + state + '" -backend-config="region=' + region + '""'
            else : raise Exception('Unmanaged backend type ' + backend)
            log.debug('-------- Command : %s', cmd)
            process = Popen(cmd, cwd=directory, stdout=PIPE, shell=True)
            (output,err) = process.communicate()
            log.debug(output)
            if process.returncode > 0 :
                log.error(err)
                raise Exception('Initialization failed')

            log.info("-------- Destroying deployment")
            cmd = 'terraform destroy -no-color -input=false --auto-approve -var-file=' + configuration + ' -var="region=' + self.m_region + '" -var="access_key=' + self.m_access_key + '" -var="secret_key=' + self.m_secret_key + '" -state=' + state + other_parameters
            log.debug('-------- Command : %s', cmd)
            process = Popen(cmd, cwd=directory, stdout=PIPE, shell=True)
            (output,err) = process.communicate()
            log.debug(output)
            if process.returncode > 0 :
                log.error(err)
                raise Exception('Destruction failed')

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0301, C0321, W0102, R0913, R0914, R1732

# pylint: disable=C0321
    def recurse(self, item, level=0):
        """ Recurse function to create terraform variables from dictionary
        ---
        item  (any) : Json item to transform into terraform lnguage
        level (int) : tree level to which item belong
        """
        if isinstance(item, dict):
            if level > 0: yield "{"

            for key, value in item.items():
                yield "\n"
                yield 4 * level * " "
                yield f'{key} = '

                for token in self.recurse(value, level=level+1): yield token

            if level > 0:
                yield "\n"
                yield 4 * (level-1) * " "
                yield "}"

        elif isinstance(item, list):
            if level > 0: yield "["

            for index, value in enumerate(item):
                yield "\n"
                yield 4 * level * " "

                for token in self.recurse(value, level=level+1): yield token

                if index < len(item) - 1: yield ","

            if level > 0:
                yield "\n"
                yield 4 * (level-1) * " "
                yield "]"

        elif isinstance(item, bool) : yield "true" if item else "false"

        else : yield f'"{item}"'

        if level-1 == 0: yield "\n"
# pylint: enable=C0321
