// Android port: live mid-game QoL mods state & settings persistence (all OFF by default).
// Two panels share it: "QoL mods" (world, gear, travel) and "Map icons" (which icon types the map shows).
// Shared-memory layout at dm_fps_state + 0x40 (loader.c dm_qol_set, patches.py stubs):
//   +0x40  uint32_t qol_flags   (bitmask below; 0 = all vanilla)
//   +0x44  float    glider_mult (0.0f or 1.0f = vanilla, 1.5f, 2.0f)
//   +0x48  uint32_t qol_ext     (bits 0..2 day length, bits 4..6 weapon durability; 0 = vanilla)
//   +0x4c  float    day_mult    (the game clock's step x this while the day length is not Normal)
//   +0x50 .. +0x74 and +0x100 .. +0x2ff are the durability stubs' own (the game writes them; patches.py "Weapon durability"): the wear carried over, the
//          frame count, the equipped items' Life handles, and the counts loader.c dm_qol_stats logs
#pragma once
#include <stdint.h>
#include <stdio.h>
#include <string.h>

// Bitmask written to dm_fps_state + 0x40 (the bit numbers are the stubs' in patches.py)
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
    QOL_TOWERS            = 1u << 11,
    QOL_VILLAGES          = 1u << 12,
    QOL_UNVISITED         = 1u << 13,
    QOL_FAIRIES           = 1u << 14,
    QOL_MISKO             = 1u << 15,
    QOL_BARGAINER         = 1u << 16,
    QOL_OLD_MAPS          = 1u << 17,
    QOL_TEMPLES           = 1u << 18,
    QOL_NO_COLD           = 1u << 19,
    QOL_NO_HEAT           = 1u << 20,
    QOL_NO_FIRE           = 1u << 21,
    QOL_FLAGS_VALID       = 0x3FFFFFu,
    QOL_MAP_FLAGS         = QOL_KOROK_MASK | QOL_SHRINES | QOL_CAVES | QOL_TEARS | QOL_DISPENSERS | 0x7F800u,   // bits 0..5, 11..18
};

enum {
    QOL_GLIDER_OFF = 0,
    QOL_GLIDER_15  = 1,
    QOL_GLIDER_20  = 2,
    QOL_GLIDER_N   = 3,
};

// qol_ext (dm_fps_state + 0x48)
enum { QOL_DAY_NORMAL, QOL_DAY_2X, QOL_DAY_3X, QOL_DAY_4X, QOL_DAY_STOP, QOL_DAY_N };
enum { QOL_DUR_NORMAL, QOL_DUR_2X, QOL_DUR_3X, QOL_DUR_5X, QOL_DUR_UNBREAKABLE, QOL_DUR_N };
#define QOL_EXT_DAY(e) ((int)((e) & 7u))
#define QOL_EXT_DUR(e) ((int)((e) >> 4 & 7u))
#define QOL_EXT_PACK(day, dur) ((uint32_t)(day) | (uint32_t)(dur) << 4)

typedef struct { uint32_t flags, ext; int glider; } qol_state;

// Items: the Map icons panel's first (QOL_MAP_FIRST .. QOL_MAP_FIRST + QOL_MAP_N - 1), then the QoL mods panel's
enum {
    QOL_ITEM_KOROK = 0,
    QOL_ITEM_SHRINES,
    QOL_ITEM_CAVES,
    QOL_ITEM_TEARS,
    QOL_ITEM_DISPENSERS,
    QOL_ITEM_TOWERS,
    QOL_ITEM_VILLAGES,
    QOL_ITEM_UNVISITED,
    QOL_ITEM_FAIRIES,
    QOL_ITEM_MISKO,
    QOL_ITEM_BARGAINER,
    QOL_ITEM_OLD_MAPS,
    QOL_ITEM_TEMPLES,
    QOL_ITEM_NO_FOG,
    QOL_ITEM_NO_COLD,
    QOL_ITEM_NO_HEAT,
    QOL_ITEM_NO_FIRE,
    QOL_ITEM_DAY,
    QOL_ITEM_DURABILITY,
    QOL_ITEM_NO_ZONAI_DESPAWN,
    QOL_ITEM_NO_ZONAI_LIMIT,
    QOL_ITEM_GLIDER,
    QOL_ITEM_INF_HORSE,
    QOL_ITEM_SURF_SHIELD,
    QOL_ITEM_N,
};
#define QOL_MAP_FIRST QOL_ITEM_KOROK
#define QOL_MAP_N (QOL_ITEM_TEMPLES + 1 - QOL_ITEM_KOROK)
#define QOL_MODS_FIRST QOL_ITEM_NO_FOG
#define QOL_MODS_N (QOL_ITEM_N - QOL_ITEM_NO_FOG)

