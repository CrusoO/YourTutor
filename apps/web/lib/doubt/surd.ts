import { B0, B1, B10, Frac, bpow, isqrt } from "./frac";

/**
 * Numbers of the form p + q*sqrt(d) with rational p, q and a square-free integer d > 1 (d = 0 means "rational").
 * Enough for the exact quadratic formula and for the leak filter to see through surd disguises.
 */
export type QNum = { readonly p: Frac; readonly q: Frac; readonly d: bigint };

const SQRT_LIMIT = bpow(B10, 15);

export function qRat(p: Frac): QNum {
  return { p, q: Frac.ZERO, d: B0 };
}

function norm(p: Frac, q: Frac, d: bigint): QNum {
  return q.isZero() || d === B0 ? { p, q: Frac.ZERO, d: B0 } : { p, q, d };
}

/** n = s*s*d with d square-free. Null when n is too large to split cheaply (trial division to its cube root). */
export function sqrtSplit(n: bigint): { s: bigint; d: bigint } | null {
  if (n < B1 || n > SQRT_LIMIT) return null;
  let s = B1;
  let d = B1;
  let rest = n;
  const two = BigInt(2);
  let f = two;
  while (f * f * f <= n) {
    while (rest % f === B0) {
      rest /= f;
      if (rest % f === B0) {
        rest /= f;
        s *= f;
      } else d *= f;
    }
    f += f === two ? B1 : two;
  }
  // Every prime left is above the cube root, so `rest` is 1, one prime, two primes or one prime squared.
  const r = isqrt(rest);
  if (r * r === rest) s *= r;
  else d *= rest;
  return { s, d };
}

export function qSqrt(x: QNum): QNum | null {
  if (x.d !== B0 || x.p.sign < 0) return null;
  const exact = x.p.sqrt();
  if (exact) return qRat(exact);
  const split = sqrtSplit(x.p.n * x.p.d);
  if (!split) return null;
  return norm(Frac.ZERO, Frac.of(split.s, x.p.d), split.d);
}

function sameRoot(a: QNum, b: QNum): bigint | null {
  if (a.d === B0) return b.d;
  if (b.d === B0 || a.d === b.d) return a.d;
  return null;
}

export function qAdd(a: QNum, b: QNum): QNum | null {
  const d = sameRoot(a, b);
  return d === null ? null : norm(a.p.add(b.p), a.q.add(b.q), d);
}
export function qNeg(a: QNum): QNum {
  return { p: a.p.neg(), q: a.q.neg(), d: a.d };
}
export function qSub(a: QNum, b: QNum): QNum | null {
  return qAdd(a, qNeg(b));
}
export function qMul(a: QNum, b: QNum): QNum | null {
  const d = sameRoot(a, b);
  if (d === null) return null;
  const dd = Frac.of(d === B0 ? B0 : d);
  return norm(a.p.mul(b.p).add(a.q.mul(b.q).mul(dd)), a.p.mul(b.q).add(a.q.mul(b.p)), d);
}
export function qDiv(a: QNum, b: QNum): QNum | null {
  if (b.d === B0) {
    if (b.p.isZero()) return null;
    return norm(a.p.div(b.p), a.q.div(b.p), a.d);
  }
  const d = sameRoot(a, b);
  if (d === null) return null;
  const den = b.p.mul(b.p).sub(b.q.mul(b.q).mul(Frac.of(d)));
  if (den.isZero()) return null;
  const num = qMul(a, { p: b.p, q: b.q.neg(), d });
  return num ? norm(num.p.div(den), num.q.div(den), num.d) : null;
}
export function qPow(a: QNum, e: number): QNum | null {
  if (!Number.isInteger(e) || Math.abs(e) > 64) return null;
  let base = a;
  if (e < 0) {
    const inv = qDiv(qRat(Frac.ONE), a);
    if (!inv) return null;
    base = inv;
  }
  let result = qRat(Frac.ONE);
  for (let i = 0; i < Math.abs(e); i++) {
    const next = qMul(result, base);
    if (!next) return null;
    result = next;
  }
  return result;
}
export function qEq(a: QNum, b: QNum): boolean {
  return a.p.eq(b.p) && a.q.eq(b.q) && a.d === b.d;
}
export function qIsRational(a: QNum): boolean {
  return a.d === B0;
}

/** Rational approximation within 1e-6 (exact integer arithmetic), for "is this decimal near that surd". */
export function qApprox(a: QNum): Frac {
  if (a.d === B0) return a.p;
  const scale = bpow(B10, 6);
  const root = Frac.of(isqrt(a.d * scale * scale), scale);
  return a.p.add(a.q.mul(root));
}

/** Canonical text "p+q√d": p omitted when 0, q omitted when 1, "+" only after a printed p. Rational: the fraction. */
export function qToString(a: QNum): string {
  if (a.d === B0) return a.p.toString();
  const qa = a.q.abs();
  const mag = qa.eq(Frac.ONE) ? "" : qa.toString();
  const tail = `${mag}√${a.d}`;
  if (a.p.isZero()) return `${a.q.sign < 0 ? "-" : ""}${tail}`;
  return `${a.p.toString()}${a.q.sign < 0 ? "-" : "+"}${tail}`;
}
