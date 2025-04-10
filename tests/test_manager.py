# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import os
import unittest


async def client(*args):
    """Run bluetoothctl in a subprocess and return output."""
    proc = await asyncio.create_subprocess_exec(
        'bluetoothctl', *args, stdout=asyncio.subprocess.PIPE)
    return await proc.stdout.read()


async def manager(method, *args):
    """Call method on BlueZoo manager and return output."""
    proc = await asyncio.create_subprocess_exec(
        'dbus-send',
        '--system',
        '--print-reply',
        '--type=method_call',
        '--dest=org.bluez',
        '/org/bluezoo',
        'org.bluezoo.Manager1.' + method,
        *args, stdout=asyncio.subprocess.PIPE)
    return await proc.stdout.read()


class BlueZooManagerTestCase(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):

        # Start a private D-Bus session and get the address.
        self._bus = await asyncio.create_subprocess_exec(
            'dbus-daemon', '--session', '--print-address',
            stdout=asyncio.subprocess.PIPE)
        address = await self._bus.stdout.readline()

        # Update environment with D-Bus address.
        os.environ['DBUS_SYSTEM_BUS_ADDRESS'] = address.strip().decode('utf-8')

        # Start mock with two adapters.
        self._mock = await asyncio.create_subprocess_exec(
            "bluezoo",
            "--verbose",
            "--adapter=00:00:00:11:11:11",
            "--adapter=00:00:00:22:22:22",
            stderr=asyncio.subprocess.PIPE)

        # Wait for the adapter to appear.
        await self._mock.stderr.readline()

        async def forward():
            while True:
                line = await self._mock.stderr.readline()
                os.sys.stderr.buffer.write(line)
        self._mock_forwarder = asyncio.create_task(forward())

    async def asyncTearDown(self):
        self._mock_forwarder.cancel()
        self._mock.terminate()
        await self._mock.wait()
        self._bus.terminate()
        await self._bus.wait()

    async def test_add_adapter(self):

        reply = await manager("AddAdapter", "byte:5", "string:00:00:00:00:00:55")
        self.assertEqual(len(reply.splitlines()), 2)
        self.assertIn(b'object path "/org/bluez/hci5"', reply)

        output = await client("list")
        self.assertIn(b"Controller 00:00:00:11:11:11", output)
        self.assertIn(b"Controller 00:00:00:22:22:22", output)
        self.assertIn(b"Controller 00:00:00:00:00:55", output)

    async def test_remove_adapter(self):

        reply = await manager("RemoveAdapter", "byte:1")
        self.assertEqual(len(reply.splitlines()), 1)

        output = await client("list")
        self.assertIn(b"Controller 00:00:00:11:11:11", output)
        self.assertNotIn(b"Controller 00:00:00:22:22:22", output)


if __name__ == '__main__':
    asyncio.run(unittest.main())
