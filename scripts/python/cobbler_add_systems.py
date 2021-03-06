#!/usr/bin/env python
# Copyright 2016 IBM Corp.
#
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import nested_scopes, generators, division, absolute_import, \
    with_statement, print_function, unicode_literals
import sys
import xmlrpclib

from lib.inventory import Inventory
from lib.logger import Logger

COBBLER_USER = 'cobbler'
COBBLER_PASS = 'cobbler'

YAML_HOSTNAME = 'hostname'
YAML_IPV4_IPMI = 'ipv4-ipmi'
YAML_USERID_IPMI = 'userid-ipmi'
YAML_PASSWORD_IPMI = 'password-ipmi'
YAML_IPV4_PXE = 'ipv4-pxe'
YAML_MAC_PXE = 'mac-pxe'
YAML_CHASSIS_PART_NUMBER = 'chassis-part-number'
YAML_CHASSIS_SERIAL_NUMBER = 'chassis-serial-number'
YAML_MODEL = 'model'
YAML_SERIAL_NUMBER = 'serial-number'
INV_TEMPLATE = 'template'

CFG_NODES_TEMPLATES = 'node-templates'
CFG_COBBLER_PROFILE = 'cobbler-profile'
YAML_COBBLER_PROFILE = 'cobbler-profile'
CFG_OS_DISK = 'os-disk'
YAML_ARCH = 'architecture'
COBBLER_PROFILE_X86_64 = 'ubuntu-14.04.4-server-amd64'
COBBLER_PROFILE_PPC64 = 'ubuntu-14.04.4-server-ppc64el'


class CobblerAddSystems(object):
    def __init__(self, log_level, inv_file, cfg_file):
        log = Logger(__file__)
        if log_level is not None:
            log.set_level(log_level)

        cobbler_server = xmlrpclib.Server("http://127.0.0.1/cobbler_api")
        token = cobbler_server.login(COBBLER_USER, COBBLER_PASS)

        inv = Inventory(log_level, inv_file, cfg_file)

        for node_inv, INV_NODES, key, index, node in inv.yield_nodes():
            hostname = node[YAML_HOSTNAME]
            ipv4_ipmi = node[YAML_IPV4_IPMI]
            userid_ipmi = node[YAML_USERID_IPMI]
            password_ipmi = node[YAML_PASSWORD_IPMI]
            ipv4_pxe = node[YAML_IPV4_PXE]
            mac_pxe = node[YAML_MAC_PXE]

            if YAML_COBBLER_PROFILE in node:
                COBBLER_PROFILE = \
                    node[YAML_COBBLER_PROFILE]
            elif (CFG_COBBLER_PROFILE in
                    inv.cfg[CFG_NODES_TEMPLATES][node[INV_TEMPLATE]]):
                COBBLER_PROFILE = \
                    (inv.cfg[CFG_NODES_TEMPLATES][node[INV_TEMPLATE]]
                            [CFG_COBBLER_PROFILE])
            elif (YAML_ARCH in node and
                    node[YAML_ARCH] is not None):
                if node[YAML_ARCH].lower() == 'x86_64':
                    COBBLER_PROFILE = COBBLER_PROFILE_X86_64
                elif node[YAML_ARCH].lower() == 'ppc64':
                    COBBLER_PROFILE = COBBLER_PROFILE_PPC64
                else:
                    log.log_error(
                        'Inventory: Invalid architecture set for %s' %
                        hostname)
            else:
                COBBLER_PROFILE = COBBLER_PROFILE_X86_64

            new_system_create = cobbler_server.new_system(token)

            cobbler_server.modify_system(
                new_system_create,
                "name",
                hostname,
                token)
            cobbler_server.modify_system(
                new_system_create,
                "hostname",
                hostname,
                token)
            cobbler_server.modify_system(
                new_system_create,
                "power_address",
                ipv4_ipmi,
                token)
            cobbler_server.modify_system(
                new_system_create,
                "power_user",
                userid_ipmi,
                token)
            cobbler_server.modify_system(
                new_system_create,
                "power_pass",
                password_ipmi,
                token)
            cobbler_server.modify_system(
                new_system_create,
                "power_type",
                "ipmilan",
                token)
            cobbler_server.modify_system(
                new_system_create,
                "profile",
                COBBLER_PROFILE,
                token)
            cobbler_server.modify_system(
                new_system_create,
                'modify_interface',
                {
                    "macaddress-eth0": mac_pxe,
                    "ipaddress-eth0": ipv4_pxe,
                    "dnsname-eth0": hostname},
                token)
            if CFG_OS_DISK in inv.cfg[CFG_NODES_TEMPLATES][node[INV_TEMPLATE]]:
                disks = (
                    inv.cfg[CFG_NODES_TEMPLATES][node[INV_TEMPLATE]]
                    [CFG_OS_DISK])
                if isinstance(disks, basestring):
                    KS_META = 'install_disk=%s' % disks
                elif isinstance(disks, list) and len(disks) == 2:
                    KS_META = (
                        'install_disk=%s install_disk_2=%s' %
                        (disks[0], disks[1]))
                else:
                    log.error(
                        'Invalid %s[%s][%s] value: '
                        'Must be string or two item list.' %
                        (CFG_NODES_TEMPLATES, node[INV_TEMPLATE],
                            CFG_OS_DISK))
                cobbler_server.modify_system(
                    new_system_create,
                    "ks_meta",
                    KS_META,
                    token)
            comment = ""
            if YAML_CHASSIS_PART_NUMBER in node:
                comment += (
                    '%s: %s\n' %
                    (YAML_CHASSIS_PART_NUMBER, node[YAML_CHASSIS_PART_NUMBER]))
            if YAML_CHASSIS_SERIAL_NUMBER in node:
                comment += (
                    '%s: %s\n' %
                    (YAML_CHASSIS_SERIAL_NUMBER,
                        node[YAML_CHASSIS_SERIAL_NUMBER]))
            if YAML_MODEL in node:
                comment += (
                    '%s: %s\n' %
                    (YAML_MODEL, node[YAML_MODEL]))
            if YAML_SERIAL_NUMBER in node:
                comment += (
                    '%s: %s\n' %
                    (YAML_SERIAL_NUMBER, node[YAML_SERIAL_NUMBER]))
            cobbler_server.modify_system(
                new_system_create,
                "comment",
                comment,
                token)

            cobbler_server.save_system(new_system_create, token)

            log.info(
                "Cobbler Add System: name=%s, profile=%s" %
                (hostname, COBBLER_PROFILE))

        cobbler_server.sync(token)
        log.info("Running Cobbler sync")

if __name__ == '__main__':
    """
    Arg1: config file
    Arg2: inventory file
    Arg3: log level
    """
    log = Logger(__file__)

    ARGV_MAX = 4
    argv_count = len(sys.argv)
    if argv_count > ARGV_MAX:
        try:
            raise Exception()
        except:
            log.error('Invalid argument count')
            exit(1)

    cfg_file = sys.argv[1]
    inv_file = sys.argv[2]
    if argv_count == ARGV_MAX:
        log_level = sys.argv[3]
    else:
        log_level = None

    cobbler_output = CobblerAddSystems(log_level, inv_file, cfg_file)
