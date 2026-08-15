#!/usr/bin/env python3

from pathlib import Path


GUARD = "defined(CONFIG_KSU) && defined(CONFIG_KSU_MANUAL_HOOK)"


def replace_once(path: str, anchor: str, replacement: str) -> None:
    source_path = Path(path)
    source = source_path.read_text()
    count = source.count(anchor)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}")
    source_path.write_text(source.replace(anchor, replacement, 1))


replace_once(
    "fs/exec.c",
    "static int do_execveat_common(int fd, struct filename *filename,\n",
    f"""#if {GUARD}
extern bool ksu_execveat_hook __read_mostly;
extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr,
                void *argv, void *envp, int *flags);
extern int ksu_handle_execveat_sucompat(int *fd,
                struct filename **filename_ptr, void *argv,
                void *envp, int *flags);
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
	if (unlikely(ksu_execveat_hook))
		ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);
	else
		ksu_handle_execveat_sucompat(&fd, &filename, &argv, &envp, &flags);
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
    "ssize_t vfs_read(struct file *file, char __user *buf, size_t count, loff_t *pos)\n",
    f"""#if {GUARD}
extern bool ksu_vfs_read_hook __read_mostly;
extern int ksu_handle_vfs_read(struct file **file_ptr, char __user **buf_ptr,
                size_t *count_ptr, loff_t **pos);
#endif

ssize_t vfs_read(struct file *file, char __user *buf, size_t count, loff_t *pos)
""",
)
replace_once(
    "fs/read_write.c",
    "\tssize_t ret;\n\n\tif (!(file->f_mode & FMODE_READ))",
    f"""\tssize_t ret;

#if {GUARD}
	if (unlikely(ksu_vfs_read_hook))
		ksu_handle_vfs_read(&file, &buf, &count, &pos);
#endif

	if (!(file->f_mode & FMODE_READ))""",
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
    "fs/stat.c",
    "\tunsigned int lookup_flags = LOOKUP_FOLLOW | LOOKUP_AUTOMOUNT;\n\n\tif ((flags &",
    f"""\tunsigned int lookup_flags = LOOKUP_FOLLOW | LOOKUP_AUTOMOUNT;

#if {GUARD}
	ksu_handle_stat(&dfd, &filename, &flags);
#endif

	if ((flags &""",
)

replace_once(
    "drivers/input/input.c",
    "static void input_handle_event(struct input_dev *dev,\n",
    f"""#if {GUARD}
extern bool ksu_input_hook __read_mostly;
extern int ksu_handle_input_handle_event(unsigned int *type,
                unsigned int *code, int *value);
#endif

static void input_handle_event(struct input_dev *dev,
""",
)
replace_once(
    "drivers/input/input.c",
    "\tint disposition = input_get_disposition(dev, type, code, &value);\n\n\tif (disposition !=",
    f"""\tint disposition = input_get_disposition(dev, type, code, &value);

#if {GUARD}
	if (unlikely(ksu_input_hook))
		ksu_handle_input_handle_event(&type, &code, &value);
#endif

	if (disposition !=""",
)

checks = {
    "fs/exec.c": ["ksu_handle_execveat(&fd", "ksu_handle_execveat_sucompat(&fd"],
    "fs/open.c": ["ksu_handle_faccessat(&dfd"],
    "fs/read_write.c": ["ksu_handle_vfs_read(&file"],
    "fs/stat.c": ["ksu_handle_stat(&dfd"],
    "drivers/input/input.c": ["ksu_handle_input_handle_event(&type"],
}
for path, needles in checks.items():
    source = Path(path).read_text()
    for needle in needles:
        if source.count(needle) != 1:
            raise SystemExit(f"{path}: hook verification failed for {needle}")

print("Applied and verified SukiSU v3.2.0 manual hooks")
