
# UMAT (Uma Musume Auto Train)
<a href="http://discord.gg/PhVmBtfsKp" target="_blank"><img src="https://img.shields.io/discord/1399387259245166674?color=5865F2&label=Join%20our%20Discord&logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord server"></a>

<a href="https://www.buymeacoffee.com/kisegami" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 50px !important;width: 210px !important;" ></a>
 

An automated training bot for Uma Musume: Pretty Derby that works with **Android emulators** using ADB (Android Debug Bridge). This aim for fully automate gameplay for busy players.
Right now **UMAT** support 3 senario: **URA Finales**, **Unity Cup** and **Trackblazer (through API Mode)**
![Hi](Docs/App.png)
## Highlighted Features
- **Easy to setup and config:** Using automated setup and really simple but efficient config for your training 
- **Score based training system:** Calculate score to train using elements like Support cards, hint, bond,...
- **Custom Race**: Do custom races as you setup for your run
- **Auto Skill Learning:** Auto learn necessary skills based on customizable config
- **Auto event choices picking:** Auto choose event option based on customize priority
- **Auto Update:** Auto update files and resources without needing to do it manually
## Getting Started

### Requirements

#### Software Requirements
- [Python 3.10+](https://www.python.org/downloads/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for text recognition)

#### Android Emulator Requirements
- **Supported Emulators**: The test was done on Mumu Emulator 12, but you might be able to use others
- **Emulator Resolution**: 1080x1920 (Portrait mode)
- **ADB Debugging**: Must be enabled in emulator settings

### Setup
#### Method 1: Easy Method
 1. Download from [Releases](https://github.com/Kisegami/Uma-Musume-Emulator-Auto-Train/releases)
 2. Extract and run **UMAT.exe**
     
    It will download everything, so just wait. It may ask you to install **Tesseract**, install it and don't **change** the Tesseract Path when install.
    
    You may need to close and re-open for it to auto update
3. Config the bot **See Below**
4. Enjoy!

#### Method 2: Manual Method

1. Clone the repository
2. Install all dependencies
3. Run **launch_gui.py**


## Configs
### Configure Android Emulator
1. **Install an Android emulator** (Mumu Emulator 12 or LDPlayer9 recommended)
2. **Set resolution to 1080x1920** (portrait mode)
3. **Enable ADB debugging** in emulator settings. Some enabled by default
4. **Install Uma Musume** in the emulator
### Configure UMAT
Refer to [Config Guide](https://github.com/Kisegami/Uma-Musume-Emulator-Auto-Train/wiki/Config-Guide-%5BEN%5D)

## Always start the bot on Lobby Screen
The bot need to start on lobby screen, the place that you can see training button and Tazuna Hint icon on the top right under the HUD
<div align="center">
<img src="Docs/lobby.png" alt="Description" width="200"/>
</div>

## Contribute
If you run into any issues or something doesn't work as expected, feel free to open an issue.
Contributions are also very welcome, I would truly appreciate any support to help improve this project further.
