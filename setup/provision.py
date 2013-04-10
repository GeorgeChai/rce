#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     setup/provision.py
#
#     This file is part of the RoboEarth Cloud Engine framework.
#
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#
#     Copyright 2012 RoboEarth
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     \author/s: Dhananjay Sathe
#
#

# Python specific imports
import os
import errno
import readline
import glob
import subprocess
from ConfigParser import SafeConfigParser


# Setup the python interpreter path autocomplete.
def complete(text, state):
    return (glob.glob(text+'*')+[None])[state]
readline.set_completer_delims(' \t\n;')
readline.parse_and_bind("tab: complete")
readline.set_completer(complete)

# Helper function for config provisioning
def provision_config(root_path):
        """ Provision all required files as required for first runs.
        """
        dev_mode = raw_input('Do you want to autoprovision credentials for developer mode (Insecure)[y/N] : ')
        dev_mode = dev_mode.strip().lower() == 'y'
        parser = SafeConfigParser()
        config_file = os.path.join(os.getenv('HOME'), '.rce','config.ini')
        path=os.path.join(os.getenv('HOME'), '.rce')
        config = {'global':{'gzip_lvl':9,
                            'platform':'local',
                            'dev_mode':dev_mode,
                            'password_file':os.path.join(os.getenv('HOME'), '.rce','creds')},

                  'network':{'local':'eth0,eth0,lxcbr0',
                             'rackspace':'eth0,eth1,lxcbr0',
                             'aws':'aws_dns,eth0,lxcbr0' },

                  'converters':{'image':'rce.util.converters.image.ImageConverter',},

                  'comm':{'http_port':9000,
                          'ws_port':9010,
                          'master_port':8080,
                          'rce_internal_port':10030,
                          'rce_console_port':8081,
                          'ros_proxy_port':9020},

                  'machine':{'max_container':10,
                            'rootfs':os.path.join(root_path,'rootfs'),
                            'conf_dir':os.path.join(root_path,'config'),
                            'data_dir':os.path.join(root_path,'data')},

                  'machine/packages':{}}

        if not os.path.exists(path):
            os.makedirs(path)
        conf_file = open(config_file,'w')
        for section,opts in config.iteritems():
            parser.add_section(section)
            for key,val in opts.iteritems():
                parser.set(section, key, str(val))
        parser.write(conf_file)
        conf_file.close()
# Helper function to provision the cred db
def provision_creds():
    from rce.util.settings import RCESettingsManager
    from rce.util.cred import RCECredChecker, _FIRST_RUN_MSG
    settings = RCESettingsManager()
    dev_mode = settings.DEV_MODE

    cred_checker = RCECredChecker(True)
    required_users = {'admin':'admin', 'adminInfra':'admin'}


    if dev_mode:
            required_users['testUser'] = 'testUser'
            for username in required_users.iterkeys():
                try:
                    cred_checker.getUser(username)
                except (KeyError, OSError, AttributeError):
                    cred_checker.addUser(username, required_users[username],
                                 provision=True)
            cred_checker.setUserMode('admin', 0)
            cred_checker.addUserGroups('admin','owner')
    else:
            init_flag = True
            for username in required_users.iterkeys():
                try:
                    cred_checker.getUser(username)
                except (KeyError, OSError, AttributeError):
                    if init_flag:
                        print(_FIRST_RUN_MSG)
                        init_flag = False
                    cred_checker.addUser(username, cred_checker.get_new_password(username),
                                 provision=True)
            cred_checker.setUserMode('admin', 0)
            cred_checker.addUserGroups('admin','owner')
# We start the creation here

# Fetch the required directory options from the user.




def _get_argparse():
    from argparse import ArgumentParser

    parser = ArgumentParser(prog='provision',
                            description='Provision the base settings for the'
                            ' RoboEarth Cloud Engine ')

    parser.add_argument('mode', choices=['all', 'cred','config'],
                        help='Flag to select set up instead of tear down.', )

    return parser


if __name__ == '__main__':
    args = _get_argparse().parse_args()

    if args.mode == 'all':
        while True:
            container_path = raw_input("Enter the root directory to store the RoboEarth Container Filesystem [Tab to autocomplete]: ")
            if os.path.exists(os.path.dirname(container_path)):
                break
        packages = 'lxc debootstrap python-twisted-core python-openssl ros-fuerte-ros-comm ros-fuerte-common-msgs python-imaging'
        subprocess.call("""sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list'""",shell=True)
        subprocess.call('curl http://packages.ros.org/ros.key | sudo apt-key add -',shell=True)
        subprocess.call('sudo apt-get update',shell=True)
        subprocess.call('echo "y" | sudo apt-get install {0}'.format(packages),shell=True)

        for folder in ('data','config'):
            path = os.path.join(container_path,folder)
            try:
                os.makedirs(path)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    Warning((path)+' exists ignoring...')
                else: raise
        # Create the container
        subprocess.call('sudo bash container.bash --path={0}'.format(container_path),shell=True)
        # Post Provision commands
        box_packages='python-twisted-core python-twisted-web ros-fuerte-ros-comm ros-fuerte-common-msgs'
        commands = ['adduser --disabled-password --disabled-login ros',
                    'adduser --disabled-password --disabled-login --home /opt/rce/data rce',
                    'echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list',
                    'curl http://packages.ros.org/ros.key | apt-key add -',
                    'apt-get update',
                    'echo "y" |apt-get install {0}'.format(box_packages),
                    'echo "Please change the root password"',
                    ]
        commands=(';').join(commands)
        # build up the settings file
        provision_config(container_path)
        # provision the cred db
        provision_creds()
        subprocess.call('echo "{0}" | sudo rce-make'.format(commands),shell=True)

    elif args.mode == 'cred':
        provision_creds()

    elif args.mode == 'config':
        while True:
            container_path = raw_input("Enter the root directory to store the RoboEarth Container Filesystem [Tab to autocomplete]: ")
            if os.path.exists(os.path.dirname(container_path)):
                break
        for folder in ('data','config'):
            path = os.path.join(container_path,folder)
            try:
                os.makedirs(path)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    Warning((path)+' exists ignoring...')
                else: raise
        provision_config(os.path.join(container_path,'rootfs'))
    else:
        raise ValueError('Invalid mode.')



