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
    "fs/stat.c",
    "/**\n * vfs_statx - Get basic and extra attributes by filename\n",
    f"""#if {GUARD}
extern int ksu_handle_stat(int *dfd,
                const char __user **filename_user, int *flags);
#endif

/**
 * vfs_statx - Get basic and extra attributes by filename
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

for call in (
    "ksu_selinux_hide_handle_post_fs_data();",
    "ksu_selinux_hide_handle_second_stage();",
):
    replace_all(
        "KernelSU/kernel/runtime/ksud.c",
        f"    {call}\n",
        f"""#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)
    {call}
#endif
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
    "fs/stat.c": ["ksu_handle_stat(&dfd"],
    "kernel/sys.c": ["ksu_handle_setresuid(ruid", "ksu_handle_susfs_prctl(option"],
    "kernel/reboot.c": ["ksu_handle_sys_reboot(magic1"],
}
for path, needles in checks.items():
    source = Path(path).read_text()
    for needle in needles:
        if source.count(needle) != 1:
            raise SystemExit(f"{path}: hook verification failed for {needle}")

print("Applied and verified SukiSU manual hooks")
