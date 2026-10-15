from ctypes import cast, POINTER

from comtypes import CLSCTX_ALL
from pycaw.pycaw import (
    AudioUtilities,
    IAudioEndpointVolume,
)


class VolumeTools:

    def _get_volume_interface(self):

        devices = AudioUtilities.GetSpeakers()

        # Recent pycaw returns AudioDevice; older releases return IMMDevice.
        if hasattr(type(devices), "EndpointVolume"):
            return devices.EndpointVolume

        interface = devices.Activate(
            IAudioEndpointVolume._iid_,
            CLSCTX_ALL,
            None
        )

        return cast(
            interface,
            POINTER(IAudioEndpointVolume)
        )

    def set_volume(self, level: int) -> str:

        level = max(
            0,
            min(100, level)
        )

        volume = self._get_volume_interface()

        volume.SetMasterVolumeLevelScalar(
            level / 100,
            None
        )

        return f"Volume set to {level} percent."

    def change_volume(
        self,
        direction: str,
        amount: int = 10
    ) -> str:

        volume = self._get_volume_interface()

        current = (
            volume.GetMasterVolumeLevelScalar()
            * 100
        )

        if direction == "up":
            new_level = current + amount
        else:
            new_level = current - amount

        new_level = max(
            0,
            min(100, new_level)
        )

        volume.SetMasterVolumeLevelScalar(
            new_level / 100,
            None
        )

        action = (
            "increased"
            if direction == "up"
            else "decreased"
        )

        return (
            f"Volume {action} "
            f"to {round(new_level)} percent."
        )

    def mute_volume(self, mute: bool) -> str:

        volume = self._get_volume_interface()

        volume.SetMute(
            1 if mute else 0,
            None
        )

        return "Muted." if mute else "Unmuted."
