// Android port: live mid-game QoL mods state & settings persistence (all OFF by default).
// Shared-memory layout at dm_fps_state + 0x40 (loader.c dm_qol_set, patches.py stubs):
//   +0x40  uint32_t qol_flags   (bitmask below; 0 = all vanilla)
//   +0x44  float    glider_mult (0.0f or 1.0f = vanilla, 1.5f, 2.0f)
#pragma once
#include <stdint.h>
#include <stdio.h>
#include <string.h>

// Bitmask written to dm_fps_state + 0x40
enum {
    QOL_KOROK_OFF         = 0u,
    QOL_KOROK_UNCOLLECTED = 1u,
    QOL_KOROK_ALL         = 2u,
    QOL_KOROK_MASK        = 3u,
    QOL_SHRINES           = 1u << 2,
    QOL_CAVES             = 1u << 3,
    QOL_TEARS             = 1u << 4,
    QOL_DISPENSERS        = 1u << 5,
    QOL_NO_FOG            = 1u << 6,
    QOL_NO_ZONAI_DESPAWN  = 1u << 7,
    QOL_NO_ZONAI_LIMIT    = 1u << 8,
    QOL_INF_HORSE         = 1u << 9,
    QOL_SURF_SHIELD       = 1u << 10,
    QOL_FLAGS_VALID       = 0x7FFu,
};

enum {
    QOL_GLIDER_OFF = 0,
    QOL_GLIDER_15  = 1,
    QOL_GLIDER_20  = 2,
    QOL_GLIDER_N   = 3,
};

// Menu item indices across the 2 pages (6 rows per page; last slot on page 2 is Reset all to Off)
enum {
    QOL_ITEM_KOROK = 0,
    QOL_ITEM_SHRINES,
    QOL_ITEM_CAVES,
    QOL_ITEM_TEARS,
    QOL_ITEM_DISPENSERS,
    QOL_ITEM_NO_FOG,
    QOL_ITEM_NO_ZONAI_DESPAWN,
    QOL_ITEM_NO_ZONAI_LIMIT,
    QOL_ITEM_GLIDER,
    QOL_ITEM_INF_HORSE,
    QOL_ITEM_SURF_SHIELD,
    QOL_ITEM_N,
};

static const char *const QOL_ITEM_LABELS[QOL_ITEM_N] = {
    "Korok map",
    "Shrines & Lightroots",
    "Caves, Wells & Chasms",
    "Dragon Tears",
    "Zonai Dispensers",
    "Disable fog",
    "No Zonai despawn",
    "No 21 Zonai limit",
    "Paraglider speed",
    "Infinite horse stamina",
    "Unbreakable surf shield",
};

static inline uint32_t qol_sanitize_flags(uint32_t flags) {
    flags &= QOL_FLAGS_VALID;
    if ((flags & QOL_KOROK_MASK) > QOL_KOROK_ALL) flags &= ~QOL_KOROK_MASK;
    return flags;
}

static inline int qol_sanitize_glider(int glider) {
    return (glider >= 0 && glider < QOL_GLIDER_N) ? glider : QOL_GLIDER_OFF;
}

static inline float qol_glider_mult(int glider) {
    return glider == QOL_GLIDER_15 ? 1.5f : glider == QOL_GLIDER_20 ? 2.0f : 1.0f;
}

static inline int qol_active_count(uint32_t flags, int glider) {
    flags = qol_sanitize_flags(flags);
    glider = qol_sanitize_glider(glider);
    int n = (flags & QOL_KOROK_MASK) != 0 ? 1 : 0;
    for (int bit = 2; bit <= 10; bit++) if (flags & (1u << bit)) n++;
    if (glider != QOL_GLIDER_OFF) n++;
    return n;
}

