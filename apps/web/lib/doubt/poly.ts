import { B0, B1, Frac, bgcd } from "./frac";

/** Polynomial in one unknown with exact coefficients, lowest degree first, trailing zeros trimmed. */
export class Poly {
  readonly c: readonly Frac[];

  constructor(coeffs: readonly Frac[]) {
    const out = [...coeffs];
    while (out.length > 0 && out[out.length - 1].isZero()) out.pop();
    this.c = out;
  }

  static constant(v: Frac): Poly {
    return new Poly([v]);
  }
  static x(): Poly {
    return new Poly([Frac.ZERO, Frac.ONE]);
  }
  static parseCoeffs(strings: readonly string[]): Poly | null {
    const out: Frac[] = [];
    for (const s of strings) {
      const f = Frac.parse(s);
      if (!f) return null;
      out.push(f);
    }
    return new Poly(out);
  }

  /** -1 for the zero polynomial. */
  get degree(): number {
    return this.c.length - 1;
  }
  isZero(): boolean {
    return this.c.length === 0;
  }
  isConstant(): boolean {
    return this.c.length <= 1;
  }
  coeff(i: number): Frac {
    return this.c[i] ?? Frac.ZERO;
  }
  get lead(): Frac {
    return this.c.length ? this.c[this.c.length - 1] : Frac.ZERO;
  }

  add(o: Poly): Poly {
    const n = Math.max(this.c.length, o.c.length);
    const out: Frac[] = [];
    for (let i = 0; i < n; i++) out.push(this.coeff(i).add(o.coeff(i)));
    return new Poly(out);
  }
  neg(): Poly {
    return new Poly(this.c.map((v) => v.neg()));
  }
  sub(o: Poly): Poly {
    return this.add(o.neg());
  }
  scale(k: Frac): Poly {
    return new Poly(this.c.map((v) => v.mul(k)));
  }
  mul(o: Poly): Poly {
    if (this.isZero() || o.isZero()) return new Poly([]);
    const out: Frac[] = Array.from({ length: this.c.length + o.c.length - 1 }, () => Frac.ZERO);
    for (let i = 0; i < this.c.length; i++) {
      for (let j = 0; j < o.c.length; j++) out[i + j] = out[i + j].add(this.c[i].mul(o.c[j]));
    }
    return new Poly(out);
  }
  /** Non-negative integer power. */
  pow(e: number): Poly {
    if (!Number.isInteger(e) || e < 0) throw new RangeError("non-negative integer power only");
    let result = Poly.constant(Frac.ONE);
    let base: Poly = this;
    let k = e;
    while (k > 0) {
      if (k % 2 === 1) result = result.mul(base);
      k = Math.floor(k / 2);
      if (k > 0) base = base.mul(base);
    }
    return result;
  }
  /** Horner evaluation, exact. */
  at(x: Frac): Frac {
    let acc = Frac.ZERO;
    for (let i = this.c.length - 1; i >= 0; i--) acc = acc.mul(x).add(this.c[i]);
    return acc;
  }
  equals(o: Poly): boolean {
    return this.c.length === o.c.length && this.c.every((v, i) => v.eq(o.c[i]));
  }
  /** True when this = k * o for some non-zero rational k (both non-zero). */
  isMultipleOf(o: Poly): boolean {
    if (this.isZero() || o.isZero() || this.c.length !== o.c.length) return false;
    return this.equals(o.scale(this.lead.div(o.lead)));
  }
  /** Divide by (x - r): the quotient when r is an exact root, else null. */
  divideByRoot(r: Frac): Poly | null {
    const n = this.c.length;
    if (n < 2) return null;
    const q: Frac[] = Array.from({ length: n - 1 }, () => Frac.ZERO);
    let carry = Frac.ZERO;
    for (let i = n - 1; i >= 1; i--) {
      carry = this.c[i].add(carry.mul(r));
      q[i - 1] = carry;
    }
    const rem = this.c[0].add(carry.mul(r));
    return rem.isZero() ? new Poly(q) : null;
  }
  /** Same polynomial scaled to integer coefficients with gcd 1 (sign of the scale is positive). */
  toIntegers(): bigint[] {
    if (this.isZero()) return [];
    let lcm = B1;
    for (const v of this.c) lcm = (lcm / bgcd(lcm, v.d)) * v.d;
    const ints = this.c.map((v) => (v.n * lcm) / v.d);
    let g = B0;
    for (const v of ints) g = bgcd(g, v);
    return ints.map((v) => v / (g === B0 ? B1 : g));
  }
  toStrings(): string[] {
    return this.c.map((v) => v.toString());
  }
  /** Display like "2x^2 - 3x + 1" in the given unknown letter. */
  show(v = "x"): string {
    if (this.isZero()) return "0";
    const parts: string[] = [];
    for (let i = this.c.length - 1; i >= 0; i--) {
      const co = this.c[i];
      if (co.isZero()) continue;
      const neg = co.sign < 0;
      const abs = co.abs();
      const absText = abs.toString();
      let body: string;
      if (i === 0) body = absText;
      else {
        const mag = abs.eq(Frac.ONE) ? "" : abs.isInt() ? absText : `(${absText})`;
        body = `${mag}${v}${i > 1 ? `^${i}` : ""}`;
      }
      if (parts.length === 0) parts.push(neg ? `-${body}` : body);
      else parts.push(neg ? `- ${body}` : `+ ${body}`);
    }
    return parts.join(" ");
  }
}
