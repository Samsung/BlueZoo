# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging

from sdbus import DbusObjectManagerInterfaceAsync

from .controller import Controller
from .device import Device


class BluezMockService:

    def __init__(self, bus):
        self.manager = DbusObjectManagerInterfaceAsync()
        self.manager.export_to_dbus("/", bus)
        self.controllers: dict[int, Controller] = {}
        self.bus = bus

    def add_adapter(self, id: int, address: str):
        logging.info(f"Adding adapter {id} with address {address}")
        controller = Controller(self, id, address)
        path = controller.get_object_path()
        # The order of this exports is important. The object manager interface
        # exports the objects in the reversed order. The BlueZ CLI tool expects
        # the adapter to be "processed" first. So, the adapter object needs to
        # be exported as the last one.
        self.manager.export_with_manager(path, controller.iface_le_adv_manager, self.bus)
        self.manager.export_with_manager(path, controller.iface_agent_manager, self.bus)
        self.manager.export_with_manager(path, controller.iface_adapter, self.bus)
        self.controllers[id] = controller

    def del_adapter(self, id: int):
        logging.info(f"Removing adapter {id}")
        controller = self.controllers.pop(id)
        self.manager.remove_managed_object(controller.iface_le_adv_manager)
        self.manager.remove_managed_object(controller.iface_agent_manager)
        self.manager.remove_managed_object(controller.iface_adapter)

    def create_discovering_task(self, id: int):
        """Create a task that scans for devices on the adapter.

        The scan is performed every 10 seconds. The task checks for any other
        adapter which is powered and discoverable, and reports that adapter as
        a new device. The task runs indefinitely until it is cancelled.
        """
        async def task():
            while True:
                logging.info(f"Scanning for devices on adapter {id}")
                for controller in self.controllers.values():
                    if controller.id == id:
                        # Do not report our own controller.
                        continue
                    if not controller.powered:
                        continue
                    device = None
                    # Check if controller has enabled LE advertising.
                    if controller.advertisement_slots_active > 0:
                        adv = next(iter(controller.advertisements.values()))
                        adv_props = await adv.properties_get_all_dict()
                        # The LE advertisement discoverable property is not mandatory,
                        # but if present, it overrides the controller's property.
                        if not adv_props.get("Discoverable", controller.discoverable):
                            continue
                        device = Device(controller)
                        device.name_ = adv_props.get("LocalName", controller.name)
                        device.appearance = adv_props.get("Appearance", 0)
                        device.uuids = adv_props.get("ServiceUUIDs", [])
                        device.service_data = adv_props.get("ServiceData", {})
                    # Check if controller has enabled BR/EDR advertising.
                    elif controller.discoverable:
                        device = Device(controller)
                    if device is not None:
                        # Report the device (adapter) on our controller.
                        self.controllers[id].add_device(device)
                await asyncio.sleep(10)
        return asyncio.create_task(task())
