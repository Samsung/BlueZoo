# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import unittest

from bluezoo.utils import BluetoothAddress, BluetoothClass, BluetoothUUID


class UtilsTestCase(unittest.TestCase):

    def test_address(self):
        self.assertEqual(BluetoothAddress("12:34:56:78:90:AB"), "12:34:56:78:90:AB")

    def test_address_invalid(self):
        with self.assertRaises(ValueError):
            BluetoothAddress("1234567890AB")

    def test_class(self):
        bt_class = BluetoothClass(1, 2, 3)
        self.assertEqual(bt_class, 0x006108)
        self.assertEqual(bt_class.major, BluetoothClass.Major.Computer)
        self.assertEqual(bt_class.minor, 2)
        self.assertEqual(bt_class.services, 3)

    def test_class_add_service(self):
        bt_class = BluetoothClass(BluetoothClass.Major.Phone)
        bt_class += BluetoothClass.Service.Networking
        self.assertEqual(bt_class, 0x020200)

    def test_class_del_service(self):
        bt_class = BluetoothClass(BluetoothClass.Major.Phone, 0,
                                  BluetoothClass.Service.Networking
                                  | BluetoothClass.Service.Audio)
        bt_class -= BluetoothClass.Service.Networking
        self.assertEqual(bt_class, 0x200200)

    def test_uuid(self):
        uuid = BluetoothUUID("12345678-0000-0000-0000-000000000000")
        self.assertEqual(uuid, "12345678-0000-0000-0000-000000000000")

    def test_uuid_16bit(self):
        uuid = BluetoothUUID("0x1234")
        self.assertEqual(uuid, "00001234-0000-1000-8000-00805f9b34fb")

    def test_uuid_invalid(self):
        with self.assertRaises(ValueError):
            BluetoothUUID("12345678-0000-0000")


if __name__ == '__main__':
    unittest.main()
