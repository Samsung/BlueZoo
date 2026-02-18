<!--
SPDX-FileCopyrightText: 2025 BlueZoo developers
SPDX-License-Identifier: GPL-2.0-only
-->

# BlueZoo

[![REUSE Status](https://api.reuse.software/badge/github.com/Samsung/BlueZoo)](https://api.reuse.software/info/github.com/Samsung/BlueZoo)
[![Code Coverage](https://codecov.io/gh/Samsung/BlueZoo/graph/badge.svg?token=1W6GB983WL)](https://codecov.io/gh/Samsung/BlueZoo)

BlueZoo is a BlueZ D-Bus API mock, designed to test applications for BlueZ
integration.

## Introduction

BlueZoo provides "org.bluez" D-Bus service which mocks the behavior of the real
BlueZ service. It allows to create multiple Bluetooth adapters (HCIs) within a
single "org.bluez" D-Bus service. Each adapter can communicate with each other
just like it would happen with real adapters connected to the same host.

Such setup allows developers to test BlueZ integration in their applications
without needing actual Bluetooth hardware. Additionally, BlueZoo runs entirely
in user space (it does not require any special kernel modules or permissions)
to allow easy integration with various testing environments, including CI/CD
pipelines like GitHub Actions, GitLab CI, Jenkins, etc.

![demo](https://github.com/user-attachments/assets/0751a02a-c901-4afc-9cd3-6e1998d71cf2)

## Installation

BlueZoo is available as a Python package on PyPI and can be installed using
`pip`:

```sh
pip install bluezoo
```

## Usage

By default, BlueZoo creates "org.bluez" service on the D-Bus system bus. In
order to use an isolated testing environment, it is recommended to run a local
D-Bus bus and set `DBUS_SYSTEM_BUS_ADDRESS` environment variable to point to
the local bus.

1. Start local D-Bus bus:

   ```sh
   dbus-daemon --session --print-address
   ```

2. Set `DBUS_SYSTEM_BUS_ADDRESS` environment variable:

   ```sh
   export DBUS_SYSTEM_BUS_ADDRESS=<BUS-ADDRESS-FROM-STEP-1>
   ```

3. Run BlueZoo with pre-defined adapters:

   ```sh
   bluezoo --auto-enable --adapter 00:11:22:33:44:55
   ```

4. Run your application and test BlueZ integration. For example, you can use
   `bluetoothctl`, which is a command-line utility provided by BlueZ, to
   interact with BlueZoo service:

   ```console
   $ bluetoothctl show 00:11:22:33:44:55
   Controller 00:11:22:33:44:55 (public)
           Name: Alligator's Android
           Powered: yes
           Discoverable: no
           Discovering: no
   ```

## BlueZoo Manager Interface

BlueZoo provides a D-Bus interface for managing the mock service. The manager
interface is available at `/org/bluezoo`. It allows to dynamically create and
destroy adapters.

Add adapter `hci8` with address `00:00:00:11:11:11`:

```sh
gdbus call --system \
    --dest org.bluez \
    --object-path /org/bluezoo \
    --method org.bluezoo.Manager1.AddAdapter
    8 '00:00:00:11:11:11'
```

Remove adapter `hci8`:

```sh
gdbus call --system \
    --dest org.bluez \
    --object-path /org/bluezoo \
    --method org.bluezoo.Manager1.RemoveAdapter
    8
```

## BlueZ Interfaces

The list of supported D-Bus interfaces can be found in the
[INTERFACES.md](INTERFACES.md) file.

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING](CONTRIBUTING.md)
guidelines for more information.

## License

This project is licensed under the GNU General Public License v2.0 - see the
[LICENSE](LICENSE) file for details.
