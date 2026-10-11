/**
 * Where the offline player keeps its pack, its session and its queue of unsent events.
 *
 * A key-value store with two backends: IndexedDB in the browser, and a plain in-memory map when
 * IndexedDB is missing or blocked (private windows, tests). The player works the same on both;
 * with the memory store nothing survives a reload, and the player says so through `durable`.
 */

export interface KeyValueStore {
  readonly durable: boolean;
  get<T = unknown>(key: string): Promise<T | undefined>;
  set(key: string, value: unknown): Promise<void>;
  delete(key: string): Promise<void>;
  keys(): Promise<string[]>;
}

export function memoryStore(): KeyValueStore {
  const map = new Map<string, string>();
  return {
    durable: false,
    async get<T>(key: string) {
      const raw = map.get(key);
      return raw === undefined ? undefined : (JSON.parse(raw) as T);
    },
    async set(key, value) {
      map.set(key, JSON.stringify(value));
    },
    async delete(key) {
      map.delete(key);
    },
    async keys() {
      return [...map.keys()].sort();
    },
  };
}

const STORE = "kv";

function open(name: string, factory: IDBFactory): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = factory.open(name, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error("indexeddb blocked"));
  });
}

function wrap<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** IndexedDB, or the memory store when it cannot be opened. */
export async function openStore(
  name = "yourtutor-offline",
  factory: IDBFactory | null = typeof indexedDB === "undefined" ? null : indexedDB,
): Promise<KeyValueStore> {
  if (!factory) return memoryStore();
  let db: IDBDatabase;
  try {
    db = await open(name, factory);
  } catch {
    return memoryStore();
  }
  const run = <T>(mode: IDBTransactionMode, work: (s: IDBObjectStore) => IDBRequest<T>) =>
    wrap(work(db.transaction(STORE, mode).objectStore(STORE)));
  return {
    durable: true,
    async get<T>(key: string) {
      const raw = await run("readonly", (s) => s.get(key));
      return raw === undefined ? undefined : (JSON.parse(String(raw)) as T);
    },
    async set(key, value) {
      await run("readwrite", (s) => s.put(JSON.stringify(value), key));
    },
    async delete(key) {
      await run("readwrite", (s) => s.delete(key));
    },
    async keys() {
      const all = await run("readonly", (s) => s.getAllKeys());
      return all.map(String).sort();
    },
  };
}
