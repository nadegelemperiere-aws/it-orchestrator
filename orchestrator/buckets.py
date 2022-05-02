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
from os import path

# Aws includes
from boto3 import Session

# Local includes
from orchestrator.utils import load_and_parse_json_file

# Logging configuration
log = getLogger('buckets')

class Buckets :
    """ Class containing methods to manage S3 buckets """

    m_session = None
    m_client = None
    m_username = None
    m_password = None

    def __init__(self) :
        """ Constructor """
        self.m_session = None
        self.m_client = None
        self.m_ec2_client = None
        self.m_username = None
        self.m_password = None

# pylint: disable=C0301
    def configure(self, username, password, region) :
        """ Configure boto3 to use s3 functions
        ---
        username (str) : AWS access key to use to configure AWS
        password (str) : AWS secret key to use to configure AWS
        region   (str) : AWS region to work into
        """
        is_status_ok = True

        try :
            self.m_session = Session(aws_access_key_id=username, aws_secret_access_key=password, region_name=region)
            self.m_client = self.m_session.client('s3')
            self.m_ec2_client = self.m_session.client('ec2')
            self.m_username = username
            self.m_password = password

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0301

# pylint: disable=C0301, C0321
    def empty_buckets(self, state, account, principal) :
        """ Lock and empty an S3 bucket
        ---
        state     (str) : Terraform state file to retrieve buckets from
        account   (str) : AWS accounts in which buckets are located
        principal (str) : AWS user to limit bucket access to when locked
        """

        is_status_ok = True

        try :

            if is_status_ok : state_logging = load_and_parse_json_file(state)
            if is_status_ok : regions = self.m_ec2_client.describe_regions()

            if is_status_ok :
                for bucket in state_logging['outputs']['buckets']['value'] :
                    self.lock_bucket(state_logging['outputs']['buckets']['value'][bucket]['id'], account, principal)
                    for region in regions['Regions'] :
                        if is_status_ok : is_status_ok = self.empty_bucket(state_logging['outputs']['buckets']['value'][bucket]['id'], region['RegionName'])

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0301, C0321

# pylint: disable=C0301
    def lock_bucket(self, bucket, account, principal) :
        """ Lock bucket access by only allowing a single user
        ---
        bucket       (str) : Bucket to lock
        account      (str) : AWS accounts in which buckets are located
        principal    (str) : AWS user to limit bucket access to when locked
        """
        policy = '{"Version":"2012-10-17","Statement":[{"Sid":"AllowRootAndServicePrincipal","Effect":"Allow","Principal":{"AWS":["arn:aws:iam::' + account + ':user/' + principal + '","arn:aws:iam::' + account + ':root"]},"Action":"s3:*","Resource":["arn:aws:s3:::' + bucket + '/*","arn:aws:s3:::' + bucket +'"]}]}'
        self.m_client.put_bucket_policy(Bucket=bucket, Policy=policy)
# pylint: enable=C0301

# pylint: disable=C0301
    def empty_bucket(self, bucket, region) :
        """ Empty a bucket
        ---
        bucket       (str) : Bucket to lock
        region       (str) : Bucket region*
        """

        is_status_ok = True

        try :

            session = Session(aws_access_key_id=self.m_username, aws_secret_access_key=self.m_password, region_name=region)
            client = session.client('s3')

            paginator = client.get_paginator('list_object_versions')
            response_iterator = paginator.paginate(Bucket=bucket)
            for response in response_iterator :
                if 'Versions' in response :
                    for obj in response['Versions'] :
                        log.debug(obj['Key'])
                        self.m_client.delete_object(Bucket=bucket, Key=obj['Key'], VersionId=obj['VersionId'])
                if 'DeleteMarkers' in response :
                    for obj in response['DeleteMarkers'] :
                        log.debug(obj['Key'])
                        self.m_client.delete_object(Bucket=bucket, Key=obj['Key'], VersionId=obj['VersionId'])

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok
# pylint: enable=C0301

    def upload_states(self, files, state_file) :
        """ Upload states to an s3 bucket
        ---
        files       (str) : List of state files to upload
        state_file  (str) : Terraform state file from which bucket path shall be read
        """

        is_status_ok = True

        try :
             # Retrieve s3 backend configuration from state file
            state_backend = load_and_parse_json_file(state_file)
            bucket = state_backend['outputs']['buckets']['value']['backend']['id']
            s3_path = state_backend['outputs']['bucket_terraform_key']['value']

            log.debug('-------- Bucket : %s', bucket)
            log.debug('-------- Path : %s', path)

            # Upload existing states to s3 backend
            for file in files :
                target = s3_path + path.basename(file)
                self.m_client.upload_file(file, bucket, target)

        except Exception as exc :
            log.error(str(exc))
            is_status_ok = False

        return is_status_ok
