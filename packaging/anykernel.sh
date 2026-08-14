properties() { '
kernel.string=SukiSU 4.19.325 for Xiaomi Mi 8
device.name1=dipper
do.devicecheck=1
'; }

ramdisk_compression=auto
patch_vbmeta_flag=auto
is_slot_device=0
block=boot

. tools/ak3-core.sh

ui_print " " "- Target: Xiaomi Mi 8 (dipper), non-A/B boot partition"
ui_print " " "- Installing source-built SukiSU 4.19.325 kernel..."
split_boot
flash_boot
ui_print " " "- Kernel installation completed. Reboot and open SukiSU Ultra."
