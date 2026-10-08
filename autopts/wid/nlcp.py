#
# auto-pts - The Bluetooth PTS Automation Framework
#
# Copyright (c) 2026, Nordic Semiconductor ASA.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#

import logging

from autopts.ptsprojects.stack import get_stack
from autopts.pybtp import btp
from autopts.pybtp.types import WIDParams

log = logging.debug

# NLC Profile Identifiers.
NLCP_PROFILE_ID = {
    "ALSNLCP": 0x1600,  # Ambient Light Sensor
    "BLCNLCP": 0x1601,  # Basic Lightness Controller
    "BSSNLCP": 0x1602,  # Basic Scene Selector
    "DICNLCP": 0x1603,  # Dimming Control
    "ENMNLCP": 0x1604,  # Energy Monitor
    "OCSNLCP": 0x1605,  # Occupancy Sensor
    "HVINLCP": 0x1606,  # HVAC Integration
}


def nlcp_wid_hdl(wid, description, test_case_name):
    from autopts.wid import generic_wid_hdl
    log(f'{nlcp_wid_hdl.__name__}, {wid}, {description}, {test_case_name}')
    return generic_wid_hdl(wid, description, test_case_name, [__name__, 'autopts.wid.mesh'])


# wid handlers section begin
def hdl_wid_13(_: WIDParams):
    """
    Implements:
    description: There is no shared security information. Please remove any
                 security information if any. PTS is waiting for beacon to
                 start provisioning from.
    """
    get_stack().nlcp.has_been_provisioned_by_lt = True
    return True


def hdl_wid_17(_: WIDParams):
    """
    Implements:
    description: PTS will send a packet to the IUT. Please click OK when ready
                 to receive a packet.
    """
    return True


def hdl_wid_2000(_: WIDParams):
    """
    Implements:
    description: Please perform dimming control function.
    """
    btp.nlcp_exec_dimming_ctrl()
    return True


def hdl_wid_2001(_: WIDParams):
    """
    Implements:
    description: Perform its scene selection function for the scene at
                 position N.
    """
    btp.nlcp_exec_scene_select()
    return True


def hdl_wid_4000(params: WIDParams):
    """
    Implements:
    description: Enter address for this test case.
    """
    profile = params.test_case_name.split("/")[0]
    addr = btp.nlcp_read_profile_elem_addr(NLCP_PROFILE_ID[profile])
    return f"{addr:04X}"


def hdl_wid_4001(_: WIDParams):
    """
    Implements:
    description: Enter scene for this test case (4 bytes HEX number).
    """
    scene = btp.nlcp_read_scene_number()
    return f"{scene:04X}"
