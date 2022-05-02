""" -----------------------------------------------------
# TECHNOGIX
# -------------------------------------------------------
# Copyright (c) [2022] Technogix SARL
# All rights reserved
# -------------------------------------------------------
# Class to manage workmail using boto3
# -------------------------------------------------------
# Nadège LEMPERIERE, @17 october 2021
# Latest revision: 17 october 2021
# --------------------------------------------------- """

# System includes
from logging import getLogger
from json import dumps

# ip address manipulation
from ipaddress import IPv4Network

# Aws includes
from boto3 import Session

# Local includes
from orchestrator.utils import load_and_parse_json_file

# Logging configuration
log = getLogger('networks')

# pylint: disable=C0301, R0913, R1702, C0321, R0914
class Networks :
    """ Networks CIDR range allocation class"""

    m_session = None
    m_client = None
    m_subnets = {}
    m_shall_destroy = None

    def __init__(self) :
        """ Constructor """
        self.m_session = None
        self.m_client = None
        self.m_subnets = {}
        self.m_shall_destroy = None

    def configure(self, username, password, region, shall_destroy, subnets) :
        """ Configure boto3 to use s3 functions
        ---
        username      (str)  : AWS access key to use to configure AWS
        password      (str)  : AWS secret key to use to configure AWS
        region        (str)  : AWS region to work into
        shall_destroy (bool) : True of deployment shall be destroyed, false otherwise
        subnets       (list) : List of subnets with their required masks
        """
        is_status_ok = True

        try :
            self.m_session = Session(aws_access_key_id=username, aws_secret_access_key=password, region_name=region)
            self.m_client = self.m_session.client('ec2', region_name=region)
            self.m_subnets = subnets
            self.m_shall_destroy = shall_destroy

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok

    def exists(self, topic) :
        """ Tests if a subnet is allocated to a given topic
        ---
        topic   (str)  : Topic to check
        ---
        Returns (bool) : True if a subnet is required for topic, false otherwise
        """

        result = (topic in self.m_subnets)

        return result

    def get(self, topic) :
        """ Returns subnet for a given topic
        ---
        topic   (str)  : Topic to check
        ---
        returns (dict) : Subnets with name, mask, cidr range and region
        """

        result = {}

        if not topic in self.m_subnets : raise Exception('Topic ' + topic + ' not found in subnets')
        for key in self.m_subnets[topic] :
            result[key] = []
            for subnet in self.m_subnets[topic][key] :
                if not 'cidr' in subnet : raise Exception('No cidr defined for network ' + subnet['name'] + ' in variable ' + key + ' for topic ' + topic)
                result[key].append({'name':subnet['name'],'cidr':subnet['cidr'],'region':subnet['region'] + subnet['subregion']})

        return result


    def compute(self, filename) :
        """ Compute CIDR ranges for subnets described in the provided file
        ---
        filename (str) : Filename describing subnets requirements
        """

        is_status_ok = True

        try :
            if is_status_ok : state = load_and_parse_json_file(filename)

            # Check what to do depending on state and mode
            if is_status_ok and len(state['outputs']) == 0 and self.m_shall_destroy :
                log.info('-------- Network structure already removed - Do nothing')
            elif is_status_ok and 'vpc' not in state['outputs'] :
                raise Exception('Network has not been created yet')
            else :

                # Retrieve network configuration from state file
                vpccidr = IPv4Network(state['outputs']['vpc']['value']['cidr'])
                vpcid = state['outputs']['vpc']['value']['id']

                # Retrieve all cidr in use in current vpc
                response = self.m_client.describe_subnets(Filters=[{'Name': 'vpc-id','Values': [vpcid]}])
                for topic in self.m_subnets :
                    for variable in self.m_subnets[topic] :
                        i_subnet = -1
                        for subnet in self.m_subnets[topic][variable] :
                            i_subnet = i_subnet + 1
                            found = False

                            # Checking if the subnet already exist
                            for sub in response['Subnets'] :
                                for tag in sub['Tags'] :
                                    if tag['Key'] == 'DeployIdentifier' and tag['Value'] == subnet['name'] and subnet['mask'] == int(sub['CidrBlock'].split('/')[1]) :
                                        self.m_subnets[topic][variable][i_subnet]['cidr'] = sub['CidrBlock']
                                        log.debug('---- Already allocated to cidr %s',sub['CidrBlock'])
                                        found = True

                            # If not, look to book a valid range
                            for candidate in list(vpccidr.subnets(new_prefix=subnet['mask'])) :
                                if not found :
                                    is_valid = True
                                    # Check if range already exist in AWS
                                    for sub in response['Subnets'] :
                                        if candidate.overlaps(IPv4Network(sub['CidrBlock'])) : is_valid = False
                                    # Check if range has not already been associated to another subnet
                                    for top in self.m_subnets :
                                        for var in self.m_subnets[top] :
                                            for sub in self.m_subnets[top][var] :
                                                if 'cidr' in sub and candidate.overlaps(IPv4Network(sub['cidr'])) : is_valid = False
                                    if is_valid :
                                        self.m_subnets[topic][variable][i_subnet]['cidr'] = str(candidate)
                                        log.debug('---- Reserving cidr %s',str(candidate))
                                        found = True

                log.debug(dumps(self.m_subnets))

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0301, R0913, R1702, C0321, R0914
