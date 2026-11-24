#pragma once

#include <string>

class AudioSource {
private:
    int volume = 50;
    std::string filePath;

public:
    virtual ~AudioSource() = default;
    virtual bool setVolume(int value) {
        if (value < 0 || value > 100) {
            return false;
        }
        volume = value;
        return true;
    }

    int getVolume() const {
        return volume;
    }

    void setFilePath(const std::string& path) {
        filePath = path;
    }

    const std::string& getFilePath() const {
        return filePath;
    }

    virtual void play() = 0;
    virtual void pause() = 0;
    virtual void stop() = 0;
};
