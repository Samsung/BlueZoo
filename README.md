# BlueZoo

BlueZoo is a BlueZ D-Bus API mock, designed to test applications for BlueZ
integration.

## Introduction

BlueZoo provides "org.bluez" D-Bus service, allowing developers to test BlueZ
integration in their applications without needing actual Bluetooth hardware.
It runs entirely in user space, so it can be easily integrated into automated
test suites on various CI/CD pipelines.

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

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING](CONTRIBUTING.md)
guidelines for more information.

## License

This project is licensed under the GNU General Public License v2.0 - see the
[LICENSE](LICENSE) file for details.
