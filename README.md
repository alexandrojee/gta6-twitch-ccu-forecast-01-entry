# GTA VI Twitch Viewer Forecaster

Comparable-launch forecaster for GTA VI launch-day Twitch concurrent viewers, built as an AI agent entry for the make.fun bounty "Forecast GTA VI's launch-day Twitch viewers hour by hour."

Outputs 5 quantiles (5%, 25%, 50%, 75%, 95%) for hours 2–24 post-launch, running offline in under 8 seconds per case, offline deterministic and ready to reproduce.

## Run

```bash
MAKEFUN_INPUT_DIR=./kit/input MAKEFUN_OUTPUT_DIR=./out python3 main.py
```

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/alexandrojee/gta6-twitch-ccu-forecast-01-entry/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/alexandrojee/gta6-twitch-ccu-forecast-01-entry/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
