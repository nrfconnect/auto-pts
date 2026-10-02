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

"""NLC Profiles Test Cases.

A single module for all of the NLC Profile Test Suites: having 7 almost
identical script files, one per NLC Profile, is hard to maintain. The module
is registered under the name of every supported profile at the end of the file.
"""


import sys
from fnmatch import fnmatchcase

from autopts.ptsprojects.stack import get_stack
from autopts.ptsprojects.testcase import TestFunc, TestFuncCleanUp
from autopts.ptsprojects.zephyr.nlcp_wid import nlcp_wid_hdl
from autopts.ptsprojects.zephyr.ztestcase import ZTestCase
from autopts.pybtp import btp

# Test Suites (profiles) supported by this module.
NLCP_TS_LIST = ("ALSNLCP", "BLCNLCP", "BSSNLCP", "DICNLCP",
                "ENMNLCP", "HVINLCP", "OCSNLCP")

# Set of default PIXITs should be applied for any single Test Case supported here.
NLCP_PROFILE_COMMON_PIXITS = {
    "TSPX_bd_addr_iut": "DEADBEEFDEAD",
    "TSPX_time_guard": "60000",
    "TSPX_use_implicit_send": "TRUE",
    "TSPX_mtu_size": "23",
    "TSPX_delete_link_key": "TRUE",
    "TSPX_delete_ltk": "TRUE",
    "TSPX_security_enabled": "FALSE",
    "TSPX_use_pb_gatt_bearer": "TRUE",
    "TSPX_iut_comp_data_page": "2",
}
# Per-profile PIXIT overrides, merged over the common ones.
# Pattern here: {"<NLC_PROFILE>": {"TSPX_...": "..."}}
NLCP_PROFILE_EXTRA_PIXITS = {}

# Default Auto-PTS timeout duration for the Client, in ms.
NLCP_TC_CLI_TIMEOUT_MS = 300000
# Timeout duration for Performance based Test Cases, in ms.
NLCP_TC_PERF_CLI_TIMEOUT_MS = 900000

# Set of default list of actions might to be called for any single Test Case.
NLCP_TC_DEFAULT_RECIPE = ("init_stack", "reset_node", "sync_identity")
# Map of specific Test Case names or name patterns might to have modified sequence.
NLCP_TC_CUSTOM_RECIPES = (
    ("*/GMIT/PERF/*", NLCP_TC_DEFAULT_RECIPE + ("tc_perf_cli_tout",)),
)


def _nlcp_get_profiles(pts):
    profiles_list = pts.get_project_list()
    return [profile for profile in NLCP_TS_LIST if profile in profiles_list]


def _nlcp_get_cli_default_timeout_ms():
    client = sys.modules.get("autopts.client")
    return getattr(client, "TEST_CASE_TIMEOUT_MS", NLCP_TC_CLI_TIMEOUT_MS)


def _nlcp_get_tc_commands(pts, profile, stack):
    """Precondition steps of the Test Case, bound to the profile.

    Every step is a factory creating new TestFunc instances on each call:
    they keep a state and must not be shared between Test Cases.
    The order "init_stack" -> "reset_node" -> "sync_identity" is mandatory:
    the reset needs the service registered, and the IUT identity can be read
    only after the IUT has rebooted.
    """

    return {
        "init_stack": lambda: [TestFunc(stack.nlcp_init)],
        "reset_node": lambda: [TestFunc(btp.nlcp_process_node_reset)],
        "sync_identity": lambda: [TestFunc(btp.nlcp_read_identity_report),
                                  TestFunc(lambda: _nlcp_update_identity(pts, profile))],
        "tc_perf_cli_tout": lambda: _nlcp_tc_launch(pts, NLCP_TC_PERF_CLI_TIMEOUT_MS),
    }


def _nlcp_tc_decode(tc_name):
    """Return the names of steps for a Test Case recipe."""
    for pattern, recipe in NLCP_TC_CUSTOM_RECIPES:
        if fnmatchcase(tc_name, pattern):
            return recipe
    return NLCP_TC_DEFAULT_RECIPE


def _nlcp_tc_build_preconditions(commands, tc_name):
    """Expand the recipe of the Test Case, into a direct list of commands."""
    recipe = _nlcp_tc_decode(tc_name)

    unknown_recipe = set(recipe) - commands.keys()
    if unknown_recipe:
        raise KeyError(f"NLCP recipe of {tc_name}: unknown steps {sorted(unknown_recipe)}")

    preconditions = []
    for index in recipe:
        preconditions += commands[index]()

    return preconditions


def _nlcp_tc_launch(pts, timeout_ms):
    """Raise the PTS call timeout for one test case and restore it after.

    set_call_timeout() stays in effect for the whole PTS session, so the
    cleanup is needed to keep the following test cases on the default.
    TestFuncCleanUp runs in post_run even after FAIL or PTS TIMEOUT.
    """
    return [
        TestFunc(lambda: pts.set_call_timeout(timeout_ms)),
        TestFuncCleanUp(lambda: pts.set_call_timeout(_nlcp_get_cli_default_timeout_ms())),
    ]


def _nlcp_update_identity(pts, profile):
    nlcp = get_stack().nlcp
    pts.update_pixit_param(profile, "TSPX_device_uuid", nlcp.get_ident_uuid())


def set_pixits(ptses):
    """Setup NLC Profiles PIXITS for workspace.
    Those values are used for test case if not updated within test case.

    PIXITS always should be updated accordingly to project and newest version of
    PTS.

    ptses -- list of PyPTS instances"""

    pts = ptses[0]

    for profile in _nlcp_get_profiles(pts):
        pixits = {**NLCP_PROFILE_COMMON_PIXITS, **NLCP_PROFILE_EXTRA_PIXITS.get(profile, {})}
        for name, value in pixits.items():
            pts.set_pixit(profile, name, value)


def test_cases(ptses):
    """
    Returns a list of NLCP profiles test cases.

    ptses -- list of PyPTS instances
    """

    pts = ptses[0]
    stack = get_stack()

    tc_list = []

    # Cycle all of the supported Profiles.
    for profile in _nlcp_get_profiles(pts):
        # Collect actions might be done before starting selected TC.
        commands = _nlcp_get_tc_commands(pts, profile, stack)

        # Build a list of the Test Cases available for the profile.
        tc_list.extend(
            ZTestCase(profile, tc_name,
                      cmds=_nlcp_tc_build_preconditions(commands, tc_name),
                      generic_wid_hdl=nlcp_wid_hdl)
            for tc_name in pts.get_test_case_list(profile)
        )

    return tc_list


# Register this module under the name of every NLC profile, so the client
# lookup by the test case prefix (e.g. HVINLCP -> hvinlcp) finds this file.
_this = sys.modules[__name__]
_pkg = sys.modules[__package__]
for _p in NLCP_TS_LIST:
    _alias = _p.lower()
    setattr(_pkg, _alias, _this)                      # getattr(zephyr, 'hvinlcp')
    sys.modules[f"{__package__}.{_alias}"] = _this    # import_module('...zephyr.hvinlcp')
