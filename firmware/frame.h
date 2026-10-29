#ifndef HLOG_FRAME_H
#define HLOG_FRAME_H

#include <stddef.h>
#include <stdint.h>

namespace hlog {

// Formats one device frame, including the trailing newline:
//
//   Temp <t0> <t1> ... Input <on|off> ...
//
// Fields are single-space separated and the temperature count is explicit, so
// the same code emits the 4-sensor (v1a) and 6-sensor (v1b) shapes. Returns the
// number of bytes written, excluding the terminating NUL, or 0 when `cap` is 0.
// Output is truncated safely and always NUL-terminated.
size_t formatFrame(char* out, size_t cap, const float* temps, uint8_t tempCount,
                   const bool* inputs, uint8_t inputCount, uint8_t decimals = 1);

}  // namespace hlog

#endif  // HLOG_FRAME_H
