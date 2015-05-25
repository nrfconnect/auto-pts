"""Python bindings for PTSControl introp objects

Cause of tight coupling with PTS, this module is Windows specific
"""

import os
import sys
import logging
import argparse

import clr
import System

import ctypes
libc = ctypes.cdll.msvcrt # for wcscpy_s

# load the PTS interop assembly
clr.AddReferenceToFile("Interop.PTSControl.dll")

import Interop.PTSControl as PTSControl

log = logging.debug

class PTSLogger(PTSControl.IPTSControlClientLogger):
    """PTS control client logger implementation"""

    def __init__(self):
        """"Constructor"""

        # an object that implements testcase.PTSCallback, it can either be
        # TestCase or xmlrpc SimpleXMLRPCServer running in auto pts client.
        self.callback = None

    def set_callback(self, callback):
        """Sets the callback"""
        self.callback = callback

    def unset_callback(self):
        """Unsets the callback"""
        self.callback = None

    def Log(self, log_type, logtype_string, log_time, log_message):
        """Implements:

        interface IPTSControlClientLogger : IUnknown {
            HRESULT _stdcall Log(
                            [in] _PTS_LOGTYPE logType,
                            [in] LPWSTR szLogType,
                            [in] LPWSTR szTime,
                            [in] LPWSTR pszMessage);
        };
        """

        logger = logging.getLogger(self.__class__.__name__)
        log = logger.info

        log("%s %s %s %s" % (log_type, logtype_string, log_time, log_message))

        try:
            # xmrpc proxy object in boolean test calls the method __nonzero__
            # of the xmlrpc server, so "is" test is a better choice here
            if self.callback is not None:
                log("Calling callback.log")
                # log_type of type PTSControl._PTS_LOGTYPE is marshalled as
                # int since xmlrcp has not marshalling rules for _PTS_LOGTYPE
                self.callback.log(int(log_type), logtype_string, log_time,
                                  log_message)
        except Exception as e:
            log("Caught exception")
            log(e)
            # exit does not work, cause app is blocked in PTS.RunTestCase?
            sys.exit("Exception in Log")

class PTSSender(PTSControl.IPTSImplicitSendCallbackEx):
    """Implicit send callback implementation"""

    def __init__(self):
        """"Constructor"""

        # an object that implements testcase.PTSCallback, it can either be
        # TestCase or xmlrpc SimpleXMLRPCServer running in auto pts client.
        self.callback = None

    def set_callback(self, callback):
        """Sets the callback"""
        self.callback = callback

    def unset_callback(self):
        """Unsets the callback"""
        self.callback = None

    def OnImplicitSend(self, project_name, wid, test_case_name, description,
                       style, response, response_size, response_is_present):
        """Implements:

        interface IPTSImplicitSendCallbackEx : IUnknown {
        HRESULT _stdcall OnImplicitSend(
                    [in] LPWSTR pszProjectName,
                    [in] unsigned short wID,
                    [in] LPWSTR pszTestCase,
                    [in] LPWSTR pszDescription,
                    [in] unsigned long style,
                    [in, out] LPWSTR pszResponse,
                    [in] unsigned long responseSize,
                    [in, out] long* pbResponseIsPresent);
        };
        """

        logger = logging.getLogger(self.__class__.__name__)
        log = logger.info

        log("*" * 20)
        log("BEGIN OnImplicitSend:")
        log("project_name: %s %s" % (project_name, type(project_name)))
        log("wid: %d %s" % (wid, type(wid)))
        log("test_case_name: %s %s" % (test_case_name, type(test_case_name)))
        log("description: %s %s" % (description, type(description)))
        log("style: Ox%x %s" % (style, type(style)))
        log("response:  %s %s %s" % (repr(response), type(response), id(response)))
        log("response_size: %d %s" % (response_size, type(response_size)))
        log("response_is_present:  %s %s" % (response_is_present, type(response_is_present)))

        callback_response = ""

        try:
            # xmrpc proxy object in boolean test calls the method __nonzero__
            # of the xmlrpc server, so "is" test is a better choice here
            if self.callback is not None:
                log("Calling callback.on_implicit_send")
                callback_response = self.callback.on_implicit_send(
                    project_name,
                    int(wid), # UInt16 cannot be marshalled
                    test_case_name,
                    description,
                    int(style),
                    int(response),
                    int(response_size),
                    int(response_is_present))

                log("callback returned on_implicit_send, respose: %s",
                    callback_response)

                if callback_response:
                    libc.wcscpy_s(response, response_size,
                                  unicode(callback_response))
                    response_is_present.Value = 1

        except Exception as e:
            log("Caught exception")
            log(e)
            # exit does not work, cause app is blocked in PTS.RunTestCase?
            sys.exit("Exception in OnImplicitSend")

        # not easy to to redirect libc stdout to the log file, can print it by:
        # libc._putws(response)
        # libc.fflush(None);
        log("final response: %s %s %s" % (response, type(response),
                                          id(response)))
        log("final response_is_present: %s %s" %
            (response_is_present, type(response_is_present)))

        log("END OnImplicitSend:")
        log("*" * 20)

