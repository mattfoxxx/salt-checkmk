# -*- coding: utf-8 -*-
#!/usr/bin/env python
'''
:maintainer: Matthias Mintert (matthias.mintert@gmail.com)
:maturity: 20210714
:requires: none
:platform: all

Support for CheckMK
'''

from __future__ import absolute_import
import os
import salt.utils
import re
import logging
from salt.exceptions import SaltException
from requests.exceptions import SSLError, ConnectionError

LOG = logging.getLogger(__name__)

__virtualname__ = 'check-mk-agent'

updater_local_destination = '/usr/bin/cmk-update-agent'

def _set_global_vars():
    global id
    id = __grains__['id']
    LOG.debug(f'checkmk: id was set to {id}')


def __virtual__():
    """
    Only load the module if check-mk-web-api module is installed and checkmk_agent role was found in grains.
    """
    if 'checkmk_agent' in __grains__['roles']:
        _set_global_vars()
        return __virtualname__
    return (
        False,
        "The check-mk-web-api python module could not be loaded or the minion is missing the role 'checkmk_agent'."
    )

def current_updater_state():
    """
    A function to return the state of the updater

    CLI Example::

        salt '*' checkmk.current_updater_state
    """
    result = True
    ret = {}
    if not __salt__['file.file_exists'](updater_local_destination):
        ret.update({'updater_binary': f"{updater_local_destination} not found"})
        result = False
    else:
        ret.update({'updater_binary': f"{updater_local_destination} found"})

    return (
        result,
        ret
    )

def current_agent_state():
    """
    A function to return the state of the agent
    CLI Example::


        salt '*' checkmk.current_agent_state
    """
    result = True
    ret = {}
    if not __salt__['file.file_exists']('/usr/bin/check_mk_agent'):
        ret.update({'agent_binary': "CheckMK agent binary not found"})
        if result: result = False
    else:
        ret.update({'agent_binary': f"CheckMK agent binary not found"})

    return (
        result,
        ret
    )

def install_update_agent(cmk_url, proto, site):
    """
    install cmk-update-agent and register host for agent updates.

    CLI Example::

        salt '*' checkmk.install_agent_updater cmk_url proto site automation_user automation_secret
    """
    updater_url = f"{proto}://{cmk_url}/{site}/check_mk/agents/plugins/cmk-update-agent"
    try:
        if not __salt__['cp.get_url'](updater_url, updater_local_destination):
            return (
                False,
                f'The cmk-update-agent file could be downloaded from {updater_url}!'
                )
    except SSLError:
        return (
            False,
            f"The URL {updater_url} could not be verified by {updater_local_destination}"
        )
    except ConnectionError:
        return (
            False,
            f"The URL {updater_url} could not be found by {updater_local_destination}"
        )

    if not __salt__['file.set_mode'](updater_local_destination, '0755'):
        return (
            False,
            f'Could not set mode on {updater_local_destination}!'
        )
    return (
        True,
        ''
    )
    

def register_update_agent(cmk_url, proto, site, automation_user, automation_secret):
    try:
        ret = __salt__['cmd.run'](f"{updater_local_destination} register -H {id} -s {cmk_url} -p {proto} -i {site} -U {automation_user} -S {automation_secret}", raise_err=True)
    except Exception as e:
        LOG.debug(f"CHECKMK: {e}")
        return (
            False,
            f"The host {id} could not be registered by {updater_local_destination}"
        )
    LOG.debug(f"CHECKMK: {ret}")
    return True


def install_checkmk_agent():
    success_pattern = "Successfully installed agent .*\."
    no_agent_available_pattern = "No agent available for us."
    try:
        ret = __salt__['cmd.run'](f"{updater_local_destination} -G -f -v", raise_err=True)
    except Exception as e:
        LOG.debug(f"CHECKMK: {e.with_traceback}")
        return (
            False,
            f"The agent could not be installed by {updater_local_destination}, see debug log for details."
        )
    LOG.debug(f"CHECKMK: {ret}")
    if re.findall(success_pattern, ret):
        return (
            True,
            "Agent successfully installed."
        )
    elif re.findall(no_agent_available_pattern, ret):
        return (
            False,
            f"The agent could not be installed: {no_agent_available_pattern}"
        )

