#pragma once

#include <iostream>
#include "VlcPlayer.h"
#include "AudioSource.h"

class Bluetooth : public AudioSource {
private:
    VlcPlayer player;

public:
    void play() override {
        if (!player.play(getFilePath(), getVolume())) {
            std::cerr << "Bluetooth cannot play file\n";
        }
    }

    void pause() override {
        player.pause();
    }

    void stop() override {
        player.stop();
    }

    bool setVolume(int value) override {
        bool valid = AudioSource::setVolume(value);

        if (valid) {
            player.setVolume(value);
        }

        return valid;
    }
};