class PyPTS:
    """PTS control interface.

    Provides wrappers around Interop.PTSControl.PTSControlClass methods and
    some additional features.

    For detailed documentation see 'Extended Automatiing - Using PTSControl'
    document provided with PTS in file Extended_Automating.pdf

    """

    def __init__(self):
        """Constructor"""
        log("%s", self.__init__.__name__)

        self._pts = PTSControl.PTSControlClass()

        self._pts_logger = PTSLogger()
        self._pts_sender = PTSSender()

        # cached frequently used PTS attributes: optimisation reasons it is
        # avoided to contact PTS. These attributes should not change anyway.
        self.__bd_addr = None

        # mandatory to set at least to None if logger is not used
        self.set_control_client_logger_callback(self._pts_logger)

        self.register_implicit_send_callback_ex(self._pts_sender)

        log("PTS Version: %x", self.get_version())
        log("PTS Bluetooth Address: %x", self.get_bluetooth_address())
        log("PTS BD_ADDR: %s" % self.bd_addr())

    def create_workspace(self, bd_addr, pts_file_path, workspace_name,
                         workspace_path):
        """Creates a new workspace"""

        log("%s %s %s %s", self.create_workspace.__name__, bd_addr,
            pts_file_path, workspace_name, workspace_path)

        self._pts.CreateWorkspace(bd_addr, pts_file_path, workspace_name,
                                   workspace_path)

    def open_workspace(self, workspace_path):
        """Opens existing workspace"""

        log("%s %s", self.open_workspace.__name__, workspace_path)
        self._pts.OpenWorkspace(workspace_path)

    def get_project_count(self):
        """Returns number of projects available in the current workspace"""

        project_count = clr.StrongBox[System.UInt32]()
        self._pts.GetProjectCount(project_count)
        project_count_int = int(project_count)

        log("%s out: %s", self.get_project_count.__name__, project_count_int)

        return project_count_int

    def get_project_name(self, project_index):
        """Returns project name"""

        project_name = ""
        project_name = self._pts.GetProjectName(project_index, project_name)

        log("%s %s out: %s", self.get_project_name.__name__, project_index,
            project_name)

        return project_name

    def get_project_version(self, project_name):
        """Returns project version"""

        project_version = self._pts.GetProjectVersion(project_name)

        log("%s %s out: %s", self.get_project_version.__name__, project_name,
            project_version)

        return project_version

    def get_test_case_count(self, project_name):
        """Returns the number of test cases that are available in the specified
        project."""

        test_case_count = clr.StrongBox[System.UInt32]()
        self._pts.GetTestCaseCount(project_name, test_case_count)
        test_case_count_int  = int(test_case_count)

        log("%s %s out: %s", self.get_test_case_count.__name__, project_name,
            test_case_count_int)

        return test_case_count_int

    def get_test_case_name(self, project_name, test_case_index):
        """Returns name of the specified test case"""

        test_case_name = ""
        test_case_name = self._pts.GetTestCaseName(project_name,
                                                    test_case_index,
                                                    test_case_name)

        log("%s %s %s out: %s", self.get_test_case_name.__name__, project_name,
            test_case_index, test_case_name)

        return test_case_name

    def get_test_case_description(self, project_name, test_case_index):
        """Returns description of the specified test case"""

        test_case_description = ""
        test_case_description = self._pts.GetTestCaseDescription(
            project_name, test_case_index, test_case_description)

        log("%s %s %s out: %s", self.get_test_case_description.__name__,
            project_name, test_case_index, test_case_description)

        return test_case_description

    def is_active_test_case(self, project_name, test_case_name):
        """Returns True if the specified test case is active (enabled) in the
        specified project. Returns False is if the test case is not active
        (disabled).
        """

        is_active = clr.StrongBox[System.Int32]()
        self._pts.IsActiveTestCase(project_name, test_case_name, is_active)
        is_active_bool = bool(int(is_active))

        log("%s %s %s out: %s", self.is_active_test_case.__name__,
            project_name, test_case_name, is_active_bool)

        return is_active_bool

    def run_test_case(self, project_name, test_case_name):
        """Executes the specified Test Case."""

        log("Starting %s %s %s", self.run_test_case.__name__, project_name,
            test_case_name)

        self._pts.RunTestCase(project_name, test_case_name)

        log("Done %s %s %s", self.run_test_case.__name__, project_name,
            test_case_name)

    def run_test_case_object(self, test_case):
        """Runs the test case specified by a TestCase instance.

        This method will cause the status of TestCase to be updated
        automatically and its on_implicit_send to be called from PTSSender

        NOTE: cannot be used over xmlrpc, unless marshalling of TestCase is
        implemented

        """
        log("Starting TestCase %s %s", self.run_test_case_object.__name__,
            test_case)

        self.register_ptscallback(test_case)

        test_case.pre_run()
        self.run_test_case(test_case.project_name, test_case.name)
        test_case.post_run()

        self.unregister_ptscallback()

        log("Done TestCase %s %s", self.run_test_case.__name__, test_case)

    def stop_test_case(self, project_name, test_case_name):
        """NOTE: According to documentation 'StopTestCase() is not currently
        implemented'"""

        log("%s %s %s", self.is_active_test_case.__name__, project_name,
            test_case_name)

        self._pts.StopTestCase(project_name, test_case_name)

    def get_test_case_count_from_tss_file(self, project_name):
        """Returns the number of test cases that are available in the specified
        project according to TSS file."""

        test_case_count = clr.StrongBox[System.UInt32]()
        self._pts.GetTestCaseCountFromTSSFile(project_name, test_case_count)
        test_case_count_int = int(test_case_count)

        log("%s %s out: %s", self.get_test_case_count_from_tss_file.__name__,
            project_name, test_case_count_int)

        return test_case_count_int

    def get_test_cases_from_tss_file(self, project_name):
        """Returns array of test case names according to TSS file."""

        test_cases_unused = []
        test_cases = self._pts.GetTestCasesFromTSSFile(project_name,
                                                        test_cases_unused)

        log("%s %s out: %s", self.get_test_cases_from_tss_file.__name__,
            project_name, repr(test_cases))

        return test_cases

    def update_pics(self, project_name, entry_name, bool_value):
        """Updates PICS

        This wrapper handles exceptions that PTS throws if PICS entry is
        already set to the same value.

        PTS throws exception if the value passed to UpdatePics is the same as
        the value when PTS was started.

        In C++ HRESULT error with this value is returned:
        PTSCONTROL_E_PICS_ENTRY_NOT_CHANGED (0x849C0032)

        """
        log("%s %s %s %s", self.update_pics.__name__, project_name,
            entry_name, bool_value)

        try:
            self._pts.UpdatePics(project_name, entry_name, bool_value)
        except System.Runtime.InteropServices.COMException as e:
            log('Exception in UpdatePics "%s", is pics value aready set?' %
                (e.Message,))

    def update_pixit_param(self, project_name, param_name, new_param_value):
        """Updates PIXIT

        This wrapper handles exceptions that PTS throws if PIXIT param is
        already set to the same value.

        PTS throws exception if the value passed to UpdatePixitParam is the same as
        the value when PTS was started.

        In C++ HRESULT error with this value is returned:
        PTSCONTROL_E_PIXIT_PARAM_NOT_CHANGED (0x849C0021)

        """
        log("%s %s %s %s", self.update_pixit_param.__name__, project_name,
            param_name, new_param_value)

        try:
            self._pts.UpdatePixitParam(project_name, param_name, new_param_value)
        except System.Runtime.InteropServices.COMException as e:
            log(('Exception in UpdatePixitParam "%s", is pixit param aready '
                 'set?') % (e.Message,))

    def enable_maximum_logging(self, enable):
        """Enables/disables the maximum logging."""

        log("%s %s", self.enable_maximum_logging.__name__, enable)
        self._pts.EnableMaximumLogging(enable)

    def set_call_timeout(self, timeout):
        """Sets a timeout period in milliseconds for the RunTestCase() calls
        to PTS."""

        log("%s %s", self.set_call_timeout.__name__, timeout)
        self._pts.SetPTSCallTimeout(timeout)

    def save_test_history_log(self, save):
        """This function enables automation clients to specify whether test
        logs have to be saved in the corresponding workspace folder.

        save -- Boolean

        """

        log("%s %s", self.save_test_history_log.__name__, save)
        self._pts.SaveTestHistoryLog(save)

    def get_bluetooth_address(self):
        """Returns PTS bluetooth address as a 64 bit integer"""

        pts_bt_address = clr.StrongBox[System.UInt64]()
        self._pts.GetPTSBluetoothAddress(pts_bt_address)
        pts_bt_address_int = int(pts_bt_address)

        log("%s out: %x", self.get_bluetooth_address.__name__,
            pts_bt_address_int)

        return pts_bt_address_int

    def bd_addr(self):
        '''Returns PTS BD_ADDR as a string'''
        # use cached address if available
        if self.__bd_addr:
            log("%s out cached: %s", self.bd_addr.__name__, self.__bd_addr)
            return self.__bd_addr

        bt_address_int = self.get_bluetooth_address()
        bt_address_upper = ("%x" % bt_address_int).upper()

        bd_addr = "00"
        for i in range(0, len(bt_address_upper), 2):
            bd_addr += ":" + bt_address_upper[i:i + 2]

        self.__bd_addr = bd_addr

        log("%s out: %s", self.bd_addr.__name__, self.__bd_addr)

        return bd_addr

    def get_version(self):
        """Returns PTS version"""

        pts_version = clr.StrongBox[System.UInt32]()
        self._pts.GetPTSVersion(pts_version)
        pts_version_int = int(pts_version)

        log("%s out: %x", self.get_version.__name__, pts_version_int)

        return pts_version_int

    def set_control_client_logger_callback(self, logger):
        """Sets PTSControl logger

        Note: if this function is not called upon initialization of PTSControl
        COM object, the COM object won't work. Calling with logger set to
        None also get the COM object working.

        logger -- a COM object derived from IPTSControlClientLogger, set it to
                  None to disable logging

        """

        log("%s %s", self.set_control_client_logger_callback.__name__, logger)

        self._pts.SetControlClientLoggerCallback(logger)

    def register_implicit_send_callback_ex(self, callback):
        """Connects the implicit send handler to the PTS.

        callback -- a COM object derived from IPTSImplicitSendCallbackEx

        """

        log("%s %s", self.register_implicit_send_callback_ex.__name__,
            callback)

        self._pts.RegisterImplicitSendCallbackEx(callback)

    def unregister_implicit_send_callback_ex(self, callback):
        """Disconnects the implicit send handler from the PTS."""

        log("%s %s", self.unregister_implicit_send_callback_ex.__name__,
            callback)

        self._pts.UnregisterImplicitSendCallbackEx(callback)

    def register_ptscallback(self, callback):
        """Registers testcase.PTSCallback instance to be used as PTS log and
        implicit send callback"""

        log("%s %s", self.register_ptscallback.__name__, callback)

        self._pts_logger.set_callback(callback)
        self._pts_sender.set_callback(callback)

    def unregister_ptscallback(self):
        """Unregisters the testcase.PTSCallback callback"""

        log("%s", self.unregister_ptscallback.__name__)

        self._pts_logger.unset_callback()
        self._pts_sender.unset_callback()

