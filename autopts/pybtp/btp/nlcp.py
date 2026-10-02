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
import struct
import time

from autopts.ptsprojects.stack import get_stack
from autopts.pybtp import defs
from autopts.pybtp.btp.btp import CONTROLLER_INDEX, btp_hdr_check
from autopts.pybtp.btp.btp import get_iut_method as get_iut
from autopts.pybtp.types import BTPError, le_bytes_to_hex_str

log = logging.debug


NLCP = {
    'read_supported_cmds': (defs.BTP_SERVICE_ID_NLCP,
                            defs.BTP_NLCP_CMD_READ_SUPPORTED_COMMANDS,
                            CONTROLLER_INDEX),
    'read_identity_report': (defs.BTP_SERVICE_ID_NLCP,
                             defs.BTP_NLCP_CMD_READ_IDENTITY_REPORT,
                             CONTROLLER_INDEX, ""),
    'exec_button_injection': (defs.BTP_SERVICE_ID_NLCP,
                              defs.BTP_NLCP_CMD_EXEC_BUTTON_INJECTION,
                              CONTROLLER_INDEX, ""),
    'read_prov_node_info': (defs.BTP_SERVICE_ID_NLCP,
                            defs.BTP_NLCP_CMD_READ_PROV_NODE_INFO,
                            CONTROLLER_INDEX, ""),
    'exec_non_trivial': (defs.BTP_SERVICE_ID_NLCP,
                         defs.BTP_NLCP_CMD_EXEC_NON_TRIVIAL,
                         CONTROLLER_INDEX)
}


def nlcp_command_rsp_succ(timeout=20.0):
    logging.debug("%s", nlcp_command_rsp_succ.__name__)

    iutctl = get_iut()

    tuple_hdr, tuple_data = iutctl.btp_socket.read(timeout)
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_NLCP)

    return tuple_data


def nlcp_read_identity_report(retries=20, delay=0.5):
    logging.debug("")

    iutctl = get_iut()

    for _ in range(retries):
        try:
            ret = iutctl.btp_socket.send_wait_rsp(*NLCP['read_identity_report'])
            break
        except BTPError:
            time.sleep(delay)
    else:
        raise BTPError("NLCP: identity is not ready.")

    rsp = ret[0] if isinstance(ret, tuple) else ret

    identity_fmt = '<16s32sBHBHH'
    if len(rsp) != struct.calcsize(identity_fmt):
        raise BTPError(f"NLCP identity: {len(rsp)} B, expected "
                       f"{struct.calcsize(identity_fmt)}")

    (uuid, static_auth, out_size, out_acts, in_size, in_acts, crpl) = struct.unpack_from(identity_fmt, rsp)
    logging.warning("NLCP identity: uuid=%s static_auth=%s out=(%d, 0x%04x) "
                    "in=(%d, 0x%04x) crpl=%d",
                    uuid.hex(), static_auth.hex(), out_size, out_acts,
                    in_size, in_acts, crpl)

    stack = get_stack()
    stack.nlcp.set_identity_report(uuid, static_auth, out_size, out_acts, in_size, in_acts, crpl)


def nlcp_exec_button_injection(btn, act):
    logging.debug("")

    btn_inject_fmt = '<B'

    act_btn = (act | btn) & 0xFF
    data = struct.pack(btn_inject_fmt, act_btn)

    iutctl = get_iut()
    ret = iutctl.btp_socket.send_wait_rsp(*NLCP['exec_button_injection'], data)

    rsp = ret[0] if isinstance(ret, tuple) else ret
    if len(rsp) != struct.calcsize(btn_inject_fmt):
        raise BTPError(f"NLCP button inject: {len(rsp)} B, expected "
                       f"{struct.calcsize(btn_inject_fmt)}")

    (recv_act_btn,) = struct.unpack_from(btn_inject_fmt, rsp)

    if (recv_act_btn != act_btn):
        raise BTPError(f"NLCP button inject: not applied, {recv_act_btn:#04x}.")

    stack = get_stack()
    stack.nlcp.set_inject_last(btn, act)


def nlcp_read_prov_node_info():
    logging.debug("")

    iutctl = get_iut()
    ret = iutctl.btp_socket.send_wait_rsp(*NLCP['read_prov_node_info'])

    rsp = ret[0] if isinstance(ret, tuple) else ret

    prov_node_fmt = '<BH'
    if len(rsp) != struct.calcsize(prov_node_fmt):
        raise BTPError(f"NLCP provisioned info: {len(rsp)} B, expected "
                       f"{struct.calcsize(prov_node_fmt)}")

    (elems_num, primary_addr) = struct.unpack_from(prov_node_fmt, rsp)

    if (elems_num == 0) or (primary_addr == 0):
        raise BTPError("NLCP provisioned info: invalid elems num or primary addr.")

    stack = get_stack()
    stack.nlcp.set_prov_info(elems_num, primary_addr)


