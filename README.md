# osu! Mania to SDX Converter

## Description
forked from https://github.com/yukoimi/mania_to_runningstone, please support the original project as well!

designed for my preference of beatmap conversion toolchain, mainly using mania 9k, track denoting stacked note counts and ln denoting a critical note.

usage: `./osu_to_sdx.py <mapper> <difficulty>`, `./osu_to_sdx.py <difficulty> (mapper default set to me)` or `./osu_to_sdx.py`

mania editor 中的 123 轨就是常规对应道路上的 123 轨，456 轨相当于 123 轨上的 2 个重叠 note，789 轨相当于 5 个重叠 note，暂时不支持同一行写多押

ln 头会被转化为绝赞，尾巴无视

环境变量：在 /src 目录下创建文件 `userconfig.ini`，其中输入 `mapper=123` 可以在每次打开转换器时自动将 123 填入 mapper 内容

todo: rewrite chord logic to customize note style?

## License
This project is licensed under the MIT License. See the [LICENSE](https://github.com/yukoimi/mania_to_runningstone/blob/main/LICENSE) file for details.