def parse_args():
    """Parses command line arguments and options"""
    required_ext = ".pqw6" # valid PTS workspace file extension

    arg_parser = argparse.ArgumentParser(
        description = "PTS Control")

    arg_parser.add_argument(
        "workspace",
        help = "Path to PTS workspace to use for testing. It should have %s "
        "extension" % (required_ext,))

    args = arg_parser.parse_args()

    # check that aruments and options are sane
    if not os.path.isfile(args.workspace):
        raise Exception("Workspace file '%s' does not exist" %
                        (args.workspace,))

    specified_ext = os.path.splitext(args.workspace)[1]
    if required_ext != specified_ext:
        raise Exception(
            "Workspace file '%s' extension is wrong, should be %s" %
            (args.workspace, required_ext))

    return args

def main():
    """Rudimentary testing."""

    args = parse_args()

    script_name = os.path.basename(sys.argv[0]) # in case it is full path
    script_name_no_ext = os.path.splitext(script_name)[0]

    log_filename = "%s.log" % (script_name_no_ext,)
    logging.basicConfig(format = '%(name)s [%(asctime)s] %(message)s',
                        filename = log_filename,
                        filemode = 'w',
                        level = logging.DEBUG)

    pts = PyPTS()

    pts.open_workspace(args.workspace)

    # pts.run_test_case("RFCOMM", "TC_RFC_BV_19_C")

    project_count = pts.get_project_count()
    print "Project count:", project_count

    # print all projects and their test cases
    for project_index in range(project_count):
        project_name = pts.get_project_name(project_index)
        print "\nProject name:", project_name
        print "Project version:", pts.get_project_version(project_name)
        test_case_count = pts.get_test_case_count(project_name)
        print "Test case count:", test_case_count

        for test_case_index in range(test_case_count):
            test_case_name = pts.get_test_case_name(project_name, test_case_index)
            print "\nTest case project:", project_name
            print "Test case name:", test_case_name
            print "Test case description:", pts.get_test_case_description(project_name, test_case_index)
            print "Is active test case:", pts.is_active_test_case(project_name, test_case_name)

    print "\n\n\n\nTSS file info:"

    # print all projects and their test cases
    for project_index in range(project_count):
        project_name = pts.get_project_name(project_index)
        print "\nProject name:", project_name
        print "Project version:", pts.get_project_version(project_name)
        test_case_count = pts.get_test_case_count_from_tss_file(project_name)
        print "Test case count:", test_case_count


        test_cases = pts.get_test_cases_from_tss_file(project_name)
        print test_cases

        for test_case in test_cases:
            print test_case


    pts.update_pixit_param("L2CAP", "TSPX_iut_role_initiator", "FALSE")
    pts.update_pixit_param("L2CAP", "TSPX_iut_role_initiator", "TRUE")

    pts.update_pics("L2CAP", "TSPC_L2CAP_3_13", True)
    pts.update_pics("L2CAP", "TSPC_L2CAP_3_13", False)

    pts.enable_maximum_logging(True)
    pts.enable_maximum_logging(False)

    pts.set_call_timeout(600000)
    pts.set_call_timeout(0)

    pts.save_test_history_log(True)
    pts.save_test_history_log(False)

    pts.register_implicit_send_callback_ex(None)
    pts.unregister_implicit_send_callback_ex(None)

    pts.set_control_client_logger_callback(None)

    print
    print "PTS Bluetooth Address: %x" % pts.get_bluetooth_address()
    print "PTS BD_ADDR:", pts.bd_addr()
    print "PTS BD_ADDR:", pts.bd_addr()
    print "PTS Version: %x" % pts.get_version()

if __name__ == "__main__":
    main()