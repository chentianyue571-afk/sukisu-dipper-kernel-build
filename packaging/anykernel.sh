properties() { '
kernel.string=SukiSU v3.2.0 exact LineageOS kernel for Xiaomi Mi 8
device.name1=dipper
do.devicecheck=1
'; }

RAMDISK_COMPRESSION=auto
PATCH_VBMETA_FLAG=auto
IS_SLOT_DEVICE=0
BLOCK=/dev/block/bootdevice/by-name/boot

. tools/ak3-core.sh

ui_print " " "- Target: Xiaomi Mi 8 (dipper), non-A/B boot partition"
ui_print " " "- Installing exact LineageOS 23.2 SukiSU v3.2.0 kernel..."
split_boot
flash_boot
ui_print " " "- Kernel installation completed. Reboot and open SukiSU Ultra."
