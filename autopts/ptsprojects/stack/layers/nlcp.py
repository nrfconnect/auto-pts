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


class NLCP:
    def __init__(self, provisioned_by_lt=False):
        self.event_queues = {}

        # Flag: indicates IUT has been provisioned by LT during this session.
        self.has_been_provisioned_by_lt = provisioned_by_lt

        # Identity report
        self.ident_is_valid = False
        self.ident_iut_uuid = None     # 16 bytes max
        self.ident_static_auth = None  # 32 bytes max
        self.ident_output_size = 0
        self.ident_output_acts = 0
        self.ident_input_size = 0
        self.ident_input_acts = 0
        self.ident_crpl = 0

        # Button injection/usage
        self.inject_last_btn = None
        self.inject_last_act = None

        # Provisioned Node information
        self.prov_elems_num = None
        self.prov_primary_addr = None

        # Non-trivial information/actions/states
        self.nt_data_bss_scene_idx = None
        self.nt_state_node_reset = None

    def set_identity_report(self, uuid, static_auth, output_size,
                            output_acts, input_size, input_acts, crpl):
        self.ident_iut_uuid = bytes(uuid).hex()
        self.ident_static_auth = bytes(static_auth).hex()
        self.ident_output_size = output_size
        self.ident_output_acts = output_acts
        self.ident_input_size = input_size
        self.ident_input_acts = input_acts
        self.ident_crpl = crpl
        self.ident_is_valid = True

    def set_inject_last(self, btn, act):
        self.inject_last_btn = btn
        self.inject_last_act = act

    def set_prov_info(self, elems_num, primary_addr):
        self.prov_elems_num = elems_num
        self.prov_primary_addr = primary_addr

    def set_non_triv_data_bss_scene_idx(self, scene_idx):
        self.nt_data_bss_scene_idx = scene_idx

    def set_non_triv_state_node_reset(self, state):
        self.nt_state_node_reset = state

    def get_ident_uuid(self):
        return self.ident_iut_uuid

    def get_ident_static_auth(self):
        return self.ident_static_auth

    def get_prov_info_elems_num(self):
        return self.prov_elems_num

    def get_prov_info_primary_addr(self):
        return self.prov_primary_addr

    def get_non_triv_data_bss_scene_idx(self):
        return self.nt_data_bss_scene_idx

    def get_non_triv_state_node_reset(self):
        return self.nt_state_node_reset
