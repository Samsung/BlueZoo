# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import sdbus


class DBusBluezAlreadyConnectedError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.AlreadyConnected"


class DBusBluezAlreadyExistsError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.AlreadyExists"


class DBusBluezAuthenticationCanceledError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.AuthenticationCanceled"


class DBusBluezAuthenticationFailedError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.AuthenticationFailed"


class DBusBluezAuthenticationRejectedError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.AuthenticationRejected"


class DBusBluezAuthenticationTimeoutError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.AuthenticationTimeout"


class DBusBluezCanceledError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.Canceled"


class DBusBluezConnectionAttemptFailedError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.ConnectionAttemptFailed"


class DBusBluezDoesNotExistError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.DoesNotExist"


class DBusBluezFailedError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.Failed"


class DBusBluezHealthErrorError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.HealthError"


class DBusBluezImproperlyConfiguredError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.ImproperlyConfigured"


class DBusBluezInProgressError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.InProgress"


class DBusBluezInvalidArgumentsError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.InvalidArguments"


class DBusBluezInvalidLengthError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.InvalidLength"


class DBusBluezInvalidOffsetError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.InvalidOffset"


class DBusBluezInvalidValueLengthError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.InvalidValueLength"


class DBusBluezNotAcquiredError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.NotAcquired"


class DBusBluezNotAllowedError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.NotAllowed"


class DBusBluezNotAuthorizedError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.NotAuthorized"


class DBusBluezNotAvailableError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.NotAvailable"


class DBusBluezNotConnectedError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.NotConnected"


class DBusBluezNotFoundError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.NotFound"


class DBusBluezNotPermittedError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.NotPermitted"


class DBusBluezNotReadyError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.NotReady"


class DBusBluezNotSupportedError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.NotSupported"


class DBusBluezOutOfRangeError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.OutOfRange"


class DBusBluezRejectedError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluez.Error.Rejected"
