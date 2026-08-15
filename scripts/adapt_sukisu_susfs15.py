#!/usr/bin/env python3

from pathlib import Path


def replace_once(path: Path, anchor: str, replacement: str) -> None:
    source = path.read_text()
    count = source.count(anchor)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}")
    path.write_text(source.replace(anchor, replacement, 1))


root = Path(".")

kconfig = root / "KernelSU/kernel/Kconfig"
source = kconfig.read_text()
start = source.index("config KSU_SUSFS_SUS_MAP\n")
end = source.index("\nendmenu", start)
source = source[:start] + source[end:]
anchor = "config KSU_SUSFS_SUS_PATH\n"
legacy_options = '''config KSU_SUSFS_HAS_MAGIC_MOUNT
\tbool "Current KernelSU has magic mount support"
\tdepends on KSU_SUSFS
\tdefault y

config KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT
\tbool "Automatically hide KernelSU default mounts"
\tdepends on KSU_SUSFS_SUS_MOUNT
\tdefault y

config KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT
\tbool "Automatically hide suspicious bind mounts"
\tdepends on KSU_SUSFS_SUS_MOUNT
\tdefault y

config KSU_SUSFS_SUS_OVERLAYFS
\tbool "Spoof overlayfs kstat and kstatfs"
\tdepends on KSU_SUSFS
\tdefault n

config KSU_SUSFS_TRY_UMOUNT
\tbool "Enable SUSFS try_umount"
\tdepends on KSU_SUSFS
\tdefault y

config KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT
\tbool "Automatically add bind mounts to try_umount"
\tdepends on KSU_SUSFS_TRY_UMOUNT
\tdefault y

'''
if source.count(anchor) != 1:
    raise SystemExit(f"{kconfig}: missing SUS_PATH anchor")
kconfig.write_text(source.replace(anchor, legacy_options + anchor, 1))

header = root / "include/linux/susfs_def.h"
replace_once(
    header,
    "#include <linux/bits.h>\n",
    "#include <linux/bits.h>\n#include <linux/string.h>\n#include <linux/sched.h>\n#include <linux/uidgid.h>\n",
)
anchor = "#endif // #ifndef KSU_SUSFS_DEF_H"
compat = '''
static inline bool susfs_starts_with(const char *str, const char *prefix)
{
\treturn !strncmp(str, prefix, strlen(prefix));
}

static inline bool susfs_ends_with(const char *str, const char *suffix)
{
\tsize_t str_len = strlen(str);
\tsize_t suffix_len = strlen(suffix);

\treturn suffix_len <= str_len &&
\t       !strcmp(str + str_len - suffix_len, suffix);
}

static inline bool susfs_is_current_proc_umounted(void)
{
\treturn current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC;
}

static inline bool susfs_is_current_proc_umounted_app(void)
{
\treturn susfs_is_current_proc_umounted() && current_uid().val >= 10000;
}

static inline void susfs_set_current_proc_umounted(void)
{
\tcurrent->susfs_task_state |= TASK_STRUCT_NON_ROOT_USER_APP_PROC;
}

'''
replace_once(header, anchor, compat + anchor)

lsm = root / "KernelSU/kernel/hook/lsm_hook.c"
anchor = '''extern struct work_struct susfs_extra_works;

static inline void ksu_handle_extra_susfs_work(void)
{
    if (work_pending(&susfs_extra_works))
        return;

    schedule_work(&susfs_extra_works);
}
'''
replacement = '''#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
extern void susfs_try_umount(uid_t target_uid);
#endif

static inline void ksu_handle_extra_susfs_work(void)
{
#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
    susfs_try_umount(current_uid().val);
#endif
}
'''
replace_once(lsm, anchor, replacement)

dispatch = root / "KernelSU/kernel/supercall/dispatch.c"
source = dispatch.read_text()
start_marker = "#ifdef CONFIG_KSU_SUSFS\nint ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd, void __user **arg)\n"
end_marker = "#endif\n\nstatic int do_nuke_ext4_sysfs"
start = source.index(start_marker)
end = source.index(end_marker, start) + len("#endif\n")
replacement = '''#ifdef CONFIG_KSU_SUSFS
int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd, void __user **arg)
{
    if (magic1 != KSU_INSTALL_MAGIC1)
        return -EINVAL;

    if (magic2 == KSU_INSTALL_MAGIC2)
        return ksu_supercall_reboot_handler(arg);

    return -EINVAL;
}
#endif
'''
dispatch.write_text(source[:start] + replacement + source[end:])

makefile = root / "KernelSU/kernel/Makefile"
with makefile.open("a") as stream:
    stream.write("\nobj-$(CONFIG_KSU_SUSFS) += susfs_legacy_prctl.o\n")

checks = {
    "KernelSU/kernel/Kconfig": ["config KSU_SUSFS_TRY_UMOUNT"],
    "KernelSU/kernel/hook/lsm_hook.c": ["susfs_try_umount(current_uid().val)"],
    "KernelSU/kernel/supercall/dispatch.c": ["return ksu_supercall_reboot_handler(arg)"],
    "include/linux/susfs.h": ['#define SUSFS_VERSION "v1.5.5"'],
}
for name, needles in checks.items():
    text = (root / name).read_text()
    for needle in needles:
        if needle not in text:
            raise SystemExit(f"{name}: missing {needle}")

print("Applied SukiSU 40796 compatibility for native SUSFS v1.5.5")
