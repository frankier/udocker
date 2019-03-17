#!/usr/bin/env python2
"""
udocker unit tests.
Unit tests for udocker, a wrapper to execute basic docker containers
without using docker.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import sys
import unittest
import mock

sys.path.append('../../')

from udocker.utils.fileutil import FileUtil

STDOUT = sys.stdout
STDERR = sys.stderr
UDOCKER_TOPDIR = "test_topdir"

if sys.version_info[0] >= 3:
    BUILTINS = "builtins"
else:
    BUILTINS = "__builtin__"


def set_env():
    """Set environment variables."""
    if not os.getenv("HOME"):
        os.environ["HOME"] = os.getcwd()


def find_str(self, find_exp, where):
    """Find string in test output messages."""
    found = False
    for item in where:
        if find_exp in str(item):
            self.assertTrue(True)
            found = True
            break
    if not found:
        self.assertTrue(False)


def is_writable_file(obj):
    """Check if obj is a file."""
    try:
        obj.write("")
    except(AttributeError, OSError, IOError):
        return False
    else:
        return True


class FileUtilTestCase(unittest.TestCase):
    """Test FileUtil() file manipulation methods."""

    @classmethod
    def setUpClass(cls):
        """Setup test."""
        set_env()

    @mock.patch('udocker.config.Config')
    def test_01_init(self, mock_config):
        """Test FileUtil() constructor."""
        Config = mock_config
        Config.tmpdir = "/tmp"
        futil = FileUtil("filename.txt")
        self.assertEqual(futil.filename, os.path.abspath("filename.txt"))
        self.assertTrue(Config.tmpdir)

        mock_config.side_effect = AttributeError("abc")
        futil = FileUtil()
        self.assertEqual(futil.filename, None)

    @mock.patch('udocker.config.Config')
    def test_02_mktmp(self, mock_config):
        """Test FileUtil.mktmp()."""
        Config = mock_config
        Config.tmpdir = "/somewhere"
        tmp_file = FileUtil("filename2.txt").mktmp()
        self.assertTrue(tmp_file.endswith("-filename2.txt"))
        self.assertTrue(tmp_file.startswith("/somewhere/udocker-"))
        self.assertGreater(len(tmp_file.strip()), 68)

    @mock.patch('os.stat')
    def test_03_uid(self, mock_stat):
        """Test FileUtil.uid()."""
        mock_stat.return_value.st_uid = 1234
        uid = FileUtil("filename3.txt").uid()
        self.assertEqual(uid, 1234)

    @mock.patch('udocker.config.Config')
    @mock.patch('os.path.realpath')
    @mock.patch('os.path.exists')
    @mock.patch('udocker.msg.Msg')
    @mock.patch('os.remove')
    @mock.patch('os.path.islink')
    @mock.patch('os.path.isfile')
    @mock.patch('os.path.isdir')
    @mock.patch('udocker.utils.fileutil.FileUtil.uid')
    @mock.patch('udocker.utils.fileutil.FileUtil._is_safe_prefix')
    def test_04_remove_file(self, mock_safe, mock_uid, mock_isdir,
                            mock_isfile, mock_islink, mock_remove, mock_msg,
                            mock_exists, mock_realpath, mock_config):
        """Test FileUtil.remove() with plain files."""
        mock_uid.return_value = os.getuid()
        # file does not exist (regression of #50)
        mock_isdir.return_value = True
        mock_isfile.return_value = True
        mock_exists.return_value = True
        mock_safe.return_value = True
        Config = mock_config
        Config.uid = os.getuid()
        Config.tmpdir = "/tmp"
        mock_realpath.return_value = "/tmp"
        # under /
        futil = FileUtil("/filename4.txt")
        status = futil.remove()
        self.assertFalse(status)
        # wrong uid
        mock_uid.return_value = os.getuid() + 1
        futil = FileUtil("/tmp/filename4.txt")
        status = futil.remove()
        self.assertFalse(status)
        # under /tmp
        mock_uid.return_value = os.getuid()
        futil = FileUtil("/tmp/filename4.txt")
        status = futil.remove()
        self.assertTrue(status)
        # under user home
        futil = FileUtil("/home/user/.udocker/filename4.txt")
        futil.safe_prefixes.append("/home/user/.udocker")
        status = futil.remove()
        self.assertTrue(status)
        # outside of scope 1
        mock_safe.return_value = False
        futil = FileUtil("/etc/filename4.txt")
        futil.safe_prefixes = []
        status = futil.remove()
        self.assertFalse(status)

    @mock.patch('udocker.config.Config')
    @mock.patch('os.path.exists')
    @mock.patch('udocker.msg.Msg')
    @mock.patch('subprocess.call')
    @mock.patch('os.path.isdir')
    @mock.patch('os.path.islink')
    @mock.patch('os.path.isfile')
    @mock.patch('udocker.utils.fileutil.FileUtil.uid')
    @mock.patch('udocker.utils.fileutil.FileUtil._is_safe_prefix')
    def test_05_remove_dir(self, mock_safe, mock_uid, mock_isfile,
                           mock_islink, mock_isdir, mock_call,
                           mock_msg, mock_exists, mock_config):
        """Test FileUtil.remove() with directories."""
        mock_uid.return_value = os.getuid()
        mock_isfile.return_value = False
        mock_islink.return_value = False
        mock_isdir.return_value = True
        mock_exists.return_value = True
        mock_safe.return_value = True
        mock_call.return_value = 0
        Config = mock_config
        Config.uid = os.getuid()
        Config.tmpdir = "/tmp"
        # remove directory under /tmp OK
        futil = FileUtil("/tmp/directory")
        status = futil.remove()
        self.assertTrue(status)
        # remove directory under /tmp NOT OK
        mock_call.return_value = 1
        futil = FileUtil("/tmp/directory")
        status = futil.remove()
        self.assertFalse(status)

    @mock.patch('udocker.msg.Msg')
    @mock.patch('subprocess.call')
    @mock.patch('os.path.isfile')
    def test_06_verify_tar01(self, mock_isfile, mock_call, mock_msg):
        """Test FileUtil.verify_tar() check tar file."""
        mock_msg.level = 0
        mock_isfile.return_value = False
        mock_call.return_value = 0
        status = FileUtil("tarball.tar").verify_tar()
        self.assertFalse(status)

    @mock.patch('udocker.msg.Msg')
    @mock.patch('subprocess.call')
    @mock.patch('os.path.isfile')
    def test_07_verify_tar02(self, mock_isfile, mock_call, mock_msg):
        """Test FileUtil.verify_tar() check tar file."""
        mock_msg.level = 0
        mock_isfile.return_value = True
        mock_call.return_value = 0
        status = FileUtil("tarball.tar").verify_tar()
        self.assertTrue(status)

    @mock.patch('udocker.msg.Msg')
    @mock.patch('subprocess.call')
    @mock.patch('os.path.isfile')
    def test_08_verify_tar03(self, mock_isfile, mock_call, mock_msg):
        """Test FileUtil.verify_tar() check tar file."""
        mock_msg.level = 0
        mock_isfile.return_value = True
        mock_call.return_value = 1
        status = FileUtil("tarball.tar").verify_tar()
        self.assertFalse(status)

    @mock.patch('udocker.config.Config')
    @mock.patch('udocker.utils.fileutil.FileUtil.remove')
    def test_09_cleanup(self, mock_remove, mock_config):
        """Test FileUtil.cleanup() delete tmp files."""
        Config = mock_config
        Config.tmpdir = "/tmp"
        FileUtil.tmptrash = {'file1.txt': None, 'file2.txt': None}
        FileUtil("").cleanup()
        self.assertEqual(mock_remove.call_count, 2)

    @mock.patch('os.path.isdir')
    def test_10_isdir(self, mock_isdir):
        """Test FileUtil.isdir()."""
        mock_isdir.return_value = True
        status = FileUtil("somedir").isdir()
        self.assertTrue(status)
        mock_isdir.return_value = False
        status = FileUtil("somedir").isdir()
        self.assertFalse(status)

    @mock.patch('os.stat')
    def test_11_size(self, mock_stat):
        """Test FileUtil.size() get file size."""
        mock_stat.return_value.st_size = 4321
        size = FileUtil("somefile").size()
        self.assertEqual(size, 4321)

    def test_12_getdata(self):
        """Test FileUtil.size() get file content."""
        with mock.patch(BUILTINS + '.open',
                        mock.mock_open(read_data='qwerty')):
            data = FileUtil("somefile").getdata()
            self.assertEqual(data, 'qwerty')

    @mock.patch('udocker.utils.uprocess.Uprocess')
    def test_13_find_exec(self, mock_call):
        """Test FileUtil.find_exec() find executable."""
        mock_call.return_value.get_output.return_value = None
        filename = FileUtil("executable").find_exec()
        self.assertEqual(filename, "")
        #
        mock_call.return_value.get_output.return_value = "/bin/ls"
        filename = FileUtil("executable").find_exec()
        self.assertEqual(filename, "/bin/ls")
        #
        mock_call.return_value.get_output.return_value = "not found"
        filename = FileUtil("executable").find_exec()
        self.assertEqual(filename, "")

    @mock.patch('os.path.lexists')
    def test_14_find_inpath(self, mock_exists):
        """Test FileUtil.find_inpath() file is in a path."""
        # exist
        mock_exists.return_value = True
        filename = FileUtil("exec").find_inpath("/bin:/usr/bin")
        self.assertEqual(filename, "/bin/exec")
        # does not exist
        mock_exists.return_value = False
        filename = FileUtil("exec").find_inpath("/bin:/usr/bin")
        self.assertEqual(filename, "")
        # exist PATH=
        mock_exists.return_value = True
        filename = FileUtil("exec").find_inpath("PATH=/bin:/usr/bin")
        self.assertEqual(filename, "/bin/exec")
        # does not exist PATH=
        mock_exists.return_value = False
        filename = FileUtil("exec").find_inpath("PATH=/bin:/usr/bin")
        self.assertEqual(filename, "")

    def test_15_copyto(self):
        """Test FileUtil.copyto() file copy."""
        with mock.patch(BUILTINS + '.open', mock.mock_open()):
            status = FileUtil("source").copyto("dest")
            self.assertTrue(status)
            status = FileUtil("source").copyto("dest", "w")
            self.assertTrue(status)
            status = FileUtil("source").copyto("dest", "a")
            self.assertTrue(status)

    @mock.patch('os.makedirs')
    @mock.patch('udocker.utils.fileutil.FileUtil')
    def test_16_mkdir(self, mock_mkdirs, mock_futil):
        """Create directory"""
        mock_mkdirs.return_value = True
        status = mock_futil.mkdir()
        self.assertTrue(status)

        mock_mkdirs.side_effect = OSError("fail")
        status = mock_futil.mkdir()
        self.assertTrue(status)

    @mock.patch('os.umask')
    def test_17_umask(self, mock_umask):
        """Test FileUtil.umask()."""
        mock_umask.return_value = 0
        futil = FileUtil("somedir")
        status = futil.umask()
        self.assertTrue(status)
        #
        mock_umask.return_value = 0
        futil = FileUtil("somedir")
        FileUtil.orig_umask = 0
        status = futil.umask(1)
        self.assertTrue(status)
        self.assertEqual(FileUtil.orig_umask, 0)
        #
        mock_umask.return_value = 0
        futil = FileUtil("somedir")
        FileUtil.orig_umask = None
        status = futil.umask(1)
        self.assertTrue(status)
        self.assertEqual(FileUtil.orig_umask, 0)

    @mock.patch('udocker.utils.fileutil.FileUtil.mktmp')
    @mock.patch('udocker.utils.fileutil.FileUtil.mkdir')
    def test_18_mktmpdir(self, mock_umkdir, mock_umktmp):
        """Test FileUtil.mktmpdir()."""
        mock_umktmp.return_value = "/dir"
        mock_umkdir.return_value = True
        futil = FileUtil("somedir")
        status = futil.mktmpdir()
        self.assertEqual(status, "/dir")
        #
        mock_umktmp.return_value = "/dir"
        mock_umkdir.return_value = False
        futil = FileUtil("somedir")
        status = futil.mktmpdir()
        self.assertEqual(status, None)

    @mock.patch('udocker.utils.fileutil.FileUtil.mktmp')
    @mock.patch('udocker.utils.fileutil.FileUtil.mkdir')
    def test_19__is_safe_prefix(self, mock_umkdir, mock_umktmp):
        """Test FileUtil._is_safe_prefix()."""
        futil = FileUtil("somedir")
        FileUtil.safe_prefixes = []
        status = futil._is_safe_prefix("/AAA")
        self.assertFalse(status)
        #
        futil = FileUtil("somedir")
        FileUtil.safe_prefixes = ["/AAA", ]
        status = futil._is_safe_prefix("/AAA")
        self.assertTrue(status)

    def test_20_putdata(self):
        """Test FileUtil.putdata()"""
        futil = FileUtil("somefile")
        futil.filename = ""
        data = futil.putdata("qwerty")
        self.assertFalse(data)
        #
        with mock.patch(BUILTINS + '.open',
                        mock.mock_open()):
            data = FileUtil("somefile").putdata("qwerty")
            self.assertEqual(data, 'qwerty')

    @mock.patch('os.rename')
    def test_21_rename(self, mock_rename):
        """Test FileUtil.rename()."""
        status = FileUtil("somefile").rename("otherfile")
        self.assertTrue(status)

    @mock.patch('os.path.exists')
    def test_22_find_file_in_dir(self, mock_exists):
        """Test FileUtil.find_file_in_dir()."""
        file_list = []
        status = FileUtil("/dir").find_file_in_dir(file_list)
        self.assertEqual(status, "")
        #
        file_list = ["F1", "F2"]
        mock_exists.side_effect = [False, False]
        status = FileUtil("/dir").find_file_in_dir(file_list)
        self.assertEqual(status, "")
        #
        file_list = ["F1", "F2"]
        mock_exists.side_effect = [False, True]
        status = FileUtil("/dir").find_file_in_dir(file_list)
        self.assertEqual(status, "/dir/F2")

    @mock.patch('os.symlink')
    @mock.patch('os.remove')
    @mock.patch('os.stat')
    @mock.patch('os.chmod')
    @mock.patch('os.access')
    @mock.patch('os.path.dirname')
    @mock.patch('os.path.realpath')
    @mock.patch('os.readlink')
    def test_23__link_change_apply(self, mock_readlink,
                                   mock_realpath, mock_dirname,
                                   mock_access, mock_chmod, mock_stat,
                                   mock_remove, mock_symlink):
        """Actually apply the link convertion."""
        mock_readlink.return_value = "/HOST/DIR"
        mock_realpath.return_value = "/HOST/DIR"
        mock_access.return_value = True
        FileUtil("/con").\
            _link_change_apply("/con/lnk_new", "/con/lnk", False)
        self.assertTrue(mock_remove.called)
        self.assertTrue(mock_symlink.called)

        mock_access.return_value = False
        mock_remove.reset_mock()
        mock_symlink.reset_mock()
        FileUtil("/con").\
            _link_change_apply("/con/lnk_new", "/con/lnk", True)
        self.assertTrue(mock_chmod.called)
        self.assertTrue(mock_remove.called)
        self.assertTrue(mock_symlink.called)

    @mock.patch('os.symlink')
    @mock.patch('os.remove')
    @mock.patch('os.stat')
    @mock.patch('os.chmod')
    @mock.patch('os.access')
    @mock.patch('os.path.dirname')
    @mock.patch('os.path.realpath')
    @mock.patch('os.readlink')
    def test_24__link_set(self, mock_readlink, mock_realpath, mock_dirname,
                          mock_access, mock_chmod, mock_stat, mock_remove,
                          mock_symlink):
        """Test FileUtil._link_set()."""
        mock_readlink.return_value = "X"
        status = FileUtil("/con")._link_set("/con/lnk", "", "/con", False)
        self.assertFalse(status)
        #
        mock_readlink.return_value = "/con"
        status = FileUtil("/con")._link_set("/con/lnk", "", "/con", False)
        self.assertFalse(status)
        #
        mock_readlink.return_value = "/HOST/DIR"
        mock_realpath.return_value = "/HOST/DIR"
        mock_remove.reset_mock()
        mock_symlink.reset_mock()
        mock_chmod.reset_mock()
        status = FileUtil("/con")._link_set("/con/lnk", "", "/con", False)
        self.assertTrue(mock_remove.called)
        self.assertTrue(mock_symlink.called)
        self.assertFalse(mock_chmod.called)
        self.assertTrue(status)
        #
        mock_readlink.return_value = "/HOST/DIR"
        mock_realpath.return_value = "/HOST/DIR"
        mock_access.return_value = True
        mock_remove.reset_mock()
        mock_symlink.reset_mock()
        mock_chmod.reset_mock()
        status = FileUtil("/con")._link_set("/con/lnk", "", "/con", True)
        self.assertTrue(mock_remove.called)
        self.assertTrue(mock_symlink.called)
        self.assertFalse(mock_chmod.called)
        self.assertTrue(status)
        #
        mock_readlink.return_value = "/HOST/DIR"
        mock_realpath.return_value = "/HOST/DIR"
        mock_access.return_value = False
        mock_remove.reset_mock()
        mock_symlink.reset_mock()
        mock_chmod.reset_mock()
        status = FileUtil("/con")._link_set("/con/lnk", "", "/con", True)
        self.assertTrue(mock_remove.called)
        self.assertTrue(mock_symlink.called)
        self.assertTrue(mock_chmod.called)
        self.assertTrue(status)

    @mock.patch('os.symlink')
    @mock.patch('os.remove')
    @mock.patch('os.stat')
    @mock.patch('os.chmod')
    @mock.patch('os.access')
    @mock.patch('os.path.dirname')
    @mock.patch('os.path.realpath')
    @mock.patch('os.readlink')
    def test_25__link_restore(self, mock_readlink, mock_realpath, mock_dirname,
                              mock_access, mock_chmod, mock_stat, mock_remove,
                              mock_symlink):
        """Test FileUtil._link_restore()."""
        mock_readlink.return_value = "/con/AAA"
        status = FileUtil("/con")._link_restore("/con/lnk", "/con",
                                                        "/root", False)
        self.assertTrue(status)
        #
        mock_readlink.return_value = "/con/AAA"
        mock_symlink.reset_mock()
        mock_chmod.reset_mock()
        status = FileUtil("/con")._link_restore("/con/lnk", "/con",
                                                "/root", False)
        self.assertTrue(status)
        self.assertTrue(mock_symlink.called_with("/con/lnk", "/AAA"))
        #
        mock_readlink.return_value = "/root/BBB"
        mock_symlink.reset_mock()
        mock_chmod.reset_mock()
        status = FileUtil("/con")._link_restore("/con/lnk", "/con",
                                                "/root", False)
        self.assertTrue(status)
        self.assertTrue(mock_symlink.called_with("/con/lnk", "/BBB"))
        #
        mock_readlink.return_value = "/XXX"
        status = FileUtil("/con")._link_restore("/con/lnk", "/con",
                                                "/root", False)
        self.assertFalse(status)
        #
        mock_readlink.return_value = "/root/BBB"
        mock_symlink.reset_mock()
        mock_chmod.reset_mock()
        status = FileUtil("/con")._link_restore("/con/lnk", "/con",
                                                "/root", True)
        self.assertTrue(status)
        self.assertTrue(mock_symlink.called_with("/con/lnk", "/BBB"))
        self.assertFalse(mock_chmod.called)
        #
        mock_readlink.return_value = "/root/BBB"
        mock_access.return_value = False
        mock_symlink.reset_mock()
        mock_chmod.reset_mock()
        status = FileUtil("/con")._link_restore("/con/lnk", "",
                                                "/root", True)
        self.assertTrue(status)
        self.assertTrue(mock_symlink.called_with("/con/lnk", "/BBB"))
        self.assertTrue(mock_chmod.called)
        self.assertTrue(mock_remove.called)
        self.assertTrue(mock_symlink.called)

    @mock.patch('udocker.config.Config')
    @mock.patch('udocker.utils.fileutil.FileUtil._link_restore')
    @mock.patch('udocker.utils.fileutil.FileUtil._link_set')
    @mock.patch('udocker.msg.Msg')
    @mock.patch('udocker.utils.fileutil.FileUtil._is_safe_prefix')
    @mock.patch('os.lstat')
    @mock.patch('os.path.islink')
    @mock.patch('os.walk')
    @mock.patch('os.path.realpath')
    def test_26_links_conv(self, mock_realpath, mock_walk, mock_islink,
                           mock_lstat, mock_is_safe_prefix, mock_msg,
                           mock_link_set, mock_link_restore, mock_config):
        """Test FileUtil.links_conv()."""
        mock_realpath.return_value = "/ROOT"
        mock_is_safe_prefix.return_value = False
        status = FileUtil("/ROOT").links_conv(False, True, "")
        self.assertEqual(status, None)
        #
        mock_realpath.return_value = "/ROOT"
        mock_is_safe_prefix.return_value = True
        mock_walk.return_value = []
        status = FileUtil("/ROOT").links_conv(False, True, "")
        self.assertEqual(status, [])
        #
        mock_realpath.return_value = "/ROOT"
        mock_is_safe_prefix.return_value = True
        mock_walk.return_value = [("/", [], []), ]
        status = FileUtil("/ROOT").links_conv(False, True, "")
        self.assertEqual(status, [])
        #
        mock_realpath.return_value = "/ROOT"
        mock_is_safe_prefix.return_value = True
        mock_islink = False
        mock_walk.return_value = [("/", [], ["F1", "F2"]), ]
        status = FileUtil("/ROOT").links_conv(False, True, "")
        self.assertEqual(status, [])
        #
        mock_realpath.return_value = "/ROOT"
        mock_is_safe_prefix.return_value = True
        mock_islink = True
        mock_lstat.return_value.st_uid = 1
        Config = mock_config
        Config.uid = 0
        mock_walk.return_value = [("/", [], ["F1", "F2"]), ]
        status = FileUtil("/ROOT").links_conv(False, True, "")
        self.assertEqual(status, [])
        #
        mock_realpath.return_value = "/ROOT"
        mock_is_safe_prefix.return_value = True
        mock_islink = True
        mock_lstat.return_value.st_uid = 1
        mock_link_set.reset_mock()
        mock_link_restore.reset_mock()
        Config = mock_config
        Config.uid = 1
        mock_walk.return_value = [("/", [], ["F1", "F2"]), ]
        status = FileUtil("/ROOT").links_conv(False, True, "")
        self.assertTrue(mock_link_set.called)
        self.assertFalse(mock_link_restore.called)
        #
        mock_realpath.return_value = "/ROOT"
        mock_is_safe_prefix.return_value = True
        mock_islink = True
        mock_lstat.return_value.st_uid = 1
        mock_link_set.reset_mock()
        mock_link_restore.reset_mock()
        Config = mock_config
        Config.uid = 1
        mock_walk.return_value = [("/", [], ["F1", "F2"]), ]
        status = FileUtil("/ROOT").links_conv(False, False, "")
        self.assertFalse(mock_link_set.called)
        self.assertTrue(mock_link_restore.called)
