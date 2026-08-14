# SukiSU kernel build for Xiaomi Mi 8

This repository builds a source-integrated SukiSU kernel for `dipper` and
packages it as an AnyKernel3 recovery ZIP.

The build is pinned to commit
`8fd5fad77ae4b99c05188f80e2e1a0fbce3d3d6b` from the public
`duckyduckG/android_kernel_xiaomi_sdm845_419` repository. It enables the
manual KernelSU hook, SUSFS, and KPM on Linux 4.19.325.

Run **Actions > Build SukiSU kernel for Xiaomi Mi 8 > Run workflow**. Download
the `SukiSU-dipper-Lineage23.2-4.19.325` artifact after the job succeeds.

Do not use this artifact on any device other than Xiaomi Mi 8 (`dipper`) or on
a ROM that does not use the Xiaomi SDM845 4.19 kernel base.
