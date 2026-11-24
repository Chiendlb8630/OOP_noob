#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>
#include "Radio.h"
#include "Bluetooth.h"

enum class Action { Play, Pause, Stop, Volume, Invalid };

Action parseAction(const std::string& text) {
    static const std::unordered_map<std::string, Action> actions = {
        {"PLAY", Action::Play},
        {"PAUSE", Action::Pause},
        {"STOP", Action::Stop},
        {"VOLUME", Action::Volume}
    };
    auto found = actions.find(text);
    return found == actions.end() ? Action::Invalid : found->second;
}

AudioSource* selectSource(char id, Radio& radio, Bluetooth& bluetooth) {
    if (id == 'A' || id == 'a') return &radio;
    if (id == 'B' || id == 'b') return &bluetooth;
    return nullptr;
}

int main() {
    Radio radio;
    Bluetooth bluetooth;

    radio.setFilePath("music/Radio.mp3");
    bluetooth.setFilePath("music/ble.mp3");

    std::string line;

    while(std::getline(std::cin, line)){
         std::istringstream input(line);
         std::string action;
         char sourceId;

        input >> action;
        if(action == "QUIT"){
            break;
        }

        if (!(input >> sourceId)) {
            std::cerr << "Thieu nguon A hoac B\n";
            continue;
        }

        AudioSource* source = selectSource(sourceId, radio, bluetooth);
        if (source == nullptr) {
            std::cerr << "Nguon khong hop le\n";
            continue;
        }

        switch (parseAction(action)) {
            case Action::Play:
                source->play();
                break;
            case Action::Pause:
                source->pause();
                break;
            case Action::Stop:
                source->stop();
                break;
            case Action::Volume: {
                int value;
                std::string extra;
                if (!(input >> value) || (input >> extra) || !source->setVolume(value)) {
                    std::cerr << "Volume phai la so nguyen tu 0 den 100\n";
                } else {
                    std::cout << "Volume " << sourceId << ": " << value << "%\n";
                }
                break;
            }
            case Action::Invalid:
                std::cerr << "Lenh khong hop le\n";
                break;
        }
    }
    radio.stop();
    bluetooth.stop();
    return 0;
}
