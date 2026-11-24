"""Check the live QoL mods and map icons (qol_mods.h): defaults (all off), each toggle's values, the two panels' Show all / Hide all / Reset all,
sanitising, and the settings.txt round trip."""
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
    // Defaults: every mod starts OFF, the clock and the glider at the game's own
    qol_state s = {0, 0, 0};
    assert(qol_active_count(s) == 0);
    assert(fabsf(qol_glider_mult(s.glider) - 1.0f) < 1e-6f && fabsf(qol_day_mult(s.ext) - 1.0f) < 1e-6f);
    for (int i = 0; i < QOL_ITEM_N; i++) {
        const char *v = qol_item_value(i, s);
        assert(!strcmp(v, "Off") || !strcmp(v, "Normal"));
    }
    // The two panels cover every item once: Map icons first, then QoL mods
    assert(QOL_MAP_FIRST == 0 && QOL_MAP_N == 13 && QOL_MODS_FIRST == QOL_MAP_N && QOL_MODS_FIRST + QOL_MODS_N == QOL_ITEM_N && QOL_MODS_N == 11);
    for (int i = QOL_MAP_FIRST; i < QOL_MAP_FIRST + QOL_MAP_N; i++) assert(i == QOL_ITEM_KOROK || (qol_item_bit(i) & QOL_MAP_FLAGS) == qol_item_bit(i));
    for (int i = QOL_MODS_FIRST; i < QOL_ITEM_N; i++) assert(!(qol_item_bit(i) & QOL_MAP_FLAGS));
    // The stubs' bit numbers (patches.py)
    assert(QOL_TOWERS == 1u << 11 && QOL_VILLAGES == 1u << 12 && QOL_UNVISITED == 1u << 13 && QOL_FAIRIES == 1u << 14 && QOL_MISKO == 1u << 15);
    assert(QOL_BARGAINER == 1u << 16 && QOL_OLD_MAPS == 1u << 17 && QOL_TEMPLES == 1u << 18 && QOL_NO_COLD == 1u << 19 && QOL_NO_HEAT == 1u << 20 && QOL_NO_FIRE == 1u << 21);

    // Korok: Off -> Uncollected -> All -> Off
    qol_toggle_item(QOL_ITEM_KOROK, &s);
    assert((s.flags & QOL_KOROK_MASK) == QOL_KOROK_UNCOLLECTED && !strcmp(qol_item_value(QOL_ITEM_KOROK, s), "*Uncollected"));
    qol_toggle_item(QOL_ITEM_KOROK, &s);
    assert((s.flags & QOL_KOROK_MASK) == QOL_KOROK_ALL && !strcmp(qol_item_value(QOL_ITEM_KOROK, s), "*All"));
    qol_toggle_item(QOL_ITEM_KOROK, &s);
    assert((s.flags & QOL_KOROK_MASK) == QOL_KOROK_OFF && qol_active_count(s) == 0);

    // A map icon: Off <-> Shown
    qol_toggle_item(QOL_ITEM_MISKO, &s);
    assert(s.flags == QOL_MISKO && !strcmp(qol_item_value(QOL_ITEM_MISKO, s), "*Shown") && qol_active_range(s, QOL_MAP_FIRST, QOL_MAP_N) == 1);
    qol_toggle_item(QOL_ITEM_MISKO, &s);
    assert(s.flags == 0);

    // Day length: Normal -> 2x -> 3x -> 4x -> Stopped -> Normal, and the clock's multiplier for each
    const float day[QOL_DAY_N] = {1.0f, 0.5f, 1.0f / 3.0f, 0.25f, 0.0f};
    const char *const dayv[QOL_DAY_N] = {"Normal", "*2x longer", "*3x longer", "*4x longer", "*Stopped"};
    for (int k = 1; k <= QOL_DAY_N; k++) {
        qol_toggle_item(QOL_ITEM_DAY, &s);
        int m = k % QOL_DAY_N;
        assert(QOL_EXT_DAY(s.ext) == m && fabsf(qol_day_mult(s.ext) - day[m]) < 1e-6f && !strcmp(qol_item_value(QOL_ITEM_DAY, s), dayv[m]));
    }
    // Weapon durability: Normal -> 2x -> 3x -> 5x -> Unbreakable -> Normal; the day length is left alone
    qol_toggle_item(QOL_ITEM_DAY, &s);
    const char *const durv[QOL_DUR_N] = {"Normal", "*2x", "*3x", "*5x", "*Unbreakable"};
    for (int k = 1; k <= QOL_DUR_N; k++) {
        qol_toggle_item(QOL_ITEM_DURABILITY, &s);
        int m = k % QOL_DUR_N;
        assert(QOL_EXT_DUR(s.ext) == m && QOL_EXT_DAY(s.ext) == QOL_DAY_2X && !strcmp(qol_item_value(QOL_ITEM_DURABILITY, s), durv[m]));
    }
    qol_toggle_item(QOL_ITEM_DURABILITY, &s);   // 2x

    // Glider: Off -> 1.5x -> 2.0x -> Off
    qol_toggle_item(QOL_ITEM_GLIDER, &s);
    assert(s.glider == QOL_GLIDER_15 && fabsf(qol_glider_mult(s.glider) - 1.5f) < 1e-6f && !strcmp(qol_item_value(QOL_ITEM_GLIDER, s), "*1.5x"));

    // Show all / Hide all touch only the map icons; Reset all only the QoL mods panel's items
    qol_toggle_item(QOL_ITEM_NO_COLD, &s);
    qol_map_all(&s, 1);
    assert(qol_active_range(s, QOL_MAP_FIRST, QOL_MAP_N) == QOL_MAP_N && (s.flags & QOL_KOROK_MASK) == QOL_KOROK_ALL);
    assert(qol_active_range(s, QOL_MODS_FIRST, QOL_MODS_N) == 4);   // cold, day, durability, glider
    qol_state kept = s;
    qol_mods_reset(&s);
    assert(qol_active_range(s, QOL_MODS_FIRST, QOL_MODS_N) == 0 && s.ext == 0 && s.glider == 0 && qol_active_range(s, QOL_MAP_FIRST, QOL_MAP_N) == QOL_MAP_N);
    qol_map_all(&s, 0);
    assert(qol_active_count(s) == 0 && s.flags == 0);
    s = kept;

    // Every item on
    qol_state all = {0, 0, 0};
    for (int i = 0; i < QOL_ITEM_N; i++) qol_toggle_item(i, &all);
    assert(qol_active_count(all) == QOL_ITEM_N);

    // Sanitising: unknown bits, a Korok value 3, and out-of-range modes go
    assert(qol_sanitize_flags(0xFFFFFFFFu) == (QOL_FLAGS_VALID & ~QOL_KOROK_MASK));
    assert(qol_sanitize_ext(QOL_EXT_PACK(7, 7)) == 0 && qol_sanitize_ext(QOL_EXT_PACK(QOL_DAY_STOP, QOL_DUR_UNBREAKABLE)) == QOL_EXT_PACK(QOL_DAY_STOP, QOL_DUR_UNBREAKABLE) && qol_sanitize_ext(QOL_EXT_PACK(0, 5)) == 0);
    assert(qol_sanitize_glider(-1) == QOL_GLIDER_OFF && qol_sanitize_glider(99) == QOL_GLIDER_OFF);

    // settings.txt round trip (and the old two-line form still reads)
    FILE *fp = fopen(argv[1], "w+");
    assert(fp);
    qol_write(fp, s);
    rewind(fp);
    char line[128];
    qol_state r = {0, 0, 0};
    int lines = 0;
    while (fgets(line, sizeof line, fp)) { assert(qol_parse(line, &r)); lines++; }
    fclose(fp);
    assert(lines == 3 && r.flags == s.flags && r.ext == s.ext && r.glider == s.glider);
    qol_state old = {0, 0, 0};
    assert(qol_parse("qol_flags=7fe\n", &old) && qol_parse("qol_glider=2\n", &old) && old.flags == 0x7FE && old.glider == 2 && old.ext == 0);
    assert(!qol_parse("overlay=1\n", &old));
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
