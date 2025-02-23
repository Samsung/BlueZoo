# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import os
import unittest


class AsyncProcessContext:

    def __init__(self, proc):
        self.proc = proc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.proc.terminate()
        await self.proc.wait()

    async def expect(self, data: str, timeout: float = 1.0):
        """Read output until expected text is found or timeout occurs."""
        output = b''
        needle = data.encode()
        start = asyncio.get_event_loop().time()
        while True:
            diff = timeout - (asyncio.get_event_loop().time() - start)
            if diff <= 0:
                raise TimeoutError(f"Timeout waiting for '{data}' in output")
            try:
                line = await asyncio.wait_for(self.proc.stdout.readline(),
                                              timeout=diff)
                print(line.decode(), end="")
                if not line:  # EOF
                    break
                output += line
                if needle in output:
                    break
            except asyncio.TimeoutError:
                continue
        return output.decode()

    async def write(self, data: str, end="\n"):
        self.proc.stdin.write((data + end).encode())
        await self.proc.stdin.drain()


async def client():
    """Start bluetoothctl in a subprocess and return a context manager."""
    proc = await asyncio.create_subprocess_exec(
        'bluetoothctl',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE)
    return AsyncProcessContext(proc)


class BluetoothMockTestCase(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):

        # Start a private D-Bus session and get the address
        self._bus = await asyncio.create_subprocess_exec(
            'dbus-daemon', '--session', '--print-address',
            stdout=asyncio.subprocess.PIPE)
        address = await self._bus.stdout.readline()

        # Update environment with D-Bus address
        os.environ['DBUS_SYSTEM_BUS_ADDRESS'] = address.strip().decode('utf-8')

        # Start mock with two adapters
        self._mock = await asyncio.create_subprocess_exec(
            'bluetoothd-mock',
            '--verbose',
            '-a', '00:00:00:01:00:00',
            '-a', '00:00:00:02:00:00')

        # Wait for mock to start
        await asyncio.sleep(0.5)

    async def asyncTearDown(self):
        self._mock.terminate()
        await self._mock.wait()
        self._bus.terminate()
        await self._bus.wait()

    async def test_scan(self):
        async with await client() as proc:

            await proc.write("select 00:00:00:01:00:00")
            await proc.write("power on")
            await proc.expect("Changing power on succeeded")
            await proc.write("discoverable on")
            await proc.expect("Changing discoverable on succeeded")

            await proc.write("select 00:00:00:02:00:00")
            await proc.write("power on")
            await proc.expect("Changing power on succeeded")

            await proc.write("scan on")
            await proc.expect("Discovery started")
            await proc.expect("Device 00:00:00:01:00:00")

    async def test_scan_le(self):
        async with await client() as proc:

            await proc.write("select 00:00:00:01:00:00")
            await proc.write("power on")
            await proc.expect("Changing power on succeeded")
            await proc.write("advertise on")
            await proc.expect("Advertising object registered")

            await proc.write("select 00:00:00:02:00:00")
            await proc.write("power on")
            await proc.expect("Changing power on succeeded")

            await proc.write("scan le")
            await proc.expect("Discovery started")
            await proc.expect("Device 00:00:00:01:00:00")

    async def test_advertise_le(self):
        async with await client() as proc:

            await proc.write("select 00:00:00:01:00:00")
            await proc.write("power on")
            await proc.expect("Changing power on succeeded")
            await proc.write("menu advertise")
            await proc.write("name BLE-Device")
            await proc.write("appearance 0x00a0")
            await proc.write("uuids 0xFFF1")
            await proc.write("service 0xFFF1 0xDE 0xAD 0xBE 0xEF")
            await proc.write("discoverable on")
            await proc.write("back")
            await proc.write("advertise peripheral")
            await proc.expect("Advertising object registered")

            await proc.write("select 00:00:00:02:00:00")
            await proc.write("power on")
            await proc.expect("Changing power on succeeded")

            await proc.write("scan le")
            await proc.expect("Discovery started")
            await proc.expect("Device 00:00:00:01:00:00")

            await proc.write("info 00:00:00:01:00:00")
            await proc.expect("Name: BLE-Device")
            await proc.expect("Appearance: 0x00a0")
            await proc.expect("ServiceData Key: 0xFFF1")


if __name__ == '__main__':
    asyncio.run(unittest.main())
