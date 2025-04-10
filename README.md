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

## BlueZoo Manager Interface

BlueZoo provides a D-Bus interface for managing the mock service. The manager
interface is available at `/org/bluezoo`. It allows to dynamically create and
destroy adapters.

Remove adapter `hci0`:

```sh
gdbus call --system \
    --dest org.bluez \
    --object-path /org/bluezoo \
    --method org.bluezoo.Manager1.RemoveAdapter
    0
```

Add adapter `hci0` with address `00:00:00:11:11:11`:

```sh
gdbus call --system \
    --dest org.bluez \
    --object-path /org/bluezoo \
    --method org.bluezoo.Manager1.AddAdapter
    0 '00:00:00:11:11:11'
```

## BlueZ Interfaces

| Name                                   | Supported | Notes |
| :---                                   | :-------: | :---  |
| org.bluez.Adapter1                     |    ✅     |       |
| org.bluez.AdminPolicySet1              |    -      |       |
| org.bluez.AdminPolicyStatus1           |    -      |       |
| org.bluez.AdvertisementMonitorManager1 |    -      |       |
| org.bluez.AdvertisementMonitor1        |    -      |       |
| org.bluez.AgentManager1                |    ✅     |       |
| org.bluez.Agent1                       |    ✅     |       |
| org.bluez.BatteryProviderManager1      |    -      |       |
| org.bluez.BatteryProvider1             |    -      |       |
| org.bluez.Battery1                     |    -      |       |
| org.bluez.Device1                      |    ✅     |       |
| org.bluez.DeviceSet1                   |    -      |       |
| org.bluez.GattCharacteristic1          |    ✅     |       |
| org.bluez.GattDescriptor1              |    ✅     |       |
| org.bluez.GattManager1                 |    ✅     |       |
| org.bluez.GattProfile1                 |    -      |       |
| org.bluez.GattService1                 |    ✅     |       |
| org.bluez.Input1                       |    -      |       |
| org.bluez.LEAdvertisement1             |    ✅     |       |
| org.bluez.LEAdvertisingManager1        |    ✅     |       |
| org.bluez.MediaAssistant1              |    -      |       |
| org.bluez.MediaControl1                |    -      |       |
| org.bluez.MediaEndpoint1               |    -      |       |
| org.bluez.MediaFolder1                 |    -      |       |
| org.bluez.MediaItem1                   |    -      |       |
| org.bluez.MediaPlayer1                 |    -      |       |
| org.bluez.Media1                       |    -      |       |
| org.bluez.MediaTransport1              |    -      |       |
| org.bluez.Network1                     |    -      |       |
| org.bluez.NetworkServer1               |    -      |       |
| org.bluez.obex.AgentManager1           |    -      |       |
| org.bluez.obex.Agent1                  |    -      |       |
| org.bluez.obex.Client1                 |    -      |       |
| org.bluez.obex.FileTransfer1           |    -      |       |
| org.bluez.obex.Image1                  |    -      |       |
| org.bluez.obex.MessageAccess1          |    -      |       |
| org.bluez.obex.Message1                |    -      |       |
| org.bluez.obex.ObjectPush1             |    -      |       |
| org.bluez.obex.PhonebookAccess1        |    -      |       |
| org.bluez.obex.Session1                |    -      |       |
| org.bluez.obex.Synchronization1        |    -      |       |
| org.bluez.obex.Transfer1               |    -      |       |
| org.bluez.ProfileManager1              |    -      |       |
| org.bluez.Profile1                     |    -      |       |

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING](CONTRIBUTING.md)
guidelines for more information.

## License

This project is licensed under the GNU General Public License v2.0 - see the
[LICENSE](LICENSE) file for details.