static const char *const QOL_ITEM_LABELS[QOL_ITEM_N] = {
    "Korok seeds",
    "Shrines & Lightroots",
    "Caves, Wells & Chasms",
    "Dragon Tears",
    "Zonai Dispensers",
    "Skyview Towers",
    "Villages & Stables",
    "Unvisited places",
    "Great Fairies",
    "Misko's treasure",
    "Bargainer Statues",
    "Old maps",
    "Five temples",
    "Disable fog",
    "No cold damage",
    "No heat damage",
    "No fire damage",
    "Day length",
    "Weapon durability",
    "No Zonai despawn",
    "No 21 Zonai limit",
    "Paraglider speed",
    "Infinite horse stamina",
    "Unbreakable surf shield",
};

// The on/off items: their bit (0 for the multi-value items: Korok seeds, Day length, Weapon durability, Paraglider speed)
static inline uint32_t qol_item_bit(int item) {
    static const uint32_t BITS[QOL_ITEM_N] = {
        [QOL_ITEM_SHRINES] = QOL_SHRINES, [QOL_ITEM_CAVES] = QOL_CAVES, [QOL_ITEM_TEARS] = QOL_TEARS, [QOL_ITEM_DISPENSERS] = QOL_DISPENSERS,
        [QOL_ITEM_TOWERS] = QOL_TOWERS, [QOL_ITEM_VILLAGES] = QOL_VILLAGES, [QOL_ITEM_UNVISITED] = QOL_UNVISITED, [QOL_ITEM_FAIRIES] = QOL_FAIRIES,
        [QOL_ITEM_MISKO] = QOL_MISKO, [QOL_ITEM_BARGAINER] = QOL_BARGAINER, [QOL_ITEM_OLD_MAPS] = QOL_OLD_MAPS, [QOL_ITEM_TEMPLES] = QOL_TEMPLES,
        [QOL_ITEM_NO_FOG] = QOL_NO_FOG, [QOL_ITEM_NO_COLD] = QOL_NO_COLD, [QOL_ITEM_NO_HEAT] = QOL_NO_HEAT, [QOL_ITEM_NO_FIRE] = QOL_NO_FIRE,
        [QOL_ITEM_NO_ZONAI_DESPAWN] = QOL_NO_ZONAI_DESPAWN, [QOL_ITEM_NO_ZONAI_LIMIT] = QOL_NO_ZONAI_LIMIT, [QOL_ITEM_INF_HORSE] = QOL_INF_HORSE,
        [QOL_ITEM_SURF_SHIELD] = QOL_SURF_SHIELD,
    };
    return item >= 0 && item < QOL_ITEM_N ? BITS[item] : 0;
}

static inline uint32_t qol_sanitize_flags(uint32_t flags) {
    flags &= QOL_FLAGS_VALID;
    if ((flags & QOL_KOROK_MASK) > QOL_KOROK_ALL) flags &= ~QOL_KOROK_MASK;
    return flags;
}

static inline uint32_t qol_sanitize_ext(uint32_t ext) {
    int day = QOL_EXT_DAY(ext), dur = QOL_EXT_DUR(ext);
    return QOL_EXT_PACK(day < QOL_DAY_N ? day : QOL_DAY_NORMAL, dur < QOL_DUR_N ? dur : QOL_DUR_NORMAL);
}

static inline int qol_sanitize_glider(int glider) {
    return (glider >= 0 && glider < QOL_GLIDER_N) ? glider : QOL_GLIDER_OFF;
}

static inline qol_state qol_sanitize(qol_state s) {
    s.flags = qol_sanitize_flags(s.flags); s.ext = qol_sanitize_ext(s.ext); s.glider = qol_sanitize_glider(s.glider);
    return s;
}

static inline float qol_glider_mult(int glider) {
    return glider == QOL_GLIDER_15 ? 1.5f : glider == QOL_GLIDER_20 ? 2.0f : 1.0f;
}

// The game clock's step is multiplied by this (patches.py day length stub); 1.0 = the game's own
static inline float qol_day_mult(uint32_t ext) {
    switch (QOL_EXT_DAY(ext)) {
    case QOL_DAY_2X:   return 0.5f;
    case QOL_DAY_3X:   return 1.0f / 3.0f;
    case QOL_DAY_4X:   return 0.25f;
    case QOL_DAY_STOP: return 0.0f;
    default:           return 1.0f;
    }
}

