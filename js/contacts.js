// Contacts panel (Del direction 2026-10-29: Milo leads contacts,
// Medicus first). A human review directory per product: name, role,
// organization, stored locally in this browser only. Human-initiated
// only: nothing here sends, notifies, or dispatches anything, and no
// contact action ever runs on its own. Sample contacts are placeholders,
// never real people, and are always flagged sample so the UI labels
// them SAMPLE on screen. Pure module, no DOM: the app renders it.

import { isProductId } from "./products.js";

export const CONTACTS_STORAGE_KEY = "meta-trio-contacts-v1";

// Seed: Medicus first, per the direction. Every seeded entry is a
// SAMPLE placeholder, never a real person or office.
export const SAMPLE_CONTACTS = [
  {
    product: "medicus",
    name: "SAMPLE — EMS Review Lead",
    role: "Human reviewer (sample)",
    organization: "Sample EMS review office",
    sample: true,
  },
  {
    product: "medicus",
    name: "SAMPLE — EMS Field Supervisor",
    role: "EMS supervisor (sample)",
    organization: "Sample EMS review office",
    sample: true,
  },
];

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim() !== "";
}

function isWellFormedContact(entry) {
  return (
    entry &&
    typeof entry === "object" &&
    Number.isInteger(entry.id) &&
    isProductId(entry.product) &&
    isNonEmptyString(entry.name) &&
    isNonEmptyString(entry.role) &&
    isNonEmptyString(entry.organization) &&
    typeof entry.sample === "boolean"
  );
}

export class ContactsStore {
  constructor({ storage = null, storageKey = CONTACTS_STORAGE_KEY } = {}) {
    this._storage = storage;
    this._storageKey = storageKey;
    this._contacts = [];
    this._seq = 0;
    this._restore();
  }

  // First run (no saved data at all) seeds the Medicus SAMPLE contacts
  // and persists them, so deleting a sample removes it for good instead
  // of it reappearing on reload. A corrupt or wrong-shaped store loads
  // empty but stays usable; a missing or unwritable store keeps the
  // directory in memory only.
  _restore() {
    if (!this._storage) {
      this._seed();
      return;
    }
    let raw;
    try {
      raw = this._storage.getItem(this._storageKey);
    } catch {
      this._seed();
      return;
    }
    if (typeof raw !== "string" || raw === "") {
      this._seed();
      this._save();
      return;
    }
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch {
      return;
    }
    if (!Array.isArray(parsed)) return;
    for (const entry of parsed) {
      if (!isWellFormedContact(entry)) continue;
      this._contacts.push(entry);
      if (entry.id > this._seq) this._seq = entry.id;
    }
  }

  _seed() {
    for (const seed of SAMPLE_CONTACTS) {
      this._seq += 1;
      this._contacts.push({ id: this._seq, ...seed });
    }
  }

  _save() {
    if (!this._storage) return;
    try {
      this._storage.setItem(this._storageKey, JSON.stringify(this._contacts));
    } catch {
      // Private browsing, quota, or a disabled store: in-memory
      // contacts continue, and the next reload simply re-seeds.
    }
  }

  list(product) {
    return this._contacts.filter((entry) => entry.product === product);
  }

  listAll() {
    return this._contacts.slice();
  }

  get count() {
    return this._contacts.length;
  }

  add({ product, name, role, organization }) {
    if (!isProductId(product)) {
      throw new RangeError(`unknown product: ${product}`);
    }
    if (!isNonEmptyString(name) || !isNonEmptyString(role) || !isNonEmptyString(organization)) {
      throw new RangeError("contact name, role, and organization must all be non-empty");
    }
    this._seq += 1;
    const entry = {
      id: this._seq,
      product,
      name: name.trim(),
      role: role.trim(),
      organization: organization.trim(),
      sample: false,
    };
    this._contacts.push(entry);
    this._save();
    return entry;
  }

  remove(id) {
    const before = this._contacts.length;
    this._contacts = this._contacts.filter((entry) => entry.id !== id);
    if (this._contacts.length === before) return false;
    this._save();
    return true;
  }
}
