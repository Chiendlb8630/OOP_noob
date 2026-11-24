#include "VlcPlayer.h"

#include <cerrno>
#include <csignal>
#include <ctime>
#include <fstream>
#include <iostream>
#include <sys/wait.h>
#include <unistd.h>


bool VlcPlayer::startVlcProcess(const std::string& filePath) {
    bool success = false;
    int pipeFd[2];
    if (pipe(pipeFd) == 0) {
        pid_t pid = fork();

        if (pid < 0) {
            close(pipeFd[0]);
            close(pipeFd[1]);
        } else if (pid == 0) {
            close(pipeFd[1]);
            if (dup2(pipeFd[0], STDIN_FILENO) == -1) {
                _exit(127);
            }
            close(pipeFd[0]);
            execlp("cvlc", "cvlc", "-I", "rc",
                   "--rc-fake-tty", "--no-video",
                   filePath.c_str(), static_cast<char*>(nullptr));

            _exit(127); // execlp thất bại
        } else {
            close(pipeFd[0]);
            processId_ = pid;
            commandFd_ = pipeFd[1];
            success = true;
        }
    }

    return success;
}

bool VlcPlayer::setVolume(int volume) {
    bool success = volume >= 0 && volume <= 100 && commandFd_ != -1;

    if (success) {
        int vlcVolume = volume * 256 / 100;
        success = sendCommand("volume " + std::to_string(vlcVolume));
    }

    return success;
}

bool VlcPlayer::pause() {
    bool success = commandFd_ != -1;
    if (success) {
        success = sendCommand("pause");
    }
    return success;
}

bool VlcPlayer::stop() {
    bool success = true;

    if (commandFd_ != -1) {
        if (close(commandFd_) == -1) {
            success = false;
        }
        commandFd_ = -1;
    }

    if (processId_ > 0) {
        if (kill(processId_, SIGTERM) == -1 && errno != ESRCH) {
            success = false;
        }

        int status = 0;
        pid_t waited;
        do {
            waited = waitpid(processId_, &status, 0);
        } while (waited == -1 && errno == EINTR);
        if (waited == -1 && errno != ECHILD) {
            success = false;
        }
        processId_ = -1;
    }

    return success;
}

bool VlcPlayer::sendCommand(const std::string& command) {
    bool success = commandFd_ != -1;
    sigset_t blocked;
    sigset_t previous;
    sigemptyset(&blocked);
    sigaddset(&blocked, SIGPIPE);

    if (success) {
        success = sigprocmask(SIG_BLOCK, &blocked, &previous) == 0;
    }
    if (success) {
        sigset_t pending;
        sigpending(&pending);
        bool hadPendingSigpipe = sigismember(&pending, SIGPIPE) == 1;
        bool brokenPipe = false;
        const std::string line = command + '\n';
        std::size_t sent = 0;

        while (sent < line.size() && success) {
            ssize_t count = ::write(commandFd_, line.data() + sent,
                                    line.size() - sent);
            if (count > 0) {
                sent += static_cast<std::size_t>(count);
            } else if (count == -1 && errno == EINTR) {
                // Thử ghi lại nếu bị ngắt bởi tín hiệu khác.
            } else {
                brokenPipe = count == -1 && errno == EPIPE;
                success = false;
            }
        }

        if (brokenPipe && !hadPendingSigpipe) {
            timespec noWait = {0, 0};
            sigtimedwait(&blocked, nullptr, &noWait);
        }
        if (sigprocmask(SIG_SETMASK, &previous, nullptr) == -1) {
            success = false;
        }
    }

    return success;
}

VlcPlayer::~VlcPlayer() {
    stop();
}

bool VlcPlayer::play(const std::string& filePath, int volume) {
    bool success = false;

    if (filePath.empty()) 
    {
        std::cerr << "Chua chon file nhac\n";
    } 
    else if (volume < 0 || volume > 100) 
    {
        std::cerr << "Volume phai nam trong khoang 0-100\n";
    } 
    else 
    {
        std::ifstream file(filePath, std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "Khong mo duoc file: " << filePath << '\n';
        } else {
            file.close();

            success = stop();
            if (success) {
                success = startVlcProcess(filePath);
            }
            if (success) {
                success = setVolume(volume);
            }
            if (!success && processId_ > 0) {
                stop();
            }
        }
    }

    return success;
}