static inline int qol_item_on(int item, qol_state s) {
    s = qol_sanitize(s);
    switch (item) {
    case QOL_ITEM_KOROK:      return (s.flags & QOL_KOROK_MASK) != 0;
    case QOL_ITEM_DAY:        return QOL_EXT_DAY(s.ext) != QOL_DAY_NORMAL;
    case QOL_ITEM_DURABILITY: return QOL_EXT_DUR(s.ext) != QOL_DUR_NORMAL;
    case QOL_ITEM_GLIDER:     return s.glider != QOL_GLIDER_OFF;
    default:                  return (s.flags & qol_item_bit(item)) != 0;
    }
}

// How many items of [first, first + n) are not at their vanilla value
static inline int qol_active_range(qol_state s, int first, int n) {
    int c = 0;
    for (int i = first; i < first + n && i < QOL_ITEM_N; i++) c += qol_item_on(i, s);
    return c;
}
static inline int qol_active_count(qol_state s) { return qol_active_range(s, 0, QOL_ITEM_N); }

static inline void qol_toggle_item(int item, qol_state *st) {
    qol_state s = qol_sanitize(*st);
    switch (item) {
    case QOL_ITEM_KOROK: s.flags = (s.flags & ~QOL_KOROK_MASK) | (((s.flags & QOL_KOROK_MASK) + 1u) % 3u); break;
    case QOL_ITEM_DAY:   s.ext = QOL_EXT_PACK((QOL_EXT_DAY(s.ext) + 1) % QOL_DAY_N, QOL_EXT_DUR(s.ext)); break;
    case QOL_ITEM_DURABILITY: s.ext = QOL_EXT_PACK(QOL_EXT_DAY(s.ext), (QOL_EXT_DUR(s.ext) + 1) % QOL_DUR_N); break;
    case QOL_ITEM_GLIDER: s.glider = (s.glider + 1) % QOL_GLIDER_N; break;
    default: s.flags ^= qol_item_bit(item); break;
    }
    *st = s;
}

// The Map icons panel's Show all (every icon type, Korok seeds All) and Hide all; the QoL mods panel's Reset all (its own items only)
static inline void qol_map_all(qol_state *st, int on) {
    qol_state s = qol_sanitize(*st);
    s.flags = (s.flags & ~QOL_MAP_FLAGS) | (on ? (QOL_MAP_FLAGS & ~QOL_KOROK_MASK) | QOL_KOROK_ALL : 0u);
    *st = s;
}
static inline void qol_mods_reset(qol_state *st) {
    qol_state s = qol_sanitize(*st);
    s.flags &= QOL_MAP_FLAGS; s.ext = 0; s.glider = QOL_GLIDER_OFF;
    *st = s;
}

// Right-column value string for ov_save_panel ('*' prefix draws in accent colour)
static inline const char *qol_item_value(int item, qol_state s) {
    s = qol_sanitize(s);
    switch (item) {
    case QOL_ITEM_KOROK: {
        uint32_t km = s.flags & QOL_KOROK_MASK;
        return km == QOL_KOROK_UNCOLLECTED ? "*Uncollected" : km == QOL_KOROK_ALL ? "*All" : "Off";
    }
    case QOL_ITEM_DAY: {
        static const char *const V[QOL_DAY_N] = {"Normal", "*2x longer", "*3x longer", "*4x longer", "*Stopped"};
        return V[QOL_EXT_DAY(s.ext)];
    }
    case QOL_ITEM_DURABILITY: {
        static const char *const V[QOL_DUR_N] = {"Normal", "*2x", "*3x", "*5x", "*Unbreakable"};
        return V[QOL_EXT_DUR(s.ext)];
    }
    case QOL_ITEM_GLIDER: return s.glider == QOL_GLIDER_15 ? "*1.5x" : s.glider == QOL_GLIDER_20 ? "*2.0x" : "Off";
    default:
        if (item < 0 || item >= QOL_ITEM_N) return "Off";
        if (item < QOL_MAP_FIRST + QOL_MAP_N) return qol_item_on(item, s) ? "*Shown" : "Off";
        return qol_item_on(item, s) ? "*On" : "Off";
    }
}

static inline int qol_parse(const char *line, qol_state *s) {
    unsigned int u = 0;
    int v = 0;
    if (sscanf(line, "qol_flags=%x", &u) == 1) { s->flags = qol_sanitize_flags((uint32_t)u); return 1; }
    if (sscanf(line, "qol_ext=%x", &u) == 1) { s->ext = qol_sanitize_ext((uint32_t)u); return 1; }
    if (sscanf(line, "qol_glider=%d", &v) == 1) { s->glider = qol_sanitize_glider(v); return 1; }
    return 0;
}

static inline void qol_write(FILE *f, qol_state s) {
    s = qol_sanitize(s);
    fprintf(f, "qol_flags=%x\nqol_glider=%d\nqol_ext=%x\n", (unsigned)s.flags, s.glider, (unsigned)s.ext);
}
