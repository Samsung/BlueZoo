# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import contextlib
import os
import unittest


class AsyncProcessContext:

    def __init__(self, proc):
        self.proc = proc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        with contextlib.suppress(ProcessLookupError):
            self.proc.terminate()
        if x := await self.proc.wait():
            raise RuntimeError(f"Process exited with status {x}")

    async def __read(self, readline=False):
        if readline:
            return await self.proc.stdout.readline()
        return await self.proc.stdout.read(4096)

    async def expect(self, data: str, timeout=1.0, eol=True):
        """Read output until expected text is found or timeout occurs."""
        output = b''
        needle = data.encode()
        start = asyncio.get_event_loop().time()
        while True:
            diff = timeout - (asyncio.get_event_loop().time() - start)
            if diff <= 0:
                raise TimeoutError(f"Timeout waiting for '{data}' in output")
            try:
                line = await asyncio.wait_for(self.__read(eol), timeout=diff)
                os.sys.stdout.buffer.write(line)
                os.sys.stdout.flush()
                if not line:  # EOF
                    break
                output += line
                if needle in output:
                    break
            except asyncio.TimeoutError:
                continue
        return output.decode(errors='ignore')

    async def write(self, data: str, end="\n"):
        self.proc.stdin.write((data + end).encode())
        await self.proc.stdin.drain()


async def client(*args, no_agent=False):
    """Start bluetoothctl in a subprocess and return a context manager."""
    proc = AsyncProcessContext(await asyncio.create_subprocess_exec(
        'bluetoothctl', *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE))
    if no_agent:
        # By default BlueZ client registers an agent on startup. However, we
        # do not want to use this agent because it requires user interaction.
        # Before we can unregister it, we need to wait for it to appear.
        await proc.expect("Agent registered")
        await proc.write("agent off")
        await proc.expect("Agent unregistered")
    return proc


