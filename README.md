# KernelSU v3.3.0 kernel for Xiaomi Mi 8 (dipper)

Builds a source-integrated **KernelSU v3.3.0** kernel for `dipper` from the
`duckyduckG/android_kernel_xiaomi_sdm845_419` 4.19 kernel source (pinned to
commit `2e1cfd38e5f3b53351d3d59c797d14ff7f050611`, matching the 2026-02-03
LineageOS 23.2 build) and packages it as an AnyKernel3 recovery ZIP.

- Kernel source: `duckyduckG/android_kernel_xiaomi_sdm845_419` @ `2e1cfd38`
- KernelSU: `tiann/KernelSU` @ `v3.3.0`
- AnyKernel3: `osm0sis/AnyKernel3` @ `e4b1bb25`
- Toolchain: Android 16 Clang `r563880`

## Usage

Run **Actions > Build KernelSU v3.3.0 kernel for Xiaomi Mi 8 (LineageOS 23.2) >
Run workflow** on branch `ksu-v3.3.0`, then download the
`KernelSU-dipper-Lineage23.2-v3.3.0` artifact.

Flash the ZIP in TWRP **only on LineageOS 23.2** (the ROM that uses this 4.19
kernel base). It is NOT compatible with the HarmonyOS ROM (4.9 kernel).

After boot, install the KernelSU manager APK and grant root.
