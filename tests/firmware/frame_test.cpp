// Host-side test for the firmware frame formatter.
//
// It compiles with the system g++ (no Arduino toolchain needed) and checks the
// formatter against the shared fixture used by the Python contract test.
//
//   g++ -std=c++17 -Wall -Wextra -Werror -I firmware firmware/frame.cpp
//       tests/firmware/frame_test.cpp -o /tmp/frame_test
//   /tmp/frame_test tests/fixtures/firmware_frames.tsv

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

#include "frame.h"

namespace {

struct Case {
    std::string id;
    int decimals = 1;
    std::vector<float> temps;
    std::vector<uint8_t> inputs;
    std::string expected;
};

std::vector<std::string> split(const std::string& text, char separator) {
    std::vector<std::string> parts;
    std::string current;
    for (char c : text) {
        if (c == separator) {
            parts.push_back(current);
            current.clear();
        } else {
            current.push_back(c);
        }
    }
    parts.push_back(current);
    return parts;
}

std::string unescapeNewlines(const std::string& text) {
    std::string result;
    for (size_t i = 0; i < text.size(); ++i) {
        if (text[i] == '\\' && i + 1 < text.size() && text[i + 1] == 'n') {
            result.push_back('\n');
            ++i;
        } else {
            result.push_back(text[i]);
        }
    }
    return result;
}

bool loadCase(const std::string& line, Case* out) {
    const std::vector<std::string> columns = split(line, '\t');
    if (columns.size() != 5) {
        return false;
    }
    out->id = columns[0];
    out->decimals = columns[1].empty() ? 1 : std::stoi(columns[1]);
    out->temps.clear();
    for (const std::string& value : split(columns[2], ',')) {
        out->temps.push_back(std::stof(value));
    }
    out->inputs.clear();
    for (const std::string& value : split(columns[3], ',')) {
        out->inputs.push_back(value == "on" ? 1 : 0);
    }
    out->expected = unescapeNewlines(columns[4]);
    return true;
}

}  // namespace

int main(int argc, char** argv) {
    const char* path = argc > 1 ? argv[1] : "tests/fixtures/firmware_frames.tsv";
    std::ifstream input(path);
    if (!input) {
        std::fprintf(stderr, "cannot open fixture: %s\n", path);
        return 2;
    }

    int checked = 0;
    int failures = 0;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty() || line[0] == '#') {
            continue;
        }
        Case test_case;
        if (!loadCase(line, &test_case)) {
            std::fprintf(stderr, "malformed fixture row: %s\n", line.c_str());
            ++failures;
            continue;
        }
        bool input_flags[8] = {};
        for (size_t i = 0; i < test_case.inputs.size() && i < 8; ++i) {
            input_flags[i] = test_case.inputs[i] != 0;
        }
        char buffer[256];
        const size_t written = hlog::formatFrame(
            buffer, sizeof(buffer), test_case.temps.data(),
            static_cast<uint8_t>(test_case.temps.size()), input_flags,
            static_cast<uint8_t>(test_case.inputs.size()),
            static_cast<uint8_t>(test_case.decimals));
        ++checked;
        if (test_case.expected != buffer || written != test_case.expected.size()) {
            std::fprintf(stderr, "FAIL %s\n  expected: %s\n  actual:   %s\n",
                         test_case.id.c_str(), test_case.expected.c_str(), buffer);
            ++failures;
        }
    }

    // Truncation must stay inside the buffer and stay NUL-terminated.
    char small[16];
    std::memset(small, 'x', sizeof(small));
    const float temps[1] = {1.5f};
    const bool inputs[1] = {true};
    const size_t written = hlog::formatFrame(small, sizeof(small), temps, 1, inputs, 1, 1);
    if (written != sizeof(small) - 1 || small[sizeof(small) - 1] != '\0') {
        std::fprintf(stderr, "FAIL truncation: written=%zu tail=%d\n", written,
                     static_cast<int>(small[sizeof(small) - 1]));
        ++failures;
    }

    if (hlog::formatFrame(small, 0, temps, 1, inputs, 1, 1) != 0) {
        std::fprintf(stderr, "FAIL zero-capacity buffer returned a length\n");
        ++failures;
    }

    if (failures != 0) {
        std::fprintf(stderr, "%d of %d frame checks failed\n", failures, checked);
        return 1;
    }
    std::printf("%d frame checks passed\n", checked);
    return 0;
}