static inline void qol_toggle_item(int item, uint32_t *flags, int *glider) {
    uint32_t f = qol_sanitize_flags(*flags);
    int g = qol_sanitize_glider(*glider);
    switch (item) {
    case QOL_ITEM_KOROK: {
        uint32_t km = ((f & QOL_KOROK_MASK) + 1u) % 3u;
        f = (f & ~QOL_KOROK_MASK) | km;
        break;
    }
    case QOL_ITEM_SHRINES:          f ^= QOL_SHRINES; break;
    case QOL_ITEM_CAVES:            f ^= QOL_CAVES; break;
    case QOL_ITEM_TEARS:            f ^= QOL_TEARS; break;
    case QOL_ITEM_DISPENSERS:       f ^= QOL_DISPENSERS; break;
    case QOL_ITEM_NO_FOG:           f ^= QOL_NO_FOG; break;
    case QOL_ITEM_NO_ZONAI_DESPAWN: f ^= QOL_NO_ZONAI_DESPAWN; break;
    case QOL_ITEM_NO_ZONAI_LIMIT:   f ^= QOL_NO_ZONAI_LIMIT; break;
    case QOL_ITEM_GLIDER:           g = (g + 1) % QOL_GLIDER_N; break;
    case QOL_ITEM_INF_HORSE:        f ^= QOL_INF_HORSE; break;
    case QOL_ITEM_SURF_SHIELD:      f ^= QOL_SURF_SHIELD; break;
    default: break;
    }
    *flags = f;
    *glider = g;
}

// Right-column value string for ov_save_panel ('*' prefix draws in accent colour)
static inline const char *qol_item_value(int item, uint32_t flags, int glider) {
    flags = qol_sanitize_flags(flags);
    glider = qol_sanitize_glider(glider);
    switch (item) {
    case QOL_ITEM_KOROK: {
        uint32_t km = flags & QOL_KOROK_MASK;
        return km == QOL_KOROK_UNCOLLECTED ? "*Uncollected" : km == QOL_KOROK_ALL ? "*All" : "Off";
    }
    case QOL_ITEM_SHRINES:          return (flags & QOL_SHRINES) ? "*On" : "Off";
    case QOL_ITEM_CAVES:            return (flags & QOL_CAVES) ? "*On" : "Off";
    case QOL_ITEM_TEARS:            return (flags & QOL_TEARS) ? "*On" : "Off";
    case QOL_ITEM_DISPENSERS:       return (flags & QOL_DISPENSERS) ? "*On" : "Off";
    case QOL_ITEM_NO_FOG:           return (flags & QOL_NO_FOG) ? "*On" : "Off";
    case QOL_ITEM_NO_ZONAI_DESPAWN: return (flags & QOL_NO_ZONAI_DESPAWN) ? "*On" : "Off";
    case QOL_ITEM_NO_ZONAI_LIMIT:   return (flags & QOL_NO_ZONAI_LIMIT) ? "*On" : "Off";
    case QOL_ITEM_GLIDER:           return glider == QOL_GLIDER_15 ? "*1.5x" : glider == QOL_GLIDER_20 ? "*2.0x" : "Off";
    case QOL_ITEM_INF_HORSE:        return (flags & QOL_INF_HORSE) ? "*On" : "Off";
    case QOL_ITEM_SURF_SHIELD:      return (flags & QOL_SURF_SHIELD) ? "*On" : "Off";
    default:                        return "Off";
    }
}

static inline int qol_parse(const char *line, uint32_t *flags, int *glider) {
    unsigned int uf = 0;
    int gv = 0;
    if (sscanf(line, "qol_flags=%x", &uf) == 1) { *flags = qol_sanitize_flags((uint32_t)uf); return 1; }
    if (sscanf(line, "qol_glider=%d", &gv) == 1) { *glider = qol_sanitize_glider(gv); return 1; }
    return 0;
}

static inline void qol_write(FILE *f, uint32_t flags, int glider) {
    fprintf(f, "qol_flags=%x\nqol_glider=%d\n", (unsigned)qol_sanitize_flags(flags), qol_sanitize_glider(glider));
}
