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

        # Provisioned Node configuration
        self.prov_elems_num = None
        self.prov_primary_addr = None

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

    def set_prov_config(self, elems_num, primary_addr):
        self.prov_elems_num = elems_num
        self.prov_primary_addr = primary_addr

    def get_identity_uuid(self):
        return self.ident_iut_uuid

    def get_ident_static_auth(self):
        return self.ident_static_auth

    def get_prov_config_elems_num(self):
        return self.prov_elems_num

    def get_prov_config_primary_addr(self):
        return self.prov_primary_addr
