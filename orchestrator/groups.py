""" -----------------------------------------------------
# TECHNOGIX
# -------------------------------------------------------
# Copyright (c) [2022] Technogix SARL
# All rights reserved
# -------------------------------------------------------
# Class to help management of groups by python
# -------------------------------------------------------
# Nadège LEMPERIERE, @04 october 2021
# Latest revision: 04 october 2021
# --------------------------------------------------- """

# System includes
from logging import getLogger
from os import path

# Aws includes
from boto3 import Session

# Local includes
from orchestrator.utils import load_and_parse_json_file, dump_json_file

# Logging configuration
log = getLogger('groups')

# pylint: disable=R0903
class Group :
    """ Workmail groups management class """

# pylint: disable=C0301, R0913, C0321, R0201
    def create_directory_group(self, group_name, organization, groups_filename, username, password, region) :
        """ Create a new group in a directory if it does not exists
        ----------
        group_name      (str) : Name of the group to create
        organization    (str) : Identifier of the organization in which the group shall be created
		groups_filename (str) : Filename of the list of groups to update with the new one id
        """
        is_status_ok = True

        try :

            log.debug('---- Opening workmail session')
            workmail_session = Session(aws_access_key_id=username, aws_secret_access_key=password)
            workmail_client = workmail_session.client('workmail', region_name=region)

            shall_create = True
            response = workmail_client.list_groups(OrganizationId = organization)
            for grp in response['Groups'] :
                if grp['Name'] == group_name : shall_create = False

            if not shall_create : log.info('---- Group already exists')
            else :

                log.info('---- Creating group')

                # Retrieve groups configuration from state file
                result = {}
                if path.isfile(groups_filename) :
                    log.debug('---- loading groups from %s', groups_filename)
                    result = load_and_parse_json_file(groups_filename)

                response = workmail_client.create_group(OrganizationId=organization, Name=group_name)
                # result['organisation'] = response['OrganizationId']
                result[group_name] = response['GroupId']

                dump_json_file(result, groups_filename)

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0301, R0913, C0321, R0201
# pylint: enable=R0903
