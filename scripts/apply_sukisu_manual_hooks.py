#!/usr/bin/env python3

from pathlib import Path


GUARD = "defined(CONFIG_KSU)"


def replace_once(path: str, anchor: str, replacement: str) -> None:
    source_path = Path(path)
    source = source_path.read_text()
    count = source.count(anchor)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}")
    source_path.write_text(source.replace(anchor, replacement, 1))


def replace_all(path: str, anchor: str, replacement: str) -> None:
    source_path = Path(path)
    source = source_path.read_text()
    count = source.count(anchor)
    if count < 1:
        raise SystemExit(f"{path}: expected at least one anchor")
    source_path.write_text(source.replace(anchor, replacement))


replace_once(
    "fs/exec.c",
    "static int do_execveat_common(int fd, struct filename *filename,\n",
    f"""#if {GUARD}
extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr,
                void *argv, void *envp, int *flags);
#endif

static int do_execveat_common(int fd, struct filename *filename,
""",
)
replace_once(
    "fs/exec.c",
    """{
	return __do_execve_file(fd, filename, argv, envp, flags, NULL);
}
""",
    f"""{{
#if {GUARD}
	ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);
#endif
	return __do_execve_file(fd, filename, argv, envp, flags, NULL);
}}
""",
)

replace_once(
    "fs/open.c",
    "/*\n * access() needs to use the real uid/gid, not the effective uid/gid.\n",
    f"""#if {GUARD}
extern int ksu_handle_faccessat(int *dfd,
                const char __user **filename_user, int *mode, int *flags);
#endif

/*
 * access() needs to use the real uid/gid, not the effective uid/gid.
""",
)
replace_once(
    "fs/open.c",
    "\tunsigned int lookup_flags = LOOKUP_FOLLOW;\n\n\tif (mode & ~S_IRWXO)",
    f"""\tunsigned int lookup_flags = LOOKUP_FOLLOW;

#if {GUARD}
	ksu_handle_faccessat(&dfd, &filename, &mode, NULL);
#endif

	if (mode & ~S_IRWXO)""",
)

replace_once(
    "fs/read_write.c",
    "ssize_t vfs_read(struct file *file, char __user *buf, size_t count, loff_t *pos)\n{\n\tssize_t ret;\n",
    f"""#if {GUARD}
extern int ksu_handle_vfs_read(struct file **file_ptr, char __user **buf_ptr,
                size_t *count_ptr, loff_t **pos);
#endif

ssize_t vfs_read(struct file *file, char __user *buf, size_t count, loff_t *pos)
{{
	ssize_t ret;

#if {GUARD}
	ksu_handle_vfs_read(&file, &buf, &count, &pos);
#endif
""",
)

replace_once(
    "fs/stat.c",
    "/**\n * vfs_statx_fd - Get the enhanced basic attributes by file descriptor\n",
    f"""#if {GUARD}
extern int ksu_handle_stat(int *dfd,
                const char __user **filename_user, int *flags);
extern void ksu_handle_vfs_fstat(int fd, loff_t *kstat_size_ptr);
#endif

/**
 * vfs_statx_fd - Get the enhanced basic attributes by file descriptor
""",
)

replace_once(
    "kernel/sys.c",
    "long __sys_setresuid(uid_t ruid, uid_t euid, uid_t suid)\n",
    f"""#if {GUARD} && defined(CONFIG_KSU_SUSFS)
extern int ksu_handle_setresuid(uid_t ruid, uid_t euid, uid_t suid);
#endif

long __sys_setresuid(uid_t ruid, uid_t euid, uid_t suid)
""",
)
replace_once(
    "kernel/sys.c",
    """long __sys_setresuid(uid_t ruid, uid_t euid, uid_t suid)
{
	struct user_namespace *ns = current_user_ns();
""",
    f"""long __sys_setresuid(uid_t ruid, uid_t euid, uid_t suid)
{{
#if {GUARD} && defined(CONFIG_KSU_SUSFS)
	ksu_handle_setresuid(ruid, euid, suid);
#endif
	struct user_namespace *ns = current_user_ns();
""",
)

replace_once(
    "kernel/reboot.c",
    "SYSCALL_DEFINE4(reboot,",
    f"""#if {GUARD}
extern int ksu_handle_sys_reboot(int magic1, int magic2,
                unsigned int cmd, void __user **arg);
#endif

SYSCALL_DEFINE4(reboot,""",
)
replace_once(
    "kernel/reboot.c",
    """	int ret = 0;

	/* We only trust the superuser with rebooting the system. */
""",
    f"""	int ret = 0;

#if {GUARD}
	if (!ksu_handle_sys_reboot(magic1, magic2, cmd, &arg))
		return 0;
#endif

	/* We only trust the superuser with rebooting the system. */
""",
)

