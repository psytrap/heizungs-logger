#include "frame.h"

#if defined(ARDUINO)
#include <Arduino.h>
#else
#include <stdio.h>
#endif

namespace {

size_t appendText(char* out, size_t cap, size_t pos, const char* text) {
    if (cap == 0) {
        return 0;
    }
    for (const char* p = text; *p != '\0' && pos + 1 < cap; ++p) {
        out[pos++] = *p;
    }
    out[pos] = '\0';
    return pos;
}

// AVR's printf has no float support, so the sketch uses dtostrf and the host
// build uses snprintf. Both are configured with width 0 and the same number of
// decimals, which yields the same digits ("29.7", "-127.0").
size_t formatTemperature(char* out, size_t cap, float value, uint8_t decimals) {
    char buf[32];
#if defined(ARDUINO)
    dtostrf(value, 0, decimals, buf);
#else
    snprintf(buf, sizeof(buf), "%.*f", (int)decimals, (double)value);
#endif
    return appendText(out, cap, 0, buf);
}

}  // namespace

namespace hlog {

size_t formatFrame(char* out, size_t cap, const float* temps, uint8_t tempCount,
                   const bool* inputs, uint8_t inputCount, uint8_t decimals) {
    if (cap == 0) {
        return 0;
    }

    size_t pos = appendText(out, cap, 0, "Temp");
    for (uint8_t i = 0; i < tempCount; ++i) {
        pos = appendText(out, cap, pos, " ");
        if (pos >= cap) {
            break;
        }
        pos += formatTemperature(out + pos, cap - pos, temps[i], decimals);
    }

    pos = appendText(out, cap, pos, " Input");
    for (uint8_t i = 0; i < inputCount; ++i) {
        pos = appendText(out, cap, pos, inputs[i] ? " on" : " off");
    }

    pos = appendText(out, cap, pos, "\n");
    return pos;
}

}  // namespace hlog
