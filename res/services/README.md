# 嵌入式业务配图

使用内置 imagegen 工具生成，2026-09-21。三张图均为 AI 硬件概念示意，不代表已交付案例或指定型号实拍。保留当前网站深色、克制青色的视觉风格；不含品牌标识。

| 文件 | 用途 | 输出 |
| --- | --- | --- |
| stm32-development.webp | STM32 固件与外设开发 | 960 × 640 |
| esp32-development.webp | ESP32 无线物联网开发 | 960 × 640 |
| linux-development.webp | 嵌入式 Linux 系统开发、首页入口 | 960 × 640 |

生成原图为 1536 × 1024 PNG，使用 Sharp 等比例缩小并导出为质量 82 的 WebP。页面提供替代文本、明确尺寸和懒加载。

## 提示词

### STM32

Use case: product-mockup. Asset type: landscape service card image for the existing Singularity Near engineering company website. Generate a premium realistic 3D product-style conceptual illustration, landscape 3:2 composition. Dark navy background #0B141B, restrained soft teal #54D6C7 rim light, natural silver connectors and matte graphite components, crisp practical hardware details. Single hardware subject centered with breathing space on a low matte surface, camera three-quarter top-down view, clean studio photography aesthetic, no overly luminous neon, no sci-fi holograms, no gradient rainbow. This is a CONCEPT ILLUSTRATION, not a claimed completed client product or exact manufacturer board. No logos, no trademarks, no brand wordmarks, no readable text, no watermark, no people, no hands, no captions. Ensure believable connector geometries and restrained traces. Subject: compact teal-green microcontroller development PCB representing STM32-class embedded firmware development. Prominent central square LQFP microcontroller with fine pins on four sides, paired straight header rows, one USB connector and tiny tactile reset button, subtle sensor breakout attached by four short tidy wires beside it. Emphasize reliable control and low-level electronics. No wireless antenna or Linux heat sink.

### ESP32

Use case: product-mockup. Asset type: landscape service card image for the existing Singularity Near engineering company website. Generate a premium realistic 3D product-style conceptual illustration, landscape 3:2 composition. Dark navy background #0B141B, restrained soft teal #54D6C7 rim light, natural silver connectors and matte graphite components, crisp practical hardware details. Single hardware subject centered with breathing space on a low matte surface, camera three-quarter top-down view, clean studio photography aesthetic, no overly luminous neon, no sci-fi holograms, no gradient rainbow. This is a CONCEPT ILLUSTRATION, not a claimed completed client product or exact manufacturer board. No logos, no trademarks, no brand wordmarks, no readable text, no watermark, no people, no hands, no captions. Ensure believable connector geometries and restrained traces. Subject: compact wireless IoT development PCB representing ESP32-class development. A rectangular metal RF shielding module with a distinct small printed PCB antenna zone at the end, two straight header rows, a USB connector, and a small environmental sensor breakout beside the board connected with a short clean cable. Emphasize connected sensing hardware; no floating Wi-Fi symbols or software UI.

### Linux

Use case: product-mockup. Asset type: landscape service card image for the existing Singularity Near engineering company website. Generate a premium realistic 3D product-style conceptual illustration, landscape 3:2 composition. Dark navy background #0B141B, restrained soft teal #54D6C7 rim light, natural silver connectors and matte graphite components, crisp practical hardware details. Single hardware subject centered with breathing space on a low matte surface, camera three-quarter top-down view, clean studio photography aesthetic, no overly luminous neon, no sci-fi holograms, no gradient rainbow. This is a CONCEPT ILLUSTRATION, not a claimed completed client product or exact manufacturer board. No logos, no trademarks, no brand wordmarks, no readable text, no watermark, no people, no hands, no captions. Ensure believable connector geometries and restrained traces. Subject: compact embedded Linux industrial edge gateway concept, a small single-board computer with modest metal heat sink, one believable Ethernet RJ45 jack and two USB ports seated partially in an open black aluminum enclosure. A short Ethernet cable connects at one edge. Emphasize practical Linux system integration and edge connectivity, no screen, no keyboard, no extra modules floating in the scene.

## 业务范围参考

- STM32 软件生态：https://www.st.com/content/st_com/en/stm32-mcu-developer-zone/embedded-software.html
- ESP-IDF OTA：https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/system/ota.html
- Linux 内核文档：https://docs.kernel.org/
- 设备树：https://cdn.kernel.org/doc/html/latest/devicetree/usage-model.html

具体能力依芯片、板卡与需求评估；页面不承诺所有 ESP32 型号均同时支持 Wi-Fi 和 BLE。
