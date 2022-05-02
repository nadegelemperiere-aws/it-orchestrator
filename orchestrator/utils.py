""" -----------------------------------------------------
# TECHNOGIX
# -------------------------------------------------------
# Copyright (c) [2022] Technogix SARL
# All rights reserved
# -------------------------------------------------------
# Utils
# -------------------------------------------------------
# Nadège LEMPERIERE, @04 october 2021
# Latest revision: 04 october 2021
# --------------------------------------------------- """

from json import load, dump
from logging import getLogger

# Logging configuration
log = getLogger('utils')

# pylint: disable=C0301, C0321
def load_and_parse_json_file(filename, heading = '') :
    """ Load and parse a json file """

    log.debug(heading + 'Parsing file : ' + filename)
    result = {}

    with open(filename,'r', encoding='UTF-8') as fid:
        result = load(fid)

    return result

def dump_json_file(content, filename, heading = '') :
    """ Dump json to a file """

    log.debug(heading + 'Dumping to file : ' + filename)

    with open(filename,'w', encoding='UTF-8') as fid:
        dump(content,fid)

    fid.close()

def remove_type_from_dictionary(linput, ltype) :
    """ Remove all object of the given type from input dictonary """

    result = {}

    for key in linput.keys() :
        if isinstance(linput[key], ltype) : log.debug('Removing element %s from dict', key)
        elif isinstance(linput[key], dict) : result[key] = remove_type_from_dictionary(linput[key], ltype)
        elif isinstance(linput[key], list) : result[key] = remove_type_from_list(linput[key], ltype)
        else : result[key] = linput[key]

    return result

def remove_type_from_list(linput, ltype) :
    """ Test if spec list is included in test """

    result = []

    for item in linput :
        if isinstance(item, ltype) : log.debug('Removing element from list')
        elif isinstance(item, dict) : result.append(remove_type_from_dictionary(item, ltype))
        elif isinstance(item, list) : result.append(remove_type_from_list(item, ltype))
        else : result.append(item)


    return result
# pylint: enable=C0301, C0321
