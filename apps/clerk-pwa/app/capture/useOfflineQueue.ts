'use client';

import { useCallback } from 'react';

const DB_NAME = 'aura-offline-queue';
const STORE_NAME = 'scans';
const MAX_AGE_MS = 60 * 60 * 1000;

interface QueueEntry {
  id: string;
  hotelId: string;
  iv: string;
  ciphertext: string;
  queuedAt: number;
}

async function deriveKey(sessionToken: string): Promise<CryptoKey> {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    enc.encode(sessionToken),
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );
  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: enc.encode('aura-queue-salt'),
      iterations: 100_000,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

function toBase64(buf: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buf)));
}

function fromBase64(b64: string): Uint8Array<ArrayBuffer> {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  return new Uint8Array(
    bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)
  );
}

async function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () =>
      req.result.createObjectStore(STORE_NAME, { keyPath: 'id' });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function purgeExpired(db: IDBDatabase): Promise<void> {
  const now = Date.now();
  const tx = db.transaction(STORE_NAME, 'readwrite');
  const store = tx.objectStore(STORE_NAME);
  return new Promise((resolve, reject) => {
    const req = store.openCursor();
    req.onsuccess = () => {
      const cursor = req.result;
      if (!cursor) {
        resolve();
        return;
      }
      if (now - (cursor.value as QueueEntry).queuedAt > MAX_AGE_MS)
        cursor.delete();
      cursor.continue();
    };
    req.onerror = () => reject(req.error);
  });
}

export function useOfflineQueue() {
  const enqueue = useCallback(
    async (
      image: Blob,
      hotelId: string,
      sessionToken: string
    ): Promise<void> => {
      const key = await deriveKey(sessionToken);
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const imageBytes = await image.arrayBuffer();
      const ciphertext = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv },
        key,
        imageBytes
      );

      const entry: QueueEntry = {
        id: crypto.randomUUID(),
        hotelId,
        iv: toBase64(iv.buffer as ArrayBuffer),
        ciphertext: toBase64(ciphertext),
        queuedAt: Date.now(),
      };

      const db = await openDb();
      await purgeExpired(db);
      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const req = tx.objectStore(STORE_NAME).put(entry);
        req.onsuccess = () => resolve();
        req.onerror = () => reject(req.error);
      });
    },
    []
  );

  const dequeue = useCallback(
    async (
      sessionToken: string
    ): Promise<Array<{ id: string; hotelId: string; image: Blob }>> => {
      const db = await openDb();
      await purgeExpired(db);
      const key = await deriveKey(sessionToken);
      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const req = tx.objectStore(STORE_NAME).getAll();
        req.onsuccess = async () => {
          const entries = req.result as QueueEntry[];
          const items = await Promise.all(
            entries.map(async (e) => {
              const plaintext = await crypto.subtle.decrypt(
                { name: 'AES-GCM', iv: fromBase64(e.iv) },
                key,
                fromBase64(e.ciphertext)
              );
              return {
                id: e.id,
                hotelId: e.hotelId,
                image: new Blob([plaintext], { type: 'image/jpeg' }),
              };
            })
          );
          resolve(items);
        };
        req.onerror = () => reject(req.error);
      });
    },
    []
  );

  return { enqueue, dequeue };
}
