# jpeg - a JPEG decoder in PlainPy: baseline pictures (sequential, Huffman
# coded, 8 bits a sample) - what map tile servers send, and most cameras and
# programs write. Works compiled (every target) and in the interpreter.
#
#   w, h, pixels = jpeg.decode(data)       # data: the file's bytes
#   w, h, pixels = jpeg.load("/hd0/1/photo.jpg")
#
# pixels is a sys.buffer of w*h*4 bytes, B G R A per pixel (A = 255), rows
# top to bottom - png.decode's layout, the one KolibriOS draws with fn 65 at
# 32 bpp and kgfx.Image keeps. Gray and YCbCr pictures, any sampling of the
# colors (4:2:0, 4:2:2, 4:4:4 ...), restart intervals, several scans. Colors
# kept at half the resolution are spread over the pixels as libjpeg does by
# default: each pixel's a blend of the four nearest samples (9:3:3:1).
# Progressive, arithmetic-coded, 12-bit and CMYK pictures raise ValueError,
# as do broken ones.
#
# The inverse DCT is libjpeg's accurate integer one (jidctint.c: 13-bit
# constants, two passes).
import sys

# where the n-th coefficient of a block's zigzag lies in the block (row * 8 + column)
ZIGZAG = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5,
          12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
          35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51,
          58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63]

# the inverse DCT's constants: c * 2^13 (jidctint.c's FIX_...)
F0_298 = 2446
F0_390 = 3196
F0_541 = 4433
F0_765 = 6270
F0_899 = 7373
F1_175 = 9633
F1_501 = 12299
F1_847 = 15137
F1_961 = 16069
F2_053 = 16819
F2_562 = 20995
F3_072 = 25172
CONST_BITS = 13
PASS1_BITS = 2

class Huffman:
    """A Huffman table: the codes up to 8 bits long looked up at once (by the
    next 8 bits), the longer ones by their length (the standard's MAXCODE,
    VALPTR, MINCODE)."""

    def __init__(self, counts: list[int], symbols: list[int]):
        self.symbols = symbols
        self.look_len: list[int] = [0] * 256
        self.look_sym: list[int] = [0] * 256
        self.maxcode: list[int] = [-1] * 17
        self.valptr: list[int] = [0] * 17
        self.mincode: list[int] = [0] * 17
        code = 0
        k = 0
        for n in range(1, 17):
            self.valptr[n] = k
            self.mincode[n] = code
            for i in range(counts[n - 1]):
                if n <= 8:
                    base = code << (8 - n)
                    for j in range(1 << (8 - n)):
                        self.look_len[base + j] = n
                        self.look_sym[base + j] = symbols[k]
                code += 1
                k += 1
            if counts[n - 1] > 0:
                self.maxcode[n] = code - 1
            code = code << 1

class Bits:
    """The entropy-coded bytes read a bit at a time, MSB first: a 0 byte
    after 0xFF dropped (stuffing); at a marker only zeros come (the marker's
    business is the decoder's: a restart, the end)."""

    def __init__(self, data: bytes, pos: int):
        self.data = data
        self.pos = pos
        self.acc = 0                         # the bits read ahead, n of them
        self.n = 0
        self.at_marker = False

    def fill(self) -> None:
        """At least 17 bits ahead."""
        data = self.data
        while self.n <= 16:
            b = 0
            if not self.at_marker and self.pos < len(data):
                b = data[self.pos]
                if b == 0xFF:
                    nxt = data[self.pos + 1] if self.pos + 1 < len(data) else 0xD9
                    if nxt == 0:
                        self.pos += 2
                    else:
                        self.at_marker = True
                        b = 0
                else:
                    self.pos += 1
            self.acc = (self.acc << 8) | b
            self.n += 8

    def get(self, count: int) -> int:
        """The next count bits as a number."""
        if count == 0:
            return 0
        if self.n < count:
            self.fill()
        self.n -= count
        v = self.acc >> self.n
        self.acc &= (1 << self.n) - 1
        return v

    def decode(self, h: Huffman) -> int:
        """The next symbol of table h."""
        if self.n < 16:
            self.fill()
        p = self.acc >> (self.n - 8)
        n = h.look_len[p]
        if n > 0:
            self.n -= n
            self.acc &= (1 << self.n) - 1
            return h.look_sym[p]
        for n in range(9, 17):
            code = self.acc >> (self.n - n)
            if code <= h.maxcode[n]:
                self.n -= n
                self.acc &= (1 << self.n) - 1
                return h.symbols[h.valptr[n] + code - h.mincode[n]]
        raise ValueError("jpeg: a bad Huffman code")

    def extend(self, s: int) -> int:
        """A value of s bits (the standard's RECEIVE and EXTEND)."""
        v = self.get(s)
        if s > 0 and v < (1 << (s - 1)):
            v -= (1 << s) - 1
        return v

    def restart(self) -> None:
        """Past a restart marker (RSTn): the bits read ahead are dropped."""
        self.acc = 0
        self.n = 0
        if self.at_marker or (self.pos + 1 < len(self.data) and self.data[self.pos] == 0xFF):
            m = self.data[self.pos + 1] if self.pos + 1 < len(self.data) else 0
            if 0xD0 <= m <= 0xD7:
                self.pos += 2
        self.at_marker = False

