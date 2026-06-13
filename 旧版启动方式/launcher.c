#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>

int main(void) {
    char executable_path[PATH_MAX];
    uint32_t size = sizeof(executable_path);

    if (_NSGetExecutablePath(executable_path, &size) != 0) {
        return 1;
    }

    char command[PATH_MAX * 2];
    snprintf(
        command,
        sizeof(command),
        "cd \"$(dirname '%s')/../../..\" && exec /usr/bin/python3 mahjong_team_app.py",
        executable_path
    );

    execl("/bin/zsh", "zsh", "-lc", command, (char *)NULL);
    return 1;
}