replace_once(
    "kernel/sys.c",
    "SYSCALL_DEFINE5(prctl, int, option, unsigned long, arg2, unsigned long, arg3,\n",
    f"""#if {GUARD} && defined(CONFIG_KSU_SUSFS)
extern int ksu_handle_susfs_prctl(int option, unsigned long cmd,
                unsigned long arg3, unsigned long arg4, unsigned long arg5);
#endif

SYSCALL_DEFINE5(prctl, int, option, unsigned long, arg2, unsigned long, arg3,
""",
)
replace_once(
    "kernel/sys.c",
    "{\n\tstruct task_struct *me = current;\n\tunsigned char comm[sizeof(me->comm)];\n\tlong error;\n",
    f"""{{
#if {GUARD} && defined(CONFIG_KSU_SUSFS)
\tif (ksu_handle_susfs_prctl(option, arg2, arg3, arg4, arg5))
\t\treturn 0;
#endif
\tstruct task_struct *me = current;
\tunsigned char comm[sizeof(me->comm)];
\tlong error;
""",
)
replace_once(
    "fs/stat.c",
    "\tunsigned int lookup_flags = LOOKUP_FOLLOW | LOOKUP_AUTOMOUNT;\n\n\tif ((flags &",
    f"""\tunsigned int lookup_flags = LOOKUP_FOLLOW | LOOKUP_AUTOMOUNT;

#if {GUARD}
	ksu_handle_stat(&dfd, &filename, &flags);
#endif

	if ((flags &""",
)

replace_once(
    "fs/stat.c",
    "\t\terror = vfs_getattr(&f.file->f_path, stat,\n\t\t\t\t    request_mask, query_flags);\n\t\tfdput(f);\n",
    f"""\t\terror = vfs_getattr(&f.file->f_path, stat,
\t\t\t\t    request_mask, query_flags);
#if {GUARD}
\t\tif (!error)
\t\t\tksu_handle_vfs_fstat(fd, &stat->size);
#endif
\t\tfdput(f);
""",
)
replace_once(
    "fs/stat.c",
    "\terror = vfs_getattr(&path, stat, request_mask, flags);\n\tpath_put(&path);\n",
    f"""\terror = vfs_getattr(&path, stat, request_mask, flags);
#if {GUARD}
\tif (!error)
\t\tksu_handle_vfs_fstat(dfd, &stat->size);
#endif
\tpath_put(&path);
""",
)

# SELinux hide backport for Linux 4.19: SukiSU compiles feature/selinux_hide.c
# only on 5.10+, so re-enable it and adapt the 4.19 SELinux internals
# (status page and its lock live in selinux_state.ss on 4.19).
replace_once(
    "KernelSU/kernel/ksu.c",
    '#include "feature/sulog.c"\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)\n#include "feature/selinux_hide.c"\n#endif\n#include "runtime/ksud.c"\n',
    '#include "feature/sulog.c"\n#include "feature/selinux_hide.c"\n#include "runtime/ksud.c"\n',
)
replace_once(
    "KernelSU/kernel/ksu.c",
    "    ksu_adb_root_init();\n\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)\n    ksu_selinux_hide_init();\n#endif\n",
    "    ksu_adb_root_init();\n\n    ksu_selinux_hide_init();\n",
)
replace_all(
    "KernelSU/kernel/feature/selinux_hide.c",
    "    mutex_lock(&selinux_state.status_lock);\n",
    "    mutex_lock(&selinux_state.ss->status_lock);\n",
)
replace_all(
    "KernelSU/kernel/feature/selinux_hide.c",
    "    mutex_unlock(&selinux_state.status_lock);\n",
    "    mutex_unlock(&selinux_state.ss->status_lock);\n",
)
replace_once(
    "KernelSU/kernel/feature/selinux_hide.c",
    "    if (!selinux_state.status_page) {\n",
    "    if (!selinux_state.ss->status_page) {\n",
)
replace_once(
    "KernelSU/kernel/feature/selinux_hide.c",
    "    struct selinux_kernel_status *status = page_address(selinux_state.status_page);\n",
    "    struct selinux_kernel_status *status = page_address(selinux_state.ss->status_page);\n",
)
# Make KSU_FEATURE_SELINUX_HIDE available on 4.19 (it is 5.10+-gated upstream).
replace_once(
    "KernelSU/kernel/include/uapi/feature.h",
    "    KSU_FEATURE_ADB_ROOT = 3,\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)\n    KSU_FEATURE_SELINUX_HIDE = 4,\n#endif\n",
    "    KSU_FEATURE_ADB_ROOT = 3,\n    KSU_FEATURE_SELINUX_HIDE = 4,\n",
)
replace_once(
    "KernelSU/kernel/feature/selinux_hide.c",
    "    fake_state.initialized = true;\n    fake_state.policy = backup_sepolicy;\n",
    """#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)
    fake_state.initialized = true;
    fake_state.policy = backup_sepolicy;
#endif
""",
)

