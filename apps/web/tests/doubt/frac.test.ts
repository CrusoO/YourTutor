import { describe, expect, it } from "vitest";
import { B0, Frac, bgcd, isqrt, bpow } from "@/lib/doubt/frac";
import { Poly } from "@/lib/doubt/poly";
import { int, rng } from "./helpers";

const big = (n: number) => BigInt(n);

describe("Frac", () => {
  it("normalises and prints exactly", () => {
    expect(Frac.of(6, -8).toString()).toBe("-3/4");
    expect(Frac.of(10, 5).toString()).toBe("2");
    expect(Frac.parse("0.125")?.toString()).toBe("1/8");
    expect(Frac.parse("-.5")?.toString()).toBe("-1/2");
    expect(Frac.parse("3 / 6")?.toString()).toBe("1/2");
    expect(Frac.parse("1/0")).toBeNull();
    expect(Frac.parse("1e3")).toBeNull();
    expect(Frac.parse("abc")).toBeNull();
  });
  it("has no floating point drift", () => {
    const tenth = Frac.of(1, 10);
    expect(tenth.add(tenth).add(tenth).eq(Frac.of(3, 10))).toBe(true);
  });
  it("is exact beyond 2^53", () => {
    const huge = Frac.of(BigInt("123456789012345678901234567890"));
    expect(huge.mul(huge).div(huge).eq(huge)).toBe(true);
    expect(huge.add(Frac.ONE).sub(huge).eq(Frac.ONE)).toBe(true);
  });
  it("division by zero throws, sqrt only of perfect squares", () => {
    expect(() => Frac.ONE.div(Frac.ZERO)).toThrow();
    expect(Frac.of(9, 4).sqrt()?.toString()).toBe("3/2");
    expect(Frac.of(2).sqrt()).toBeNull();
    expect(Frac.of(-4).sqrt()).toBeNull();
  });
  it("integer powers including negative", () => {
    expect(Frac.of(2, 3).pow(3).toString()).toBe("8/27");
    expect(Frac.of(2, 3).pow(-2).toString()).toBe("9/4");
  });

  it("property: matches a BigInt oracle for +, -, *, / and ordering (2000 random pairs)", () => {
    const r = rng(7);
    for (let i = 0; i < 2000; i++) {
      const [a, b, c, d] = [int(r, -999, 999), int(r, 1, 999), int(r, -999, 999), int(r, 1, 999)];
      const x = Frac.of(a, b);
      const y = Frac.of(c, d);
      // oracle: cross-multiplied integers, reduced by an independent gcd
      const red = (n: bigint, m: bigint): string => {
        const g = bgcd(n, m) || BigInt(1);
        let nn = n / g;
        let mm = m / g;
        if (mm < B0) {
          nn = -nn;
          mm = -mm;
        }
        return mm === BigInt(1) ? nn.toString() : `${nn}/${mm}`;
      };
      expect(x.add(y).toString()).toBe(red(big(a) * big(d) + big(c) * big(b), big(b) * big(d)));
      expect(x.sub(y).toString()).toBe(red(big(a) * big(d) - big(c) * big(b), big(b) * big(d)));
      expect(x.mul(y).toString()).toBe(red(big(a) * big(c), big(b) * big(d)));
      if (c !== 0) expect(x.div(y).toString()).toBe(red(big(a) * big(d), big(b) * big(c)));
      expect(x.cmp(y)).toBe(Math.sign(a * d - c * b));
    }
  });
  it("property: isqrt is floor(sqrt) and bpow matches repeated multiplication", () => {
    const r = rng(11);
    for (let i = 0; i < 500; i++) {
      const n = BigInt(int(r, 0, 2 ** 40)) * BigInt(int(r, 1, 2 ** 20));
      const s = isqrt(n);
      expect(s * s <= n && (s + BigInt(1)) * (s + BigInt(1)) > n).toBe(true);
      const base = BigInt(int(r, -9, 9));
      const e = int(r, 0, 12);
      let acc = BigInt(1);
      for (let k = 0; k < e; k++) acc *= base;
      expect(bpow(base, e)).toBe(acc);
    }
  });
});

describe("Poly", () => {
  const P = (...c: number[]) => new Poly(c.map((v) => Frac.of(v)));
  it("trims, adds, multiplies, shows", () => {
    expect(P(1, 2, 0, 0).degree).toBe(1);
    expect(P(1, 1).mul(P(-1, 1)).show()).toBe("x^2 - 1");
    expect(P(6, -5, 1).show()).toBe("x^2 - 5x + 6");
    expect(P(0).show()).toBe("0");
    expect(P(1, 1).pow(3).toStrings()).toEqual(["1", "3", "3", "1"]);
  });
  it("divides by an exact root and refuses a non-root", () => {
    expect(P(6, -5, 1).divideByRoot(Frac.of(2))?.show()).toBe("x - 3");
    expect(P(6, -5, 1).divideByRoot(Frac.of(1))).toBeNull();
  });
  it("detects scalar multiples", () => {
    expect(P(2, 4).isMultipleOf(P(1, 2))).toBe(true);
    expect(P(2, 5).isMultipleOf(P(1, 2))).toBe(false);
  });
  it("property: (p*q)(x) = p(x) q(x) exactly", () => {
    const r = rng(3);
    for (let i = 0; i < 300; i++) {
      const p = P(int(r, -9, 9), int(r, -9, 9), int(r, -9, 9));
      const q = P(int(r, -9, 9), int(r, -9, 9));
      const x = Frac.of(int(r, -20, 20), int(r, 1, 9));
      expect(p.mul(q).at(x).eq(p.at(x).mul(q.at(x)))).toBe(true);
    }
  });
});
