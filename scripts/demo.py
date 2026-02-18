#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only
#
# This script demonstrates BlueZoo by simulating a typical Bluetooth LE use
# casa where a client connects to a GATT server. It uses TMUX to multiplex
# "terminals" in a single viewport.
#
# In order to record the demo, one can use asciinema as follows:
#
# 1. Record the demo:
#    > asciinema rec --cols 150 --rows 35 --command scripts/demo.py demo.cast
# 2. Remove last two frames from the recording (TMUX exit):
#    > sed -i '$d' demo.cast && sed -i '$d' demo.cast
# 3. Convert the recording to GIF using agg:
#    > agg --theme monokai demo.cast demo.gif


import asyncio
import os
import tempfile
from argparse import ArgumentParser


class DBusNamespace:
    """Context manager to create an isolated D-Bus session."""

    async def __aenter__(self):
        self.proc = await asyncio.create_subprocess_exec(
            "dbus-daemon", "--session", "--print-address",
            stdout=asyncio.subprocess.PIPE)
        assert self.proc.stdout is not None, "D-Bus daemon process's stdout is None"
        self.address = (await self.proc.stdout.readline()).decode().strip()
        # Export the D-Bus address as a system bus address.
        os.environ["DBUS_SYSTEM_BUS_ADDRESS"] = self.address

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.proc.terminate()
        await self.proc.wait()


class TmuxSession:
    """Context manager to create a TMUX session for the demo."""

    def __init__(self, config: str, name="demo", keep=False):
        self.config = config
        self.name = name
        self.keep = keep

    async def __aenter__(self):
        with tempfile.NamedTemporaryFile(mode="w") as f:
            f.write(self.config)
            f.flush()
            # Create a new tmux session for the demo.
            self.proc = await asyncio.create_subprocess_exec(
                "tmux", "-L", self.name, "-f", f.name, "attach")
            # Wait a bit to ensure the tmux session is up and running.
            await asyncio.sleep(0.5)
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self.keep:
            # Terminate TMUX server by killing the session.
            proc = await asyncio.create_subprocess_exec(
                "tmux", "-L", self.name, "kill-session")
            await proc.wait()
        await self.proc.wait()

    async def type(self, text, pane=0, end="C-m", delay=0.01):
        """Simulate typing text with a delay between characters."""
        for char in text:
            proc = await asyncio.create_subprocess_exec(
                "tmux", "-L", self.name, "send-keys", "-t", str(pane), "--", char)
            await proc.wait()
            await asyncio.sleep(delay)
        if end:
            proc = await asyncio.create_subprocess_exec(
                "tmux", "-L", self.name, "send-keys", "-t", str(pane), end)
            await proc.wait()


async def demo(keep=False):

    # Setup TMUX layout for the demo.
    CONFIG = """
    # Enable mouse support for easier debugging.
    set-option -g mouse on
    # Do not use colors for pane borders.
    set-option -g pane-border-style fg=default
    set-option -g pane-active-border-style fg=default
    # Disable the status bar for a cleaner demo.
    set-option -g status off
    # Create a new session for the demo.
    new-session
    # Setup layout with top pane for the BlueZoo process.
    split-window -v -l 60%
    # Split bottom pane in half for GATT server and client.
    split-window -h -l 55%
    # Split bottom left pane for GATT server and advertiser.
    select-pane -t 1
    split-window -v
    # Focus the bottom right pane.
    select-pane -t 3
    """

    # Set a custom user name for the demo.
    os.environ["USER"] = "bluezoo"
    # Customize LP settings for the demo.
    os.environ["LP_ENABLE_GIT"] = "0"
    os.environ["LP_ENABLE_PATH"] = "0"
    os.environ["LP_ENABLE_RUNTIME"] = "0"
    os.environ["LP_ENABLE_SHLVL"] = "0"
    os.environ["LP_MARK_DISABLED"] = "$"

    async with DBusNamespace(), TmuxSession(config=CONFIG, keep=keep) as tmux:

        # Run BlueZoo in the top pane.
        await tmux.type(
            "bluezoo"
            " --auto-enable"
            " --scan-interval=30"
            " --adapter=00:00:00:11:11:11:SERVER"
            " --adapter=00:00:00:22:22:22:CLIENT",
            pane=0)
        # Wait a bit for BlueZoo to initialize.
        await asyncio.sleep(1)

        # Run a GATT server in the bottom left pane.
        await tmux.type(
            "tests/gatt/server.py"
            " --primary"
            " --service=0xFFF6"
            " --char=0x1234 "
            " --flag=read"
            # "Hello World!" in hex.
            " --value=48656c6c6f20576f726c6421",
            pane=1)
        # Wait a bit for the GATT server to start up.
        await asyncio.sleep(1)
        # Run LE advertiser in bottom left pane.
        await tmux.type(
            "tests/gatt/advertise.py"
            " --service=0xFFF6"
            " --discoverable",
            pane=2)
        # Wait a bit for the advertiser to start up.
        await asyncio.sleep(1)

        # Run BlueZ client in the bottom right pane.
        await tmux.type(
            "bluetoothctl --agent=NoInputNoOutput",
            pane=3)
        await asyncio.sleep(1)
        await tmux.type(
            "select 00:00:00:22:22:22",
            pane=3)
        await asyncio.sleep(2)
        await tmux.type(
            "scan le",
            pane=3)
        await asyncio.sleep(2)
        await tmux.type(
            "connect 00:00:00:11:11:11",
            pane=3)
        await asyncio.sleep(2)
        await tmux.type(
            "gatt.list-attributes",
            pane=3)
        await asyncio.sleep(2)
        await tmux.type(
            "gatt.select-attribute 1234",
            pane=3)
        await asyncio.sleep(2)
        await tmux.type(
            "gatt.read",
            pane=3)
        await asyncio.sleep(2)


parser = ArgumentParser()
parser.add_argument("--keep", action="store_true",
                    help="keep the TMUX session open after the demo")

args = parser.parse_args()
loop = asyncio.new_event_loop()
loop.run_until_complete(demo(args.keep))
