"""Check live QoL mods defaults (all OFF), toggle transitions, sanitization, and settings.txt round-trip."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
DM = ROOT / 'nxnative/dm'


class QolMods(unittest.TestCase):
    def test_defaults_toggles_and_persistence(self):
        cc = shutil.which('cc') or shutil.which('clang')
        if not cc:
            self.skipTest('a C compiler is needed for the QoL mods check')
        harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "qol_mods.h"

int main(int argc, char **argv) {
    assert(argc == 2);
    // Defaults: every single mod must start OFF
    uint32_t f = 0;
    int g = 0;
    assert(qol_active_count(f, g) == 0);
    assert(fabsf(qol_glider_mult(g) - 1.0f) < 1e-6f);
    for (int i = 0; i < QOL_ITEM_N; i++) {
        assert(strcmp(qol_item_value(i, f, g), "Off") == 0);
    }

    // Korok 3-way cycle: Off -> Uncollected -> All -> Off
    qol_toggle_item(QOL_ITEM_KOROK, &f, &g);
    assert((f & QOL_KOROK_MASK) == QOL_KOROK_UNCOLLECTED && strcmp(qol_item_value(QOL_ITEM_KOROK, f, g), "*Uncollected") == 0);
    assert(qol_active_count(f, g) == 1);
    qol_toggle_item(QOL_ITEM_KOROK, &f, &g);
    assert((f & QOL_KOROK_MASK) == QOL_KOROK_ALL && strcmp(qol_item_value(QOL_ITEM_KOROK, f, g), "*All") == 0);
    assert(qol_active_count(f, g) == 1);
    qol_toggle_item(QOL_ITEM_KOROK, &f, &g);
    assert((f & QOL_KOROK_MASK) == QOL_KOROK_OFF && strcmp(qol_item_value(QOL_ITEM_KOROK, f, g), "Off") == 0);
    assert(qol_active_count(f, g) == 0);

    // Paraglider 3-way cycle: Off (1.0x) -> 1.5x -> 2.0x -> Off (1.0x)
    qol_toggle_item(QOL_ITEM_GLIDER, &f, &g);
    assert(g == QOL_GLIDER_15 && fabsf(qol_glider_mult(g) - 1.5f) < 1e-6f && strcmp(qol_item_value(QOL_ITEM_GLIDER, f, g), "*1.5x") == 0);
    qol_toggle_item(QOL_ITEM_GLIDER, &f, &g);
    assert(g == QOL_GLIDER_20 && fabsf(qol_glider_mult(g) - 2.0f) < 1e-6f && strcmp(qol_item_value(QOL_ITEM_GLIDER, f, g), "*2.0x") == 0);
    qol_toggle_item(QOL_ITEM_GLIDER, &f, &g);
    assert(g == QOL_GLIDER_OFF && fabsf(qol_glider_mult(g) - 1.0f) < 1e-6f && strcmp(qol_item_value(QOL_ITEM_GLIDER, f, g), "Off") == 0);

    // Toggle all 11 items ON -> active count == 11
    for (int i = 0; i < QOL_ITEM_N; i++) qol_toggle_item(i, &f, &g);
    assert(qol_active_count(f, g) == QOL_ITEM_N);
    assert(f == (QOL_KOROK_UNCOLLECTED | QOL_SHRINES | QOL_CAVES | QOL_TEARS | QOL_DISPENSERS |
                 QOL_NO_FOG | QOL_NO_ZONAI_DESPAWN | QOL_NO_ZONAI_LIMIT | QOL_INF_HORSE | QOL_SURF_SHIELD));
    assert(g == QOL_GLIDER_15);

    // Sanitization rejects out-of-range bits and Korok=3
    assert(qol_sanitize_flags(0xFFFFFFFFu) == (QOL_FLAGS_VALID & ~QOL_KOROK_MASK));
    assert(qol_sanitize_glider(-1) == QOL_GLIDER_OFF && qol_sanitize_glider(99) == QOL_GLIDER_OFF);

    // Settings persistence round-trip
    FILE *fp = fopen(argv[1], "w+b"); assert(fp);
    qol_write(fp, f, g);
    long n = ftell(fp); rewind(fp);
    char *buf = calloc((size_t)n + 1, 1); assert(buf && fread(buf, 1, (size_t)n, fp) == (size_t)n);
    fclose(fp);

    uint32_t f2 = 0; int g2 = 0;
    for (char *l = strtok(buf, "\n"); l; l = strtok(NULL, "\n")) {
        char line[64]; snprintf(line, sizeof line, "%s\n", l);
        assert(qol_parse(line, &f2, &g2));
    }
    assert(f2 == f && g2 == g);
    assert(!qol_parse("overlay=1\n", &f2, &g2));
    free(buf);
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='nx2a_qol_') as tmp:
            tmp = Path(tmp)
            c, exe = tmp / 'check.c', tmp / 'check'
            c.write_text(harness, encoding='utf-8')
            res = subprocess.run([cc, '-std=gnu11', '-Wall', '-Wextra', '-Werror', f'-I{DM / "android"}', str(c), '-o', str(exe)],
                                 capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            res = subprocess.run([str(exe), str(tmp / 'settings.txt')], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)


if __name__ == '__main__':
    unittest.main()
