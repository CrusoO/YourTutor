/**
 * Exact rational numbers on BigInt. No floats anywhere. Pure: no network, no storage, no console.
 * (BigInt literals such as 1n need an ES2020 target; this app compiles to ES2017, so constants are made with BigInt().)
 */

export const B0 = BigInt(0);
export const B1 = BigInt(1);
export const B2 = BigInt(2);
export const B10 = BigInt(10);

export function babs(a: bigint): bigint {
  return a < B0 ? -a : a;
}

export function bgcd(a: bigint, b: bigint): bigint {
  let x = babs(a);
  let y = babs(b);
  while (y !== B0) {
    const t = x % y;
    x = y;
    y = t;
  }
  return x;
}

/** floor(sqrt(n)) for n >= 0, by Newton's method on BigInt. */
export function isqrt(n: bigint): bigint {
  if (n < B0) throw new RangeError("isqrt of a negative number");
  if (n < B2) return n;
  let x = B1 << BigInt(Math.ceil(n.toString(2).length / 2));
  for (;;) {
    const y = (x + n / x) >> B1;
    if (y >= x) return x;
    x = y;
  }
}

/** base ** e for e >= 0, square-and-multiply. */
export function bpow(base: bigint, e: number): bigint {
  if (!Number.isInteger(e) || e < 0) throw new RangeError("bpow needs a non-negative integer");
  let result = B1;
  let b = base;
  let k = e;
  while (k > 0) {
    if (k % 2 === 1) result *= b;
    k = Math.floor(k / 2);
    if (k > 0) b *= b;
  }
  return result;
}

const INT_RE = /^[+-]?\d+$/;
const DEC_RE = /^([+-]?)(\d*)\.(\d+)$/;
const RATIO_RE = /^([+-]?\d+)\s*\/\s*(\d+)$/;

export class Frac {
  readonly n: bigint;
  readonly d: bigint;

  private constructor(n: bigint, d: bigint) {
    this.n = n;
    this.d = d;
  }

  /** Normalised: gcd 1, positive denominator. Throws RangeError on a zero denominator. */
  static of(n: bigint | number, d: bigint | number = B1): Frac {
    let nn = typeof n === "number" ? BigInt(n) : n;
    let dd = typeof d === "number" ? BigInt(d) : d;
    if (dd === B0) throw new RangeError("zero denominator");
    if (dd < B0) {
      nn = -nn;
      dd = -dd;
    }
    const g = bgcd(nn, dd);
    if (g > B1) {
      nn /= g;
      dd /= g;
    }
    return new Frac(nn, dd);
  }

  /** "3", "-3/4", "0.25", "-.5". Returns null for anything else (never throws). */
  static parse(text: string): Frac | null {
    const s = text.trim();
    if (s.length === 0 || s.length > 64) return null;
    if (INT_RE.test(s)) return Frac.of(BigInt(s.replace(/^\+/, "")));
    const m = RATIO_RE.exec(s);
    if (m) {
      const den = BigInt(m[2]);
      return den === B0 ? null : Frac.of(BigInt(m[1].replace(/^\+/, "")), den);
    }
    const dm = DEC_RE.exec(s);
    if (dm) {
      const digits = dm[3];
      const num = BigInt((dm[2] || "0") + digits);
      return Frac.of(dm[1] === "-" ? -num : num, bpow(B10, digits.length));
    }
    return null;
  }

  static readonly ZERO: Frac = Frac.of(0);
  static readonly ONE: Frac = Frac.of(1);

  add(o: Frac): Frac {
    return Frac.of(this.n * o.d + o.n * this.d, this.d * o.d);
  }
  sub(o: Frac): Frac {
    return Frac.of(this.n * o.d - o.n * this.d, this.d * o.d);
  }
  mul(o: Frac): Frac {
    return Frac.of(this.n * o.n, this.d * o.d);
  }
  div(o: Frac): Frac {
    if (o.n === B0) throw new RangeError("division by zero");
    return Frac.of(this.n * o.d, this.d * o.n);
  }
  neg(): Frac {
    return new Frac(-this.n, this.d);
  }
  inv(): Frac {
    return Frac.ONE.div(this);
  }
  /** Integer power; a negative exponent inverts. Throws on 0 ** negative. */
  pow(e: number): Frac {
    if (!Number.isInteger(e)) throw new RangeError("integer exponent only");
    if (e >= 0) return Frac.of(bpow(this.n, e), bpow(this.d, e));
    return this.inv().pow(-e);
  }
  cmp(o: Frac): number {
    const l = this.n * o.d;
    const r = o.n * this.d;
    return l < r ? -1 : l > r ? 1 : 0;
  }
  eq(o: Frac): boolean {
    return this.n === o.n && this.d === o.d;
  }
  get sign(): number {
    return this.n < B0 ? -1 : this.n > B0 ? 1 : 0;
  }
  isZero(): boolean {
    return this.n === B0;
  }
  isInt(): boolean {
    return this.d === B1;
  }
  abs(): Frac {
    return this.n < B0 ? this.neg() : this;
  }
  /** Exact square root when this is a perfect square of a rational, else null. */
  sqrt(): Frac | null {
    if (this.n < B0) return null;
    const a = isqrt(this.n);
    const b = isqrt(this.d);
    return a * a === this.n && b * b === this.d ? Frac.of(a, b) : null;
  }
  /** Canonical text: "5", "-3/4". Never a decimal. */
  toString(): string {
    return this.d === B1 ? this.n.toString() : `${this.n}/${this.d}`;
  }
}

export function fracCmp(a: Frac, b: Frac): number {
  return a.cmp(b);
}

/** Sort ascending and drop duplicates. */
export function uniqueSorted(values: Frac[]): Frac[] {
  const sorted = [...values].sort(fracCmp);
  return sorted.filter((v, i) => i === 0 || !v.eq(sorted[i - 1]));
}
