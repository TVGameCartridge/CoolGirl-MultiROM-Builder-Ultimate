# CoolGirl MultiROM Builder Ultimate Classic Menu Mod

This is a high-performance, classic-style NES (Nintendo Entertainment System) game selection menu. It has been specifically modded to break the 256-game barrier using advanced 16-bit logic, making it the "Ultimate" choice for massive MultiROM builds.

## Features

* **16-bit Navigation Engine:** Theoretically supports up to 65,535 games (Stability-tested with 806 games).
* **Compact 20-Game List:** A clean, condensed layout displaying exactly 20 games per screen.
* **Page-by-Page Navigation:** Instant page-refresh system instead of slow scrolling.
* **Original System Font:** Authentic, classic 8-bit font included.
* **Rapid Seeking:** Integrated +/- 20 game jumps using Left/Right D-pad buttons.
* **Haptic Audio Feedback:** Professional-grade "bleep" sound effects.

## How to Build (Quick Start)

1.  **Prepare your Games:** Place all your NES ROM files (.nes) into the `/games` folder.
2.  **Select Configuration:** Depending on the number of games, run the appropriate batch file:
    * **Up to 20 games:** Run `load_4in1_config.bat`.
    * **21 to 47 games:** Run `load_47in1_config.bat`.
    * **48 to 512+ games:** Run `load_512in1_config.bat` or your custom `build_ultimate_800.bat`.
3.  **Compile:** The builder will scan the folder and generate your multi-game ROM.

## Compatibility & Open Collaboration

* **Mapper Support:** Please note that this builder does **not** support every NES mapper at the moment. It is optimized for the most common and compatible mappers used in the CoolGirl framework.
* **Open for Contributions:** This is an open-ended project. If you are an assembly developer or mapper expert, you are more than welcome to fork this repository and add support for more mappers or improve the existing logic. Let's make this the most compatible builder together!

## Customization (Visuals & Colors)

Modify the look using **YY-CHR** or **NESST** in the resources folder:
* `menu_symbols.png`, `menu_header.png`, `menu_sprites.png`.

## Recommended Tools (Included in /tools)

* **YY-CHR**: Graphics editing.
* **NESST (NES Screen Tool)**: UI design.
* **NESHead**: ROM header management.

## Tool Ownership & Rights

All third-party utilities in the `/tools` folder remain the intellectual property of their respective creators. No copyright infringement is intended.

## Technical Overhaul (The "Mod" details)

- **16-bit Logic:** Replaced 8-bit registers with 16-bit variables for large libraries.
- **Dynamic PRG Bank Management:** Automatic bank switching for massive name databases.
- **Instant Page Redraw:** Optimized V-blank synchronization for zero-flicker transitions.

## Credits & Acknowledgments

* **Original Creator:** Special thanks to the original author of the **CoolGirl MultiROM Builder** (**Cluster**, **MottZilla**, and the NES Homebrew community).
* **16-bit Logic & Optimization:** Modded and enhanced by **TVGameCartridge** with collaborative support from Gemini AI.

---
*CoolGirl MultiROM Builder - Powering the next generation of NES Multicarts.*