class BluetoothMockTestCase(unittest.IsolatedAsyncioTestCase):

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
            "--auto-enable",
            "--scan-interval=1",
            "--adapter=00:00:00:11:11:11",
            "--adapter=00:00:00:22:22:22",
            stderr=asyncio.subprocess.PIPE)

        # Wait for log message about adding adapter 00:00:00:11:11:11
        await self._mock.stderr.readline()
        # Wait for log message about adding adapter 00:00:00:22:22:22
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

    async def test_agent(self):
        async with await client(no_agent=True) as proc:

            # Without an agent, pairing is not possible.
            await proc.expect("Controller 00:00:00:11:11:11 Pairable: no")
            await proc.expect("Controller 00:00:00:22:22:22 Pairable: no")

            await proc.write("agent NoInputNoOutput")
            await proc.expect("Agent registered")
            await proc.expect("Controller 00:00:00:11:11:11 Pairable: yes")
            await proc.expect("Controller 00:00:00:22:22:22 Pairable: yes")

            await proc.write("default-agent")
            await proc.expect("Default agent request successful")

    async def test_discoverable(self):
        async with await client() as proc:

            await proc.write("select 00:00:00:11:11:11")
            await proc.write("discoverable on")
            await proc.expect("Changing discoverable on succeeded")

            # Verify that the timeout works as expected.
            await proc.write("discoverable-timeout 1")
            await proc.expect("Discoverable: no", timeout=1.5)

    async def test_scan(self):
        async with await client() as proc:

            await proc.write("select 00:00:00:11:11:11")
            await proc.write("discoverable on")
            await proc.expect("Changing discoverable on succeeded")

            await proc.write("select 00:00:00:22:22:22")
            await proc.write("scan on")
            await proc.expect("Discovery started")
            await proc.expect("Device 00:00:00:11:11:11")

    async def test_scan_le(self):
        async with await client() as proc:

            await proc.write("select 00:00:00:11:11:11")
            await proc.write("advertise on")
            await proc.expect("Advertising object registered")

            await proc.write("select 00:00:00:22:22:22")
            await proc.write("scan le")
            await proc.expect("Discovery started")
            await proc.expect("Device 00:00:00:11:11:11")

    async def test_advertise_le(self):
        async with await client() as proc:

            await proc.write("select 00:00:00:11:11:11")
            await proc.write("advertise.name BLE-Device")
            await proc.write("advertise.appearance 0x00a0")
            await proc.write("advertise.uuids 0xFFF1")
            await proc.write("advertise.service 0xFFF1 0xDE 0xAD 0xBE 0xEF")
            await proc.write("advertise.discoverable on")
            await proc.write("advertise peripheral")
            await proc.expect("Advertising object registered")

            await proc.write("select 00:00:00:22:22:22")
            await proc.write("scan le")
            await proc.expect("Discovery started")
            await proc.expect("Device 00:00:00:11:11:11")

            await proc.write("info 00:00:00:11:11:11")
            await proc.expect("Name: BLE-Device")
            await proc.expect("Appearance: 0x00a0")
            await proc.expect("ServiceData.0000fff1-0000-1000-8000-00805f9b34fb:")

            # Update the advertisement data and verify that the changes
            # are visible to the scanner.
            await proc.write("select 00:00:00:11:11:11")
            await proc.write("advertise.name BLE-Device-42")

            await proc.write("select 00:00:00:22:22:22")
            # The scan interval is 1 second, so we need to wait for the
            # scanner to pick up the new advertisement data.
            await proc.expect("Name: BLE-Device-42", timeout=1.5)

    async def test_gatt_application(self):
        async with await client() as proc:

            await proc.write("gatt.register-service 0xF100")
            await proc.expect("Primary (yes/no):", eol=False)
            await proc.write("yes")

            await proc.write("gatt.register-characteristic 0xF110 read,write")
            await proc.expect("Enter value:", eol=False)
            await proc.write("0x43 0x48 0x41 0x52 0x41 0x43 0x54 0x45 0x52")

            await proc.write("gatt.register-characteristic 0xF120 read,notify")
            await proc.expect("Enter value:", eol=False)
            await proc.write("0x05 0x06 0x07 0x08")

            await proc.write("gatt.register-descriptor 0xF121 read")
            await proc.expect("Enter value:", eol=False)
            await proc.write("0x44 0x45 0x53 0x43 0x52 0x49 0x50 0x54 0x4F 0x52")

            await proc.write("gatt.register-application")
            # Verify that the service handle was assigned.
            await proc.expect("/org/bluez/app/service0")
            # Verify that new service was added to the adapter.
            await proc.expect("UUIDs: 0000f100-0000-1000-8000-00805f9b34fb")

    async def test_pair(self):
        async with await client(no_agent=True) as proc:

            # Register agent for auto-pairing process.
            await proc.write("agent NoInputNoOutput")
            await proc.expect("Agent registered")

            await proc.write("select 00:00:00:11:11:11")
            await proc.write("discoverable on")
            await proc.expect("Changing discoverable on succeeded")

            await proc.write("select 00:00:00:22:22:22")
            await proc.write("scan on")
            await proc.expect("Discovery started")
            await proc.expect("Device 00:00:00:11:11:11")

            await proc.write("pair 00:00:00:11:11:11")
            await proc.expect("Pairing successful")

            # Verify that the device is paired.
            await proc.write("info 00:00:00:11:11:11")
            await proc.expect("Device 00:00:00:11:11:11 (public)")
            await proc.expect("Paired: yes")

            await proc.write("select 00:00:00:11:11:11")
            # Verify that the device is paired.
            await proc.write("info 00:00:00:22:22:22")
            await proc.expect("Device 00:00:00:22:22:22 (public)")
            await proc.expect("Paired: yes")

    async def test_connect(self):
        async with await client(no_agent=True) as proc:

            # Register agent for auto-pairing process.
            await proc.write("agent NoInputNoOutput")
            await proc.expect("Agent registered")

            await proc.write("select 00:00:00:11:11:11")
            await proc.write("discoverable on")
            await proc.expect("Changing discoverable on succeeded")

            await proc.write("select 00:00:00:22:22:22")
            await proc.write("scan on")
            await proc.expect("Discovery started")
            await proc.expect("Device 00:00:00:11:11:11")

            await proc.write("connect 00:00:00:11:11:11")
            # The device is not trusted, so we need to accept the pairing.
            await proc.expect("[agent] Accept pairing (yes/no):", eol=False)
            await proc.write("yes")

            await proc.expect("Connection successful")

            # Verify that the device is connected.
            await proc.write("info 00:00:00:11:11:11")
            await proc.expect("Device 00:00:00:11:11:11 (public)")
            await proc.expect("Connected: yes")

            await proc.write("select 00:00:00:11:11:11")
            # Verify that the device is connected.
            await proc.write("info 00:00:00:22:22:22")
            await proc.expect("Device 00:00:00:22:22:22 (public)")
            await proc.expect("Connected: yes")

    async def test_disconnect(self):
        async with await client(no_agent=True) as proc:

            # Register agent for auto-pairing process.
            await proc.write("agent NoInputNoOutput")
            await proc.expect("Agent registered")

            await proc.write("select 00:00:00:11:11:11")
            await proc.write("discoverable on")

            await proc.write("select 00:00:00:22:22:22")
            await proc.write("scan on")
            await proc.expect("Device 00:00:00:11:11:11")

            await proc.write("connect 00:00:00:11:11:11")
            # The device is not trusted, so we need to accept the pairing.
            await proc.expect("[agent] Accept pairing (yes/no):", eol=False)
            await proc.write("yes")

            await proc.expect("Connection successful")

            # Remove the device - this should trigger disconnection.
            await proc.write("remove 00:00:00:11:11:11")
            await proc.expect("Device has been removed")

            # The device is not longer available on our side, but verify that
            # on the other side (the other adapter) our device is disconnected.
            await proc.write("select 00:00:00:11:11:11")
            await proc.write("info 00:00:00:22:22:22")
            await proc.expect("Connected: no")

    async def test_connect_gatt(self):
        async with await client() as proc:

            await proc.write("select 00:00:00:11:11:11")
            # Setup GATT primary service.
            await proc.write("gatt.register-service 0xF100")
            await proc.expect("Primary (yes/no):", eol=False)
            await proc.write("yes")
            # Setup GATT characteristic with read/write permissions.
            await proc.write("gatt.register-characteristic 0xF110 read,write")
            await proc.expect("Enter value:", eol=False)
            await proc.write("0x43 0x48 0x41 0x52 0x41 0x43 0x54 0x45 0x52")
            # Setup GATT characteristic with read/notify permissions.
            await proc.write("gatt.register-characteristic 0xF120 read,notify")
            await proc.expect("Enter value:", eol=False)
            await proc.write("0x52 0x45 0x41 0x44")
            # Setup GATT descriptor with read/write permissions.
            await proc.write("gatt.register-descriptor 0xF121 read")
            await proc.expect("Enter value:", eol=False)
            await proc.write("0x44 0x45 0x53 0x43")
            # Register GATT application.
            await proc.write("gatt.register-application")
            # Verify that new service was added to the adapter.
            await proc.expect("UUIDs: 0000f100-0000-1000-8000-00805f9b34fb")
            # Advertising GATT service on first adapter.
            await proc.write("advertise.uuids 0xF100")
            await proc.write("advertise.discoverable on")
            await proc.write("advertise peripheral")
            await proc.expect("Advertising object registered")

            # Scan for the GATT service on second adapter.
            await proc.write("select 00:00:00:22:22:22")
            await proc.write("scan le")
            await proc.expect("Discovery started")
            await proc.expect("Device 00:00:00:11:11:11")

            # Connect to the GATT service.
            await proc.write("connect 00:00:00:11:11:11")
            await proc.expect("Connection successful")

            # Verify that we can read 0xF110 characteristic.
            await proc.write("gatt.select-attribute 0000f110-0000-1000-8000-00805f9b34fb")
            await proc.write("gatt.read")
            await proc.expect("CHARACTER")
            # Verify error when reading at invalid offset.
            await proc.write("gatt.read 32")
            await proc.expect("Failed to read: org.bluez.Error.InvalidOffset")
            # Verify that we can write at specified offset.
            await proc.write("gatt.write '0x61 0x63 0x74' 4")
            await proc.expect("act")
            # Verify that the value was correctly written.
            await proc.write("gatt.read")
            await proc.expect("CHARact")

            # Verify notifications from 0xF120 characteristic.
            await proc.write("gatt.select-attribute 0000f120-0000-1000-8000-00805f9b34fb")
            await proc.write("gatt.notify on")
            await proc.expect("Notify started")

            # Verify that we can read 0xF121 descriptor.
            await proc.write("gatt.select-attribute 0000f121-0000-1000-8000-00805f9b34fb")
            await proc.write("gatt.read")
            await proc.expect("DESC")
            # Verify that we can write at specified offset.
            await proc.write("gatt.write '0x4f 0x4e 0x45' 1")
            # Verify that the value was correctly written.
            await proc.write("gatt.read")
            await proc.expect("DONE")


if __name__ == '__main__':
    asyncio.run(unittest.main())
