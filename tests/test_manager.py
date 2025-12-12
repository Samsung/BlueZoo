#!/usr/bin/env -S python3 -X faulthandler
# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import os
import unittest

from bluezoo import bluezoo


async def client(*args):
    """Run bluetoothctl in a subprocess and return output."""
    proc = await asyncio.create_subprocess_exec(
        "bluetoothctl", *args, stdout=asyncio.subprocess.PIPE)
    assert proc.stdout is not None, "Client process's stdout is None"
    return await proc.stdout.read()


async def manager(method, *args):
    """Call method on BlueZoo manager and return output."""
    proc = await asyncio.create_subprocess_exec(
        "dbus-send",
        "--system",
        "--print-reply",
        "--type=method_call",
        "--dest=org.bluez",
        "/org/bluezoo",
        "org.bluezoo.Manager1." + method,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    return await proc.communicate()


class BlueZooManagerTestCase(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):

        # Start a private D-Bus session and get the address.
        self._bus = await asyncio.create_subprocess_exec(
            "dbus-daemon", "--session", "--print-address",
            stdout=asyncio.subprocess.PIPE)
        assert self._bus.stdout is not None, "D-Bus daemon stdout is None"
        address = await self._bus.stdout.readline()

        # Update environment with D-Bus address.
        os.environ["DBUS_SYSTEM_BUS_ADDRESS"] = address.strip().decode("utf-8")

        # Start mock with two adapters.
        await bluezoo.startup(
            adapters=["00:00:00:11:11:11", "00:00:00:22:22:22"])

    async def asyncTearDown(self):
        self._bus.terminate()
        await self._bus.wait()

    async def test_add_adapter(self):

        out = await manager("AddAdapter", "byte:5", "string:00:00:00:00:00:55")
        self.assertEqual(len(out[0].splitlines()), 2)
        self.assertIn(b'object path "/org/bluez/hci5"', out[0])

        output = await client("list")
        self.assertIn(b"Controller 00:00:00:11:11:11", output)
        self.assertIn(b"Controller 00:00:00:22:22:22", output)
        self.assertIn(b"Controller 00:00:00:00:00:55", output)

    async def test_add_adapter_invalid(self):
        out = await manager("AddAdapter", "byte:1", "string:00:00:00:11:11:11")
        self.assertIn(b"org.bluezoo.Error.AlreadyExists", out[1])

    async def test_remove_adapter(self):

        out = await manager("RemoveAdapter", "byte:1")
        self.assertEqual(len(out[0].splitlines()), 1)

        output = await client("list")
        self.assertIn(b"Controller 00:00:00:11:11:11", output)
        self.assertNotIn(b"Controller 00:00:00:22:22:22", output)

    async def test_remove_adapter_invalid(self):
        out = await manager("RemoveAdapter", "byte:5")
        self.assertIn(b"org.bluezoo.Error.DoesNotExist", out[1])


if __name__ == "__main__":
    unittest.main()
