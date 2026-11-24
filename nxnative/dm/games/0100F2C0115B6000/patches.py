# The Legend of Zelda: Tears of the Kingdom (0100F2C0115B6000): the rewriter's patches of this game's own builds. dm/tools/patch_nso.py loads every profile's patches.py and applies those of a module's NSO build ID;
# CUTS, OBS and FRAME_STEP as described there ("Registered patches"). Patches of Nintendo SDK module builds are in dm/tools/sdk_patches.py
import struct
from nso_asm import ADRP, B, NOP, STP_PRE

# Tears of the Kingdom picks a present interval each frame (main+0x2db174: 2 = 30 fps, 3 under load) and steps its game time by 60 / fps (int fps at timing +0x50, read at main+0x2daa54
# and main+0x3e562c). The stub replaces that logic: int fps = 60 / step, and the float fps (timing +0x24, unused, per masagrator's FPSLocker config for this build, which found the
# sites) the same, which the consumers read. Until the host has decided a step (the first frames) the step is the measured frame time (timing frame +0xd8, 19.2 MHz
# ticks), clamped to [1 / cap, 1 / 15 s]; game time that ran ahead after a short frame (the "lead", at most 0.25 s; totk-mobile) is paid back by later frames. Prerendered movies set a 30 cap (flag set and cleared around main+0x2b36100 /
# main+0x2b33918), the D-pad menu fade starts at full rate (FPSLocker's fix at main+0x1fbc80) and the swapchain argument at main+0xbe14a8 becomes 1 as in FPSLocker
def frame_step(ctx):
    here, emit, fs_site, fs_put, FS_STATE_OFF = ctx.here, ctx.emit, ctx.site, ctx.put, ctx.state
    # frame step (replaces ldrb w9,[x0,#0x58], the first instruction after the prologue)
    fs_site(0x2db18c, '09604139')
    start = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (0xB9405A11,   # ldr w17,[x16,#0x58]    frames stepped (the QoL durability stubs' clock; x17 is free at a function's first instruction)
              0x11000631,   # add w17,w17,#1
              0xB9005A11,   # str w17,[x16,#0x58]
              0xbd400200,   # ldr s0,[x16]           target fps
              0x1e202008,   # fcmp s0,#0.0
              0x54000660,   # b.eq off (+51)        target 0: original path
              0xb9402202,   # ldr w2,[x16,#0x20]     step in ticks (60 Hz vsyncs or 120 Hz refreshes)
              0x340001c2,   # cbz w2,elapsed (+14)   not decided yet: by the measured frame time
              0xb9402a05,   # ldr w5,[x16,#0x28]     tick hz (0 = 60, 120 = 120 Hz)
              0x35000045,   # cbnz w5,+2
              0x52800785,   # mov w5,#60
              0x1e2300a3,   # ucvtf s3,w5
              0x1e230041,   # ucvtf s1,w2
              0x1e211872,   # fdiv s18,s3,s1         float fps = tick_hz / step (exact for 120 / {2,3,4,5,6})
              0xbd002412,   # str s18,[x0,#0x24]     float fps
              0x1ac208a5,   # udiv w5,w5,w2          integer fps = tick_hz / step
              0xb9005005,   # str w5,[x0,#0x50]      integer fps
              0xf9401a04,   # ldr x4,[x16,#0x30]
              0x8b224084,   # add x4,x4,w2,uxtw
              0xf9001a04):  # str x4,[x16,#0x30]     ticks stepped (in tick_hz units)
        emit(w)
    emit(B(here(), 0x2db284))                                       # the original epilogue
    for w in (0xf9406c22,   # elapsed: ldr x2,[x1,#0xd8]  last frame time in 19.2 MHz ticks
              0x9e630041,   # ucvtf d1,x2
              0x529f0003,   # mov w3,#0xf800
              0x72a02483,   # movk w3,#0x124,lsl #16 (19,200,000)
              0x1e630062,   # ucvtf d2,w3
              0x1e621821,   # fdiv d1,d1,d2          elapsed seconds
              0xb9400604,   # ldr w4,[x16,#4]        movie flag
              0x1e27d003,   # fmov s3,#30.0
              0x7100009f,   # cmp w4,#0
              0x1e201c60,   # fcsel s0,s3,s0,ne      cap = movie ? 30 : target
              0x1e22c000,   # fcvt d0,s0
              0x1e6e1003,   # fmov d3,#1.0
              0x1e601864,   # fdiv d4,d3,d0          shortest step 1 / cap
              0x1e65d005,   # fmov d5,#15.0
              0x1e651865,   # fdiv d5,d3,d5          longest step 1 / 15
              0xfd400606,   # ldr d6,[x16,#8]        lead
              0x1e663827,   # fsub d7,d1,d6
              0x1e6448e7,   # fmax d7,d7,d4
              0x1e6558e7,   # fmin d7,d7,d5          step = clamp(elapsed - lead)
              0x1e6728c6,   # fadd d6,d6,d7
              0x1e6138c6,   # fsub d6,d6,d1          lead += step - elapsed
              0x2f00e410,   # movi d16,#0
              0x1e7048c6,   # fmax d6,d6,d16
              0x1e6a1011,   # fmov d17,#0.25
              0x1e7158c6,   # fmin d6,d6,d17         lead in [0, 0.25]
              0xfd000606,   # str d6,[x16,#8]
              0x1e671872,   # fdiv d18,d3,d7         fps = 1 / step
              0x1e624252,   # fcvt s18,d18
              0xbd002412,   # str s18,[x0,#0x24]     float fps
              0x1e380245,   # fcvtzs w5,s18
              0xb9005005,   # str w5,[x0,#0x50]      integer fps
              0xfd400e13,   # ldr d19,[x16,#0x18]
              0x1e672a73,   # fadd d19,d19,d7
              0xfd000e13):  # str d19,[x16,#0x18]    game seconds stepped
        emit(w)
    emit(B(here(), 0x2db284))                                       # the original epilogue
    emit(0x39416009); emit(B(here(), 0x2db190))                     # off: ldrb w9,[x0,#0x58]; back
    fs_put(0x2db18c, [B(0x2db18c, start)], 'frame step from the host in whole vsyncs, by elapsed time until it has decided one (state page target fps; 0 = original interval logic)')
    # the two readers of the integer fps: float fps when on; the scvtf a few instructions later moves into the stub (s0 is not touched in between)
    for site, cvt, r in ((0x2daa54, 0x2daa6c, 19), (0x3e562c, 0x3e5638, 22)):
        fs_site(site, struct.pack('<I', 0xbd425000 | r << 5).hex()); fs_site(cvt, '00d8215e')
        start = here(); emit(STP_PRE(16, 17, 31, -16)); emit(ADRP(16, here(), FS_STATE_OFF))
        for w in (0xb9400211,                # ldr w17,[x16]
                  0x34000071,                # cbz w17,off (+12)
                  0xbd422400 | r << 5,       # ldr s0,[xR,#0x224]  float fps
                  0x14000003,                # b done (+12)
                  0xbd425000 | r << 5,       # off: ldr s0,[xR,#0x250]  integer fps
                  0x5e21d800,                # scvtf s0,s0
                  0xa8c147f0):               # done: ldp x16,x17,[sp],#16
            emit(w)
        emit(B(here(), site + 4))
        fs_put(site, [B(site, start)], 'game step reads the float fps (original integer fps and scvtf when off)')
        fs_put(cvt, [NOP], 'scvtf moved into the stub at the load')
    # D-pad menu fade (w8 is overwritten right after the site)
    fs_site(0x1fbc80, '0820201e0a04081f')
    start = here(); emit(ADRP(8, here(), FS_STATE_OFF))
    for w in (0xb9400108, 0x340001a8,       # ldr w8,[x8]; cbz w8,off (+52)
              0x1e202028, 0x54000101,       # fcmp s1,#0.0; b.ne go
              0x785fa308, 0x7100151f, 0x540000a1,   # ldurh w8,[x24,#-6]; cmp w8,#5; b.ne go
              0x785f8308, 0x7100151f, 0x54000041,   # ldurh w8,[x24,#-8]; cmp w8,#5; b.ne go
              0x1e2e1008,                   # fmov s8,#1.0
              0x1f08040a, 0x1e202008, 0x14000003,   # go: fmadd s10,s0,s8,s1; fcmp s0,#0.0; b end
              0x1e202008, 0x1f08040a):      # off: the original fcmp s0,#0.0; fmadd s10,s0,s8,s1
        emit(w)
    emit(B(here(), 0x1fbc88))
    fs_put(0x1fbc80, [B(0x1fbc80, start), NOP], 'D-pad menu fade starts at full rate under fractional steps (FPSLocker)')
    # swapchain argument (x16 is dead before the bl that follows)
    fs_site(0xbe14a8, '61a24039')
    start = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (0xb9400210, 0x34000070, 0x52800021, 0x14000002, 0x3940a261):   # ldr w16,[x16]; cbz w16,off; mov w1,#1; b end; off: ldrb w1,[x19,#0x28]
        emit(w)
    emit(B(here(), 0xbe14ac))
    fs_put(0xbe14a8, [B(0xbe14a8, start)], 'swapchain argument 1 when on (FPSLocker)')
    # prerendered movie start and end set and clear the flag (x16 / x17 are free at a call)
    fs_site(0x2b36100, 'b6f37097'); fs_site(0x2b33918, 'de170214')
    start = here(); emit(ADRP(16, here(), FS_STATE_OFF)); emit(0x52800031); emit(0xb9000611); emit(B(here(), 0x772fd8))   # mov w17,#1; str w17,[x16,#4]; tail call
    fs_put(0x2b36100, [B(0x2b36100, start) | 0x80000000], 'movie starts: 30 fps cap')
    start = here(); emit(ADRP(16, here(), FS_STATE_OFF)); emit(0xb900061f); emit(B(here(), 0x2bb9890))                     # str wzr,[x16,#4]; tail call
    fs_put(0x2b33918, [B(0x2b33918, start)], 'movie ends')
    # Render scale (state +0x10, float written by the loader: DM_RENDER_SCALE, 1.0 by default). main+0xd5c24 sizes each view: screen size x the view's scale (5/6 for the scene: 1600x896
    # docked) x the dynamic-resolution multiplier, clamped to 8..16384 and floored to the view's alignment. The stub multiplies both extents by the factor (s6, w8 and the flags are dead
    # at main+0xd5cc0: s6 is set to 8.0 right after); any factor but 1.0 also replaces the dynamic multiplier (main+0xd5d80) with 1, so the size is fixed. 1.0 = bit-exact original
    fs_site(0xd5cc0, '08d0a8524008251e6108241e0401271e'); fs_site(0xd5d80, '062940bd')
    start = here(); emit(ADRP(8, here(), FS_STATE_OFF))
    for w in (0xbd401106,   # ldr s6,[x8,#0x10]   render scale
              0x1e250840,   # fmul s0,s2,s5       (original)
              0x1e240861,   # fmul s1,s3,s4       (original)
              0x1e2020c8,   # fcmp s6,#0.0
              0x5400006d,   # b.le skip (+12)     not set
              0x1e260800,   # fmul s0,s0,s6
              0x1e260821,   # fmul s1,s1,s6
              0x52a8d008,   # skip: mov w8,#0x46800000 (original)
              0x1e270104):  # fmov s4,w8          (original)
        emit(w)
    emit(B(here(), 0xd5cd0))
    fs_put(0xd5cc0, [B(0xd5cc0, start)], 'view render size x the host render scale (1.0 = original)'); ctx.render_scale = 1
    start = here(); emit(0xbd402906); emit(ADRP(8, here(), FS_STATE_OFF))   # ldr s6,[x8,#0x28] (original: the dynamic multiplier); x8 is dead after it
    for w in (0xbd401107,   # ldr s7,[x8,#0x10]
              0x1e2e1010,   # fmov s16,#1.0
              0x1e3020e0,   # fcmp s7,s16
              0x54000080,   # b.eq done (+16)     scale 1: the game's dynamic resolution
              0x1e2020e8,   # fcmp s7,#0.0
              0x5400004d,   # b.le done (+8)      not set
              0x1e204206):  # fmov s6,s16         a fixed scale: no dynamic multiplier
        emit(w)
    emit(B(here(), 0xd5d84))
    fs_put(0xd5d80, [B(0xd5d80, start)], 'dynamic resolution only at render scale 1.0')

    # Live mid-game QoL mods (state +0x40 u32 qol_flags, +0x44 float glider_mult; zero = bit-exact vanilla).
    # All stubs use x16 as scratch (dead at every site) and preserve NZCV where needed (backpack Korok, Zonai despawn).
    ldr_qol = 0xB9404210                 # ldr w16, [x16, #0x40]
    tbz16 = lambda bit, insns: 0x36000010 | ((bit & 31) << 19) | ((insns & 0x3FFF) << 5)
    tbnz16 = lambda bit, insns: 0x37000010 | ((bit & 31) << 19) | ((insns & 0x3FFF) << 5)
    cbz_w = lambda rt, insns: 0x34000000 | ((insns & 0x7FFFF) << 5) | rt
    cbnz_w = lambda rt, insns: 0x35000000 | ((insns & 0x7FFFF) << 5) | rt

    def emit_cbz_w8_bypass(site, orig_hex, hide_tgt, bit, why):
        fs_site(site, orig_hex)
        st = here(); emit(ADRP(16, here(), FS_STATE_OFF))
        emit(ldr_qol)
        emit(tbnz16(bit, 3))             # bit on -> show (site + 4)
        emit(cbnz_w(8, 2))               # vanilla: w8 != 0 -> show (site + 4)
        emit(B(here(), hide_tgt))        # vanilla: w8 == 0 -> hide
        emit(B(here(), site + 4))        # show
        fs_put(site, [B(site, st)], why)

    def emit_bit_swap(site, orig_hex, orig_w, mod_w, bit, why):
        fs_site(site, orig_hex)
        st = here(); emit(ADRP(16, here(), FS_STATE_OFF))
        emit(ldr_qol)
        emit(tbz16(bit, 3))              # bit off -> original instruction (preserves NZCV!)
        emit(mod_w)
        emit(B(here(), site + 4))
        emit(orig_w)
        emit(B(here(), site + 4))
        fs_put(site, [B(site, st)], why)

    # 1. Korok Map (bits 0..1: 0=Off/vanilla, 1=Uncollected only, 2=All; respects map layer & zoom-in)
    # 1a. main+0x20fc7a4 (ldrb w8, [x20, #0x1d]): mode 2 (All) jumps straight to show (0x20fc85c)
    fs_site(0x20fc7a4, '88764039')
    st = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (ldr_qol,
              0x12000610,                # and w16, w16, #3
              0x51000A10,                # sub w16, w16, #2
              cbnz_w(16, 2)):            # != 2 -> original path
        emit(w)
    emit(B(here(), 0x20fc85c))           # mode 2 (All): show Korok
    emit(0x39407688)                     # ldrb w8, [x20, #0x1d] (original)
    emit(B(here(), 0x20fc7a8))
    fs_put(0x20fc7a4, [B(0x20fc7a4, st)], 'QoL: Korok map All mode')

    # 1b. main+0x20fc7fc (regular Koroks, cbnz w8, #0x20fc85c): mode 1 (Uncollected) inverts IsCollected check
    fs_site(0x20fc7fc, '08030035')
    st = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (ldr_qol,
              0x12000610,                # and w16, w16, #3
              0x51000610,                # sub w16, w16, #1
              cbnz_w(16, 3),             # != 1 -> vanilla (+3)
              cbnz_w(8, 4)):             # mode 1: collected (w8 != 0) -> hide (+4)
        emit(w)
    emit(B(here(), 0x20fc85c))           # mode 1: uncollected -> show
    emit(cbz_w(8, 2))                    # vanilla: w8 == 0 -> hide (+2)
    emit(B(here(), 0x20fc85c))           # vanilla: collected -> show
    emit(B(here(), 0x20fc800))           # hide (falls into b 0x20fc724)
    fs_put(0x20fc7fc, [B(0x20fc7fc, st)], 'QoL: Korok map Uncollected mode (regular Koroks)')

    # 1c. main+0x20fc858 (backpack Koroks, b.ne #0x20fc724): mode 1 inverts EQ/NE without touching NZCV!
    fs_site(0x20fc858, '61f6ff54')
    st = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (ldr_qol,
              0x12000610,                # and w16, w16, #3 (non-flag-setting)
              0x51000610,                # sub w16, w16, #1 (non-flag-setting)
              cbnz_w(16, 3),             # != 1 -> vanilla (+3)
              0x54000081):               # mode 1: b.ne +4 -> show (uncollected)
        emit(w)
    emit(B(here(), 0x20fc724))           # mode 1: EQ (collected) -> hide
    emit(0x54000040)                     # vanilla: b.eq +2 -> show (collected)
    emit(B(here(), 0x20fc724))           # vanilla: NE (uncollected) -> hide
    emit(B(here(), 0x20fc85c))           # show
    fs_put(0x20fc858, [B(0x20fc858, st)], 'QoL: Korok map Uncollected mode (backpack Koroks)')

    # 2. Show All Shrines & Lightroots (bit 2)
    emit_cbz_w8_bypass(0x20f6ff0, '48020034', 0x20f7038, 2, 'QoL: show all Shrines & Lightroots on map')

    # 3. Show All Caves, Wells & Chasms (bit 3) — main map icon check + companion zoom/layer check
    fs_site(0x73644c, '28030035')
    st = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    emit(ldr_qol)
    emit(tbz16(3, 2))                    # bit 3 off -> vanilla
    emit(B(here(), 0x736500))            # bit 3 on -> skip discovered + secondary flag, keep viewport & layer check
    emit(cbz_w(8, 2))                    # vanilla: w8 == 0 -> hide (0x736450)
    emit(B(here(), 0x7364b0))            # vanilla: w8 != 0 -> secondary check
    emit(B(here(), 0x736450))            # vanilla: hide
    fs_put(0x73644c, [B(0x73644c, st)], 'QoL: show all Caves, Wells & Chasms on map')
    emit_cbz_w8_bypass(0x20fa408, '08faff34', 0x20fa348, 3, 'QoL: show all Caves, Wells & Chasms (companion discovered)')
    emit_cbz_w8_bypass(0x20fa478, '88f6ff34', 0x20fa348, 3, 'QoL: show all Caves, Wells & Chasms (companion secondary)')

    # 4. Show All Dragon Tears (bit 4)
    emit_cbz_w8_bypass(0x20fd158, 'e8fbff34', 0x20fd0d4, 4, 'QoL: show all Dragon Tears on map')

    # 5. Show All Zonai Dispensers (bit 5)
    emit_cbz_w8_bypass(0x20fcce4, '88faff34', 0x20fcc34, 5, 'QoL: show all Zonai Dispensers on map')

    # 6. Disable Fog (bit 6): fmov s3, #1.0 -> fmov s3, wzr (0.0f)
    emit_bit_swap(0x67fcc4, '03102e1e', 0x1E2E1003, 0x1E2703E3, 6, 'QoL: disable fog')

    # 7. No Zonai Despawn (bit 7): fcsel s2, s2, s0, ne -> fmov s2, wzr (NZCV preserved on vanilla path)
    emit_bit_swap(0x1ccc718, '421c201e', 0x1E201C42, 0x1E2703E2, 7, 'QoL: no Zonai device despawn')

    # 8. Remove 21 Zonai Spawn Limit (bit 8): ldr w8, [x19, #0x10] -> mov w8, #1
    emit_bit_swap(0x1c0ba70, '681240b9', 0xB9401268, 0x52800028, 8, 'QoL: remove 21 Zonai device spawn limit')

    # 9. Paraglider Speed Boost (state +0x44 float glider_mult; <= 1.0f = vanilla)
    # Hook inside ExecutePlayerParasailGlide right before horizontal dir multiply; s1, s2, x16, NZCV are all dead here
    fs_site(0x23f9fc4, 'e10b462d')
    st = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (0xBD404601,                # ldr s1, [x16, #0x44]  glider_mult
              0x1E2E1002,                # fmov s2, #1.0
              0x1E222020,                # fcmp s1, s2
              0x5400004D,                # b.le skip (+2)        0.0 or 1.0: vanilla
              0x1E210800,                # fmul s0, s0, s1
              0x2D460BE1):               # skip: ldp s1, s2, [sp, #0x30] (original)
        emit(w)
    emit(B(here(), 0x23f9fc8))
    fs_put(0x23f9fc4, [B(0x23f9fc4, st)], 'QoL: paraglider horizontal speed multiplier (state +0x44)')

    # 10. Infinite Horse Stamina (bit 9): subs w8, w8, #1 -> subs w8, w8, #0 (keeps NZCV valid for b.lt)
    emit_bit_swap(0x233765c, '08050071', 0x71000508, 0x71000108, 9, 'QoL: infinite horse stamina')

    # 11. Unbreakable Shield for Shield Surfing (bit 10): ShouldShieldSurfTakeDamage returns 0 (like snow/sand)
    fs_site(0x1b7bb24, '08087fb9')
    st = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    emit(ldr_qol)
    emit(tbz16(10, 2))                   # bit 10 off -> vanilla
    emit(B(here(), 0x1b7bb84))           # bit 10 on -> mov w0, wzr; ret
    emit(0xB97F0808)                     # ldr w8, [x0, #0x3f08] (original)
    emit(B(here(), 0x1b7bb28))
    fs_put(0x1b7bb24, [B(0x1b7bb24, st)], 'QoL: unbreakable shield while shield surfing')

    # The sites below were checked against three 1.4.3 sources (Arch9SK7/MyNXCheats 277178B7DBA1B6D4.txt, its 1.4.2 file 5CB42B1CF25469FB.txt, and for the
    # durability sites aismor/kingdom-recomp recomp/patches-v143.txt and SuperSenad/Ultra-Instinct-Tears tools/lifter/patches.py); fs_site checks each original word.
    def cbz_target(site, word):          # where a cbz at site jumps (the icon is hidden there)
        imm = (word >> 5) & 0x7FFFF
        return site + ((imm - (1 << 19)) if imm & (1 << 18) else imm) * 4
    def le(word): return word.to_bytes(4, 'little').hex()
    bcond = lambda cond, insns: 0x54000000 | ((insns & 0x7FFFF) << 5) | cond

    # 12. Map icons (bits 11..18): each "is it known" check, ldrb w8,[x29,#..] then cbz w8 -> hide, shows the icon type while its bit is on. These only read
    # flags (no game data is written). Misko's treasure: the public 1.4.3 file repeats the Great Fairy address; 0x20fe904 is the next function of the same
    # shape, 0x648 after it as Misko's was 0x644 after the Great Fairy's in 1.4.2 (0x20f8a90, 0x20f90d4)
    for site, word, bit, what in ((0x736614, 0x340002C8, 11, 'Skyview Towers'), (0x20F9F9C, 0x340000E8, 13, 'unvisited places'),
                                  (0x20FE2BC, 0x34FFFBA8, 14, 'Great Fairies'), (0x20FE904, 0x34FFFBA8, 15, "Misko's treasure"),
                                  (0x20FEDD4, 0x34FFFBE8, 16, 'Bargainer Statues'), (0x20FDC68, 0x34FFFB48, 17, 'old maps'),
                                  (0x20F8068, 0x34000988, 18, 'the five temples')):
        emit_cbz_w8_bypass(site, le(word), cbz_target(site, word), bit, f'QoL: show all {what} on map')
    # Villages & Stables (bit 12): ldrb w8,[x29,#28] -> mov w8,#1 (its cbnz then goes the "known" way)
    emit_bit_swap(0x736ce0, le(0x394073A8), 0x394073A8, 0x52800028, 12, 'QoL: show all villages & stables on map')

    # 13. Temperature (bits 19..21), the public cheat's three sites, one switch each
    emit_bit_swap(0x72ae28, le(0x1A9F57E0), 0x1A9F57E0, 0x2A1F03E0, 19, 'QoL: no cold damage (below-limit check: cset w0,mi -> mov w0,wzr)')
    emit_bit_swap(0x72b124, le(0xBD400009), 0xBD400009, 0xBD400809, 20, 'QoL: no heat damage (above-limit check reads [x0,#8])')
    emit_bit_swap(0x324c14, le(0xB9400008), 0xB9400008, 0x52800068, 21, 'QoL: no fire damage (ldr w8,[x0] -> mov w8,#3)')

    # 14. Day length (ext +0x48 bits 0..2; day_mult float +0x4c): the clock's step this frame, ldr s9,[x19,#60] (2 x the frame's time, written at 0x68c0dc), x day_mult.
    # Multiplied rather than replaced (the public cheat's fmov s9,#1.0 assumes 30 fps). s16 is free: this function never touches v16..v31
    fs_site(0x68c15c, le(0xBD403E69))
    st = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (0xB9404A10,                # ldr w16, [x16, #0x48]  ext
              0x12000A10,                # and w16, w16, #7       day length
              cbz_w(16, 6)):             # Normal -> original
        emit(w)
    emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (0xBD404E10,                # ldr s16, [x16, #0x4c]  day_mult
              0xBD403E69,                # ldr s9, [x19, #60]     (original)
              0x1E300929):               # fmul s9, s9, s16
        emit(w)
    emit(B(here(), 0x68c160))
    emit(0xBD403E69)                     # ldr s9, [x19, #60]     (original)
    emit(B(here(), 0x68c160))
    fs_put(0x68c15c, [B(0x68c15c, st)], 'QoL: day length (the clock step x state +0x4c)')

    # 15. Weapon durability (ext +0x48 bits 4..6: 1 2x, 2 3x, 3 5x, 4 unbreakable). A weapon's, bow's or shield's durability is its actor's Life (the handle at
    # component +0x1830, the value at handle +8, as for every actor), and wear is damage queued for that actor like any other. Four sites:
    #   a) main+0x282870 copies each equipped item's Life (0x2829f4) and its fused part's (0x282e58) to the pouch ("Life" = murmur3 0x0355c603). The stubs there
    #      note the handle and the frame (+0x58) in a table (+0x100 the items by slot w28, +0x200 their fused parts; 16 bytes each), and for Unbreakable make the
    #      Life read its maximum, written back (the public cheat: Arch9SK7/MyNXCheats, also in aismor/kingdom-recomp and SuperSenad/Ultra-Instinct-Tears)
    #   b) main+0x44039c, add w9,w8,w9: the damage an actor takes this frame (the only place a Life goes down). For an actor whose handle is in the table and was
    #      noted in the last 64 frames, so for Link's equipped items only: none (Unbreakable), or one part in N (the rest stays in +0x50 for the next hits)
    #   c) main+0x21eca9c, msub w8,w10,w9,w8: the charges of a weapon that shoots (its own count, not the Life): none, or on one shot in N (count at +0x54)
    # Diagnostics the host logs when the pause menu opens (loader.c dm_qol_stats): +0x60 / +0x64 the copies seen at a), +0x68 actors matched at b), +0x6c the
    # wear they were to take, +0x70 the wear they took. x16, x17 are free at b) (the function only uses them after 0x440c30, written first); w8 is dead after it
    ADRP_STATE, B_BACK = 0xD4200020, 0xD4200040          # (brk #1, brk #2: placeholders in the tables below)
    def emit_stub(site, orig_word, words, why):
        fs_site(site, le(orig_word))
        st = here()
        for w in words: emit(ADRP(16, here(), FS_STATE_OFF) if w == ADRP_STATE else B(here(), site + 4) if w == B_BACK else w)
        fs_put(site, [B(site, st)], why)
    SYNC1 = (
        0xD4200020,   #  0 adrp x16, STATE
        0x91040201,   #  1 add x1, x16, #0x100
        0x8B3C5021,   #  2 add x1, x1, w28, uxtw #4
        0xF9000028,   #  3 str x8, [x1]
        0xB9405A10,   #  4 ldr w16, [x16, #0x58]
        0xB9000830,   #  5 str w16, [x1, #0x8]
        0xD4200020,   #  6 adrp x16, STATE
        0xB9406201,   #  7 ldr w1, [x16, #0x60]
        0x11000421,   #  8 add w1, w1, #0x1
        0xB9006201,   #  9 str w1, [x16, #0x60]
        0xB9404A10,   # 10 ldr w16, [x16, #0x48]
        0x53041A10,   # 11 ubfx w16, w16, #4, #3
        0x51001210,   # 12 sub w16, w16, #0x4
        0x35000090,   # 13 cbnz w16, +4
        0xB9401901,   # 14 ldr w1, [x8, #0x18]
        0xB9000901,   # 15 str w1, [x8, #0x8]
        0xD4200040,   # 16 b back
        0xB9400901,   # 17 ldr w1, [x8, #0x8]
        0xD4200040,   # 18 b back
    )
    SYNC2 = (
        0xD4200020,   #  0 adrp x16, STATE
        0x91080201,   #  1 add x1, x16, #0x200
        0x8B3C5021,   #  2 add x1, x1, w28, uxtw #4
        0xF9000028,   #  3 str x8, [x1]
        0xB9405A10,   #  4 ldr w16, [x16, #0x58]
        0xB9000830,   #  5 str w16, [x1, #0x8]
        0xD4200020,   #  6 adrp x16, STATE
        0xB9406601,   #  7 ldr w1, [x16, #0x64]
        0x11000421,   #  8 add w1, w1, #0x1
        0xB9006601,   #  9 str w1, [x16, #0x64]
        0xB9404A10,   # 10 ldr w16, [x16, #0x48]
        0x53041A10,   # 11 ubfx w16, w16, #4, #3
        0x51001210,   # 12 sub w16, w16, #0x4
        0x35000090,   # 13 cbnz w16, +4
        0xB9401901,   # 14 ldr w1, [x8, #0x18]
        0xB9000901,   # 15 str w1, [x8, #0x8]
        0xD4200040,   # 16 b back
        0xB9400901,   # 17 ldr w1, [x8, #0x8]
        0xD4200040,   # 18 b back
    )
    APPLY = (
        0x0B090109,   #  0 add w9, w8, w9
        0x340005E9,   #  1 cbz w9, +47
        0x37F805C9,   #  2 tbnz w9, #0x1f, +46
        0xD4200020,   #  3 adrp x16, STATE
        0xB9404A11,   #  4 ldr w17, [x16, #0x48]
        0x53041A31,   #  5 ubfx w17, w17, #4, #3
        0x34000551,   #  6 cbz w17, +42
        0xF94C1A68,   #  7 ldr x8, [x19, #0x1830]
        0xB4000508,   #  8 cbz x8, +40
        0xA9BF07E0,   #  9 stp x0, x1, [sp, #-0x10]!
        0xB9405A00,   # 10 ldr w0, [x16, #0x58]
        0x91040201,   # 11 add x1, x16, #0x100
        0xF9400030,   # 12 ldr x16, [x1]
        0xCA080210,   # 13 eor x16, x16, x8
        0xB50000B0,   # 14 cbnz x16, +5
        0xB9400830,   # 15 ldr w16, [x1, #0x8]
        0x4B100010,   # 16 sub w16, w0, w16
        0x53067E10,   # 17 lsr w16, w16, #6
        0x340000D0,   # 18 cbz w16, +6
        0x91004021,   # 19 add x1, x1, #0x10
        0x92402C30,   # 20 and x16, x1, #0xfff
        0xD10C0210,   # 21 sub x16, x16, #0x300
        0xB5FFFED0,   # 22 cbnz x16, +-10
        0x14000018,   # 23 b +24
        0x9274CC21,   # 24 and x1, x1, #0xfffffffffffff000
        0xB9406830,   # 25 ldr w16, [x1, #0x68]
        0x11000610,   # 26 add w16, w16, #0x1
        0xB9006830,   # 27 str w16, [x1, #0x68]
        0xB9406C30,   # 28 ldr w16, [x1, #0x6c]
        0x0B090210,   # 29 add w16, w16, w9
        0xB9006C30,   # 30 str w16, [x1, #0x6c]
        0x51001230,   # 31 sub w16, w17, #0x4
        0x34000170,   # 32 cbz w16, +11
        0x11000620,   # 33 add w0, w17, #0x1
        0x53017E30,   # 34 lsr w16, w17, #1
        0x0A110210,   # 35 and w16, w16, w17
        0x0B100000,   # 36 add w0, w0, w16
        0xB9405030,   # 37 ldr w16, [x1, #0x50]
        0x0B090210,   # 38 add w16, w16, w9
        0x1AC00A09,   # 39 udiv w9, w16, w0
        0x1B00C130,   # 40 msub w16, w9, w0, w16
        0xB9005030,   # 41 str w16, [x1, #0x50]
        0x14000002,   # 42 b +2
        0x2A1F03E9,   # 43 mov w9, wzr
        0xB9407030,   # 44 ldr w16, [x1, #0x70]
        0x0B090210,   # 45 add w16, w16, w9
        0xB9007030,   # 46 str w16, [x1, #0x70]
        0xA8C107E0,   # 47 ldp x0, x1, [sp], #0x10
        0xD4200040,   # 48 b back
    )
    SHOTS = (
        0xD4200020,   #  0 adrp x16, STATE
        0xB9404A10,   #  1 ldr w16, [x16, #0x48]
        0x53041A10,   #  2 ubfx w16, w16, #4, #3
        0x34000210,   #  3 cbz w16, +16
        0x7100121F,   #  4 cmp w16, #0x4
        0x540001E2,   #  5 b.hs +15
        0x1B097D4A,   #  6 mul w10, w10, w9
        0x11000609,   #  7 add w9, w16, #0x1
        0x71000E1F,   #  8 cmp w16, #0x3
        0x1A891529,   #  9 cinc w9, w9, eq
        0xD4200020,   # 10 adrp x16, STATE
        0xB9405614,   # 11 ldr w20, [x16, #0x54]
        0x11000694,   # 12 add w20, w20, #0x1
        0x6B09029F,   # 13 cmp w20, w9
        0x1A9423F4,   # 14 csel w20, wzr, w20, hs
        0xB9005614,   # 15 str w20, [x16, #0x54]
        0x35000094,   # 16 cbnz w20, +4
        0x4B0A0108,   # 17 sub w8, w8, w10
        0xD4200040,   # 18 b back
        0x1B09A148,   # 19 msub w8, w10, w9, w8
        0xD4200040,   # 20 b back
    )
    emit_stub(0x2829f4, 0xB9400901, SYNC1, 'QoL: weapon durability, the equipped items (their Life handles noted; unbreakable: Life = its maximum)')
    emit_stub(0x282e58, 0xB9400901, SYNC2, 'QoL: weapon durability, the equipped items\' fused parts')
    emit_stub(0x44039c, 0x0B090109, APPLY, 'QoL: weapon durability, the wear an equipped item takes (2x / 3x / 5x / unbreakable)')
    emit_stub(0x21eca9c, 0x1B09A148, SHOTS, 'QoL: weapon durability, the charges of a weapon that shoots')
    ctx.qol_mods = 1

FRAME_STEP = {'277178b7dba1b6d4949a84778d4abc58': frame_step}
