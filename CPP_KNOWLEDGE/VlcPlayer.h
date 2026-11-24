#pragma once

#include <string>
#include <sys/types.h> // pid_t trên Linux

class VlcPlayer {
public:
    VlcPlayer() = default;
    ~VlcPlayer();

    bool play(const std::string& filePath, int volume);
    bool setVolume(int volume);
    bool pause();
    bool stop();

private:
    pid_t processId_ = -1;
    int commandFd_ = -1;
    bool startVlcProcess(const std::string& filePath);
    bool sendCommand(const std::string& command);
};

