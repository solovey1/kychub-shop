from enum import IntFlag


class Role(IntFlag):
    OWNER = 1
    ADMIN = 2
    MANAGER = 4
    EXECUTOR = 8
    CAN_CATALOG = 16
    CAN_FINANCE = 32
    CAN_USERS = 64
    CAN_BROADCAST = 128