class Component:
    def __init__(self, ident: int, hs: int, vs: int, tq: int):
        self.ident = ident
        self.hs = hs                         # its sampling: blocks across and down in an MCU
        self.vs = vs
        self.tq = tq                         # its quantization table
        self.bw = 0                          # its blocks across and down (whole MCUs)
        self.bh = 0
        self.width = 0                       # its plane: bw * 8 samples a row
        self.plane: list[int] = []
        self.dc = 0                          # the DC of the last block (predicted from)
        self.td = 0                          # its Huffman tables in the scan
        self.ta = 0

def _u16(data: bytes, pos: int) -> int:
    return (data[pos] << 8) | data[pos + 1]

def _clamp(v: int) -> int:
    if v < 0:
        return 0
    if v > 255:
        return 255
    return v

def idct(blk: list[int], ws: list[int], plane: list[int], at: int, stride: int) -> None:
    """The 64 dequantized coefficients of blk (row by row) as 8 x 8 samples
    into plane at at (stride: its row length); ws is room for the first pass."""
    for c in range(8):                       # pass 1: the columns
        i0 = blk[c]
        i1 = blk[8 + c]
        i2 = blk[16 + c]
        i3 = blk[24 + c]
        i4 = blk[32 + c]
        i5 = blk[40 + c]
        i6 = blk[48 + c]
        i7 = blk[56 + c]
        if i1 == 0 and i2 == 0 and i3 == 0 and i4 == 0 and i5 == 0 and i6 == 0 and i7 == 0:
            dc = i0 << PASS1_BITS
            for r in range(8):
                ws[r * 8 + c] = dc
            continue
        z1 = (i2 + i6) * F0_541
        t2 = z1 - i6 * F1_847
        t3 = z1 + i2 * F0_765
        t0 = (i0 + i4) << CONST_BITS
        t1 = (i0 - i4) << CONST_BITS
        t10 = t0 + t3
        t13 = t0 - t3
        t11 = t1 + t2
        t12 = t1 - t2
        z1 = i7 + i1
        z2 = i5 + i3
        z3 = i7 + i3
        z4 = i5 + i1
        z5 = (z3 + z4) * F1_175
        t0 = i7 * F0_298
        t1 = i5 * F2_053
        t2 = i3 * F3_072
        t3 = i1 * F1_501
        z1 = -z1 * F0_899
        z2 = -z2 * F2_562
        z3 = -z3 * F1_961 + z5
        z4 = -z4 * F0_390 + z5
        t0 += z1 + z3
        t1 += z2 + z4
        t2 += z2 + z3
        t3 += z1 + z4
        half = 1 << (CONST_BITS - PASS1_BITS - 1)
        sh = CONST_BITS - PASS1_BITS
        ws[c] = (t10 + t3 + half) >> sh
        ws[56 + c] = (t10 - t3 + half) >> sh
        ws[8 + c] = (t11 + t2 + half) >> sh
        ws[48 + c] = (t11 - t2 + half) >> sh
        ws[16 + c] = (t12 + t1 + half) >> sh
        ws[40 + c] = (t12 - t1 + half) >> sh
        ws[24 + c] = (t13 + t0 + half) >> sh
        ws[32 + c] = (t13 - t0 + half) >> sh
    sh = CONST_BITS + PASS1_BITS + 3
    half = 1 << (sh - 1)
    for r in range(8):                       # pass 2: the rows, to samples
        o = r * 8
        i0 = ws[o]
        i1 = ws[o + 1]
        i2 = ws[o + 2]
        i3 = ws[o + 3]
        i4 = ws[o + 4]
        i5 = ws[o + 5]
        i6 = ws[o + 6]
        i7 = ws[o + 7]
        p = at + r * stride
        if i1 == 0 and i2 == 0 and i3 == 0 and i4 == 0 and i5 == 0 and i6 == 0 and i7 == 0:
            v = _clamp(((i0 + (1 << (PASS1_BITS + 2))) >> (PASS1_BITS + 3)) + 128)
            for c in range(8):
                plane[p + c] = v
            continue
        z1 = (i2 + i6) * F0_541
        t2 = z1 - i6 * F1_847
        t3 = z1 + i2 * F0_765
        t0 = (i0 + i4) << CONST_BITS
        t1 = (i0 - i4) << CONST_BITS
        t10 = t0 + t3
        t13 = t0 - t3
        t11 = t1 + t2
        t12 = t1 - t2
        z1 = i7 + i1
        z2 = i5 + i3
        z3 = i7 + i3
        z4 = i5 + i1
        z5 = (z3 + z4) * F1_175
        t0 = i7 * F0_298
        t1 = i5 * F2_053
        t2 = i3 * F3_072
        t3 = i1 * F1_501
        z1 = -z1 * F0_899
        z2 = -z2 * F2_562
        z3 = -z3 * F1_961 + z5
        z4 = -z4 * F0_390 + z5
        t0 += z1 + z3
        t1 += z2 + z4
        t2 += z2 + z3
        t3 += z1 + z4
        plane[p] = _clamp(((t10 + t3 + half) >> sh) + 128)
        plane[p + 7] = _clamp(((t10 - t3 + half) >> sh) + 128)
        plane[p + 1] = _clamp(((t11 + t2 + half) >> sh) + 128)
        plane[p + 6] = _clamp(((t11 - t2 + half) >> sh) + 128)
        plane[p + 2] = _clamp(((t12 + t1 + half) >> sh) + 128)
        plane[p + 5] = _clamp(((t12 - t1 + half) >> sh) + 128)
        plane[p + 3] = _clamp(((t13 + t0 + half) >> sh) + 128)
        plane[p + 4] = _clamp(((t13 - t0 + half) >> sh) + 128)