def nlcp_exec_non_trivial(opcode):
    logging.debug("")

    ALLOWED_OPCODES = (defs.NLCP_NON_TRIV_ACT_RESET_NODE,
                       defs.NLCP_NON_TRIV_DATA_BSSP_SCENE_IDX)

    if opcode not in ALLOWED_OPCODES:
        raise BTPError("NLCP non-trivial: unknown operation.")

    non_triv_req_fmt = '<B'
    data = struct.pack(non_triv_req_fmt, opcode)

    iutctl = get_iut()
    ret = iutctl.btp_socket.send_wait_rsp(*NLCP['exec_non_trivial'], data)

    rsp = ret[0] if isinstance(ret, tuple) else ret

    non_triv_rsp_hdr_fmt = '<BH'
    non_triv_rsp_hdr_size = struct.calcsize(non_triv_rsp_hdr_fmt)
    if len(rsp) < non_triv_rsp_hdr_size:
        raise BTPError(f"NLCP non-trivial: {len(rsp)} B, header is "
                       f"{non_triv_rsp_hdr_size} B")

    (rsp_type, rsp_len) = struct.unpack_from(non_triv_rsp_hdr_fmt, rsp)
    data = rsp[non_triv_rsp_hdr_size:]

    if opcode != rsp_type:
        raise BTPError(f"NLCP non-trivial: type {rsp_type:#04x}, "
                       f"expected {opcode:#04x}")
    if len(data) != rsp_len:
        raise BTPError(f"NLCP non-trivial: data {len(data)} B, len field {rsp_len}")

    stack = get_stack()

    match opcode:
        case defs.NLCP_NON_TRIV_ACT_RESET_NODE:
            (result,) = struct.unpack_from('<B', data)
            return result

        case defs.NLCP_NON_TRIV_DATA_BSSP_SCENE_IDX:
            (scene_idx,) = struct.unpack_from('<H', data)
            stack.nlcp.set_non_triv_data_bss_scene_idx(scene_idx)
            return scene_idx


def nlcp_process_node_reset(await_dur_s=20.0, delay=0.2):
    """Wipe the IUT settings and wait until it reboots clean.

    Returns True if the IUT has been wiped and rebooted, False if the Node is
    not provisioned, so nothing has been done.
    Raises BTPError if the IUT does not accept the request within await_dur_s.
    """
    logging.debug("%s", nlcp_process_node_reset.__name__)

    # Before starting transmitting of the reset request need to clean up the
    # queue to prevent false positives.
    ready_ev = get_stack().core.event_queues[defs.BTP_CORE_EV_IUT_READY]
    last_error = None

    timeout = time.monotonic() + await_dur_s
    while True:
        ready_ev.clear()
        try:
            result = nlcp_exec_non_trivial(defs.NLCP_NON_TRIV_ACT_RESET_NODE)
            break
        except BTPError as error:
            # NOT_READY: BT/Mesh is not initialized or settings not loaded yet
            # FAILED: wipe failed, the IUT reboots, retry when it's available
            last_error = error
        if time.monotonic() >= timeout:
            raise BTPError(f"NLCP: IUT is not ready for Node reset ({last_error})")
        time.sleep(delay)

    if result != defs.NLCP_NON_TRIV_ACT_RESULT_OK:
        return False  # Not provisioned: no wipe, no reboot

    # No board reset via the probe: the IUT reboots by itself
    get_iut().wait_iut_ready_event(reset=False)

    return True


# An example event, to be changed or deleted
def nlcp_ev_dummy_completed(nlcp, data, data_len):
    logging.debug('%s %r', nlcp_ev_dummy_completed.__name__, data)

    fmt = '<B6sB'
    if len(data) < struct.calcsize(fmt):
        raise BTPError('Invalid data length')

    addr_type, addr, status = struct.unpack_from(fmt, data)

    addr = le_bytes_to_hex_str(addr)

    logging.debug(f'NLCP Dummy event completed: addr {addr} addr_type '
                  f'{addr_type} status {status}')

    nlcp.event_received(defs.BTP_NLCP_EV_DUMMY_COMPLETED, (addr_type, addr, status))


NLCP_EV = {
    defs.BTP_NLCP_EV_DUMMY_COMPLETED: nlcp_ev_dummy_completed,
}