# On 4.19 there is no backup_sepolicy (5.10+ only); the status-page hide
# does not need it, so only require it on 5.10+.
replace_once(
    "KernelSU/kernel/feature/selinux_hide.c",
    "    pr_info(\"selinux_hide: init selinux hide\\n\");\n    if (!backup_sepolicy) {\n        pr_err(\"no backup sepolicy available, please save feature and reboot to retry!\\n\");\n        return -EAGAIN;\n    }\n",
    """    pr_info("selinux_hide: init selinux hide\n");
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)
    if (!backup_sepolicy) {
        pr_err("no backup sepolicy available, please save feature and reboot to retry!\n");
        return -EAGAIN;
    }
#endif""",
)
replace_once(
    "KernelSU/kernel/feature/selinux_hide.c",
    "void ksu_selinux_hide_drop_backup_if_unused()\n{\n    mutex_lock(&selinux_hide_mutex);\n    if (!ksu_selinux_hide_running && backup_sepolicy) {\n        pr_info(\"selinux_hide is not enabled - drop backup_sepolicy\\n\");\n        sidtab_destroy(backup_sepolicy->sidtab);\n        kfree(backup_sepolicy->sidtab);\n        ksu_destroy_sepolicy(backup_sepolicy);\n        backup_sepolicy = NULL;\n    }\n    mutex_unlock(&selinux_hide_mutex);\n}",
    """void ksu_selinux_hide_drop_backup_if_unused()
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)
    mutex_lock(&selinux_hide_mutex);
    if (!ksu_selinux_hide_running && backup_sepolicy) {
        pr_info("selinux_hide is not enabled - drop backup_sepolicy\n");
        sidtab_destroy(backup_sepolicy->sidtab);
        kfree(backup_sepolicy->sidtab);
        ksu_destroy_sepolicy(backup_sepolicy);
        backup_sepolicy = NULL;
    }
    mutex_unlock(&selinux_hide_mutex);
#endif
}""",
)

# Swap the /sys/fs/selinux/status page for app UIDs when SELinux hide is on.
replace_once(
    "security/selinux/selinuxfs.c",
    "#include <linux/fs.h>\n",
    "#include <linux/fs.h>\n#include <linux/cred.h>\n",
)
replace_once(
    "security/selinux/selinuxfs.c",
    "\tstruct page    *status = selinux_kernel_status_page(fsi->state);\n\n\tif (!status)\n",
    """\tstruct page    *status = selinux_kernel_status_page(fsi->state);

#ifdef CONFIG_KSU
\textern bool ksu_selinux_hide_enabled;
\textern struct page *fake_status;
\tif (unlikely(ksu_selinux_hide_enabled) && current_uid().val >= 10000 && fake_status)
\t\tstatus = fake_status;
#endif

\tif (!status)
""",
)

replace_once(
    "KernelSU/kernel/sulog/event.c",
    "    #define USER_ARG_NULL user_arg_null_ptr()\n",
    """#ifdef CONFIG_KSU_SUSFS
    #define USER_ARG_NULL user_arg_null_ptr()
#else
    #define USER_ARG_NULL (*user_arg_null_ptr())
#endif
""",
)

checks = {
    "fs/exec.c": ["ksu_handle_execveat(&fd"],
    "fs/open.c": ["ksu_handle_faccessat(&dfd"],
    "fs/read_write.c": ["ksu_handle_vfs_read(&file"],
    "fs/stat.c": [
        "ksu_handle_stat(&dfd",
        "ksu_handle_vfs_fstat(fd, &stat->size);",
        "ksu_handle_vfs_fstat(dfd, &stat->size);",
    ],
    "kernel/sys.c": ["ksu_handle_setresuid(ruid", "ksu_handle_susfs_prctl(option"],
    "kernel/reboot.c": ["ksu_handle_sys_reboot(magic1"],
    "KernelSU/kernel/include/uapi/feature.h": ["    KSU_FEATURE_SELINUX_HIDE = 4,"],
    "KernelSU/kernel/ksu.c": [
        '#include "feature/selinux_hide.c"',
        "    ksu_selinux_hide_init();",
    ],
    "KernelSU/kernel/feature/selinux_hide.c": [
        "if (!selinux_state.ss->status_page) {",
        "page_address(selinux_state.ss->status_page)",
    ],
    "KernelSU/kernel/runtime/ksud.c": ["ksu_selinux_hide_handle_post_fs_data();"],
    "security/selinux/selinuxfs.c": ["status = fake_status;"],
}
for path, needles in checks.items():
    source = Path(path).read_text()
    for needle in needles:
        if source.count(needle) != 1:
            raise SystemExit(f"{path}: hook verification failed for {needle}")

print("Applied and verified SukiSU manual hooks (v12b: vfs_read + vfs_fstat + selinux_hide 4.19)")