class Decoder:
    def __init__(self, data: bytes):
        self.data = data
        self.qt: list[list[int]] = [[1] * 64, [1] * 64, [1] * 64, [1] * 64]   # in zigzag order
        self.dc_tables: list[Huffman] = []
        self.ac_tables: list[Huffman] = []
        for i in range(4):
            self.dc_tables.append(Huffman([0] * 16, []))
            self.ac_tables.append(Huffman([0] * 16, []))
        self.comps: list[Component] = []
        self.width = 0
        self.height = 0
        self.hmax = 1
        self.vmax = 1
        self.mcux = 0
        self.mcuy = 0
        self.restart = 0                     # MCUs between restart markers (0: none)
        self.blk: list[int] = [0] * 64
        self.ws: list[int] = [0] * 64

    def run(self) -> tuple[int, int, buffer]:
        data = self.data
        if len(data) < 4 or data[0] != 0xFF or data[1] != 0xD8:
            raise ValueError("jpeg: not a JPEG file")
        pos = 2
        while True:
            while pos < len(data) and data[pos] != 0xFF:      # (bytes between segments: skipped)
                pos += 1
            while pos < len(data) and data[pos] == 0xFF:      # (fill bytes)
                pos += 1
            if pos + 2 >= len(data):
                break
            m = data[pos]
            pos += 1
            if m == 0xD9:
                break
            if 0xD0 <= m <= 0xD7 or m == 0x01:
                continue
            n = _u16(data, pos)
            body = pos + 2
            end = pos + n
            if end > len(data):
                raise ValueError("jpeg: cut short")
            if m == 0xDB:
                self.quantization(body, end)
            elif m == 0xC4:
                self.huffman(body, end)
            elif m == 0xC0 or m == 0xC1:
                self.frame(body)
            elif m == 0xDD:
                self.restart = _u16(data, body)
            elif m == 0xDA:
                end = self.scan(body)
            elif 0xC2 <= m <= 0xCF and m != 0xC4 and m != 0xC8 and m != 0xCC:
                raise ValueError("jpeg: not a baseline picture (SOF" + str(m - 0xC0) + ")")
            pos = end
        if len(self.comps) == 0:
            raise ValueError("jpeg: no picture")
        return (self.width, self.height, self.pixels())

    def quantization(self, pos: int, end: int) -> None:
        data = self.data
        while pos < end:
            pq = data[pos] >> 4
            tq = data[pos] & 15
            pos += 1
            q: list[int] = []
            for i in range(64):
                if pq == 0:
                    q.append(data[pos])
                    pos += 1
                else:
                    q.append(_u16(data, pos))
                    pos += 2
            self.qt[tq & 3] = q

    def huffman(self, pos: int, end: int) -> None:
        data = self.data
        while pos < end:
            tc = data[pos] >> 4
            th = data[pos] & 3
            pos += 1
            counts: list[int] = []
            total = 0
            for i in range(16):
                counts.append(data[pos + i])
                total += data[pos + i]
            pos += 16
            symbols: list[int] = []
            for i in range(total):
                symbols.append(data[pos + i])
            pos += total
            if tc == 0:
                self.dc_tables[th] = Huffman(counts, symbols)
            else:
                self.ac_tables[th] = Huffman(counts, symbols)

    def frame(self, pos: int) -> None:
        data = self.data
        if data[pos] != 8:
            raise ValueError("jpeg: " + str(data[pos]) + "-bit samples")
        self.height = _u16(data, pos + 1)
        self.width = _u16(data, pos + 3)
        n = data[pos + 5]
        if self.width == 0 or self.height == 0:
            raise ValueError("jpeg: no size")
        if n != 1 and n != 3:
            raise ValueError("jpeg: " + str(n) + " color components")
        p = pos + 6
        for i in range(n):
            hs = data[p + 1] >> 4
            vs = data[p + 1] & 15
            if hs < 1 or hs > 4 or vs < 1 or vs > 4:
                raise ValueError("jpeg: a bad sampling")
            self.comps.append(Component(data[p], hs, vs, data[p + 2] & 3))
            p += 3
        for c in self.comps:
            self.hmax = max(self.hmax, c.hs)
            self.vmax = max(self.vmax, c.vs)
        self.mcux = (self.width + 8 * self.hmax - 1) // (8 * self.hmax)
        self.mcuy = (self.height + 8 * self.vmax - 1) // (8 * self.vmax)
        for c in self.comps:
            c.bw = self.mcux * c.hs
            c.bh = self.mcuy * c.vs
            c.width = c.bw * 8
            c.plane = [0] * (c.width * c.bh * 8)

    def scan(self, pos: int) -> int:
        """Decode a scan (its header at pos); where the bytes after it start."""
        data = self.data
        n = data[pos]
        scomps: list[Component] = []
        p = pos + 1
        for i in range(n):
            found = False
            for c in self.comps:
                if c.ident == data[p]:
                    c.td = data[p + 1] >> 4
                    c.ta = data[p + 1] & 15
                    scomps.append(c)
                    found = True
            if not found:
                raise ValueError("jpeg: a scan of an unknown component")
            p += 2
        if data[p] != 0 or data[p + 1] != 63:
            raise ValueError("jpeg: not a baseline scan")
        bits = Bits(data, p + 3)
        for c in scomps:
            c.dc = 0
        if n == 1:                           # one component: its blocks one by one
            c = scomps[0]
            bw = (((self.width * c.hs + self.hmax - 1) // self.hmax) + 7) // 8
            bh = (((self.height * c.vs + self.vmax - 1) // self.vmax) + 7) // 8
            count = 0
            for by in range(bh):
                for bx in range(bw):
                    if self.restart > 0 and count > 0 and count % self.restart == 0:
                        bits.restart()
                        c.dc = 0
                    self.block(bits, c, by * 8 * c.width + bx * 8)
                    count += 1
        else:
            count = 0
            for my in range(self.mcuy):
                for mx in range(self.mcux):
                    if self.restart > 0 and count > 0 and count % self.restart == 0:
                        bits.restart()
                        for c in scomps:
                            c.dc = 0
                    for c in scomps:
                        for v in range(c.vs):
                            for h in range(c.hs):
                                self.block(bits, c, ((my * c.vs + v) * 8) * c.width + (mx * c.hs + h) * 8)
                    count += 1
        q = bits.pos                         # (what comes after the scan: the next marker)
        while q + 1 < len(data) and not (data[q] == 0xFF and data[q + 1] != 0 and not (0xD0 <= data[q + 1] <= 0xD7)):
            q += 1
        return q

    def block(self, bits: Bits, c: Component, at: int) -> None:
        """One 8 x 8 block of component c, its samples into the plane at at."""
        blk = self.blk
        for i in range(64):
            blk[i] = 0
        q = self.qt[c.tq]
        t = bits.decode(self.dc_tables[c.td])
        c.dc += bits.extend(t)
        blk[0] = c.dc * q[0]
        ac = self.ac_tables[c.ta]
        k = 1
        while k < 64:
            rs = bits.decode(ac)
            s = rs & 15
            r = rs >> 4
            if s == 0:
                if r != 15:
                    break                    # (end of block)
                k += 16
                continue
            k += r
            if k > 63:
                raise ValueError("jpeg: a bad block")
            blk[ZIGZAG[k]] = bits.extend(s) * q[k]
            k += 1
        idct(blk, self.ws, c.plane, at, c.width)

    def full(self, c: Component) -> list[int]:
        """Component c at the picture's resolution (w * h samples): a plane of
        half the resolution across or down is blended (each pixel 3/4 its own
        sample, 1/4 the nearest other - both ways: 9:3:3:1), other ones taken
        as they are."""
        w = self.width
        h = self.height
        out: list[int] = [0] * (w * h)
        if self.hmax % c.hs != 0 or self.vmax % c.vs != 0:
            for j in range(h):
                row = (j * c.vs // self.vmax) * c.width
                for i in range(w):
                    out[j * w + i] = c.plane[row + i * c.hs // self.hmax]
            return out
        fx = self.hmax // c.hs
        fy = self.vmax // c.vs
        cw = (w * c.hs + self.hmax - 1) // self.hmax              # the samples the picture has (the rest: padding)
        ch = (h * c.vs + self.vmax - 1) // self.vmax
        p = c.plane
        for j in range(h):
            cy = j // fy
            ny = cy
            if fy == 2:
                ny = max(0, cy - 1) if j % 2 == 0 else min(ch - 1, cy + 1)
            r0 = cy * c.width
            r1 = ny * c.width
            o = j * w
            for i in range(w):
                cx = i // fx
                if fx == 2:
                    nx = max(0, cx - 1) if i % 2 == 0 else min(cw - 1, cx + 1)
                    if fy == 2:
                        out[o + i] = (9 * p[r0 + cx] + 3 * p[r0 + nx] + 3 * p[r1 + cx] + p[r1 + nx] + 8) >> 4
                    else:
                        out[o + i] = (3 * p[r0 + cx] + p[r0 + nx] + 2) >> 2
                elif fy == 2:
                    out[o + i] = (3 * p[r0 + cx] + p[r1 + cx] + 2) >> 2
                else:
                    out[o + i] = p[r0 + cx]
        return out

    def plane(self, c: Component) -> tuple[list[int], int]:
        """A component's samples at the picture's resolution, and their row length."""
        if c.hs == self.hmax and c.vs == self.vmax:
            return (c.plane, c.width)
        return (self.full(c), self.width)

    def pixels(self) -> buffer:
        """The planes as B G R A pixels."""
        w = self.width
        h = self.height
        out = sys.buffer(w * h * 4)
        yp = self.plane(self.comps[0])
        ys = yp[0]
        if len(self.comps) == 1:
            for j in range(h):
                row = j * yp[1]
                p = j * w * 4
                for i in range(w):
                    v = ys[row + i]
                    sys.poke(out, p, v | (v << 8) | (v << 16) | -0x1000000, 4)
                    p += 4
            return out
        bp = self.plane(self.comps[1])
        rp = self.plane(self.comps[2])
        bs = bp[0]
        rs = rp[0]
        for j in range(h):
            yrow = j * yp[1]
            brow = j * bp[1]
            rrow = j * rp[1]
            p = j * w * 4
            for i in range(w):
                lum = ys[yrow + i]
                u = bs[brow + i] - 128
                v = rs[rrow + i] - 128
                r = _clamp(lum + ((91881 * v + 32768) >> 16))
                g = _clamp(lum + ((-22554 * u - 46802 * v + 32768) >> 16))
                b = _clamp(lum + ((116130 * u + 32768) >> 16))
                sys.poke(out, p, b | (g << 8) | (r << 16) | -0x1000000, 4)
                p += 4
        return out

def decode(data: bytes) -> tuple[int, int, buffer]:
    """A JPEG file's bytes: (width, height, B G R A pixels)."""
    return Decoder(data).run()

def load(path: str) -> tuple[int, int, buffer]:
    f = open(path, "rb")
    data = f.read()
    f.close()
    return decode(data)
