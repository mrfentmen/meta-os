#!/usr/bin/env node
// CB-096 — every frame in the set must have the same PNG dimensions.
import fs from "node:fs";
import path from "node:path";

export function pngSize(buf) {
  const signature = "89504e470d0a1a0a";
  if (buf.length < 24 || buf.subarray(0, 8).toString("hex") !== signature) {
    throw new Error("not a PNG");
  }
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

export function validateFrames(dir) {
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".png")).sort();
  const frames = files.map((file) => ({ file, ...pngSize(fs.readFileSync(path.join(dir, file))) }));
  const dimensions = [...new Set(frames.map((f) => f.width + "x" + f.height))];
  return { ok: dimensions.length === 1, frames, dimensions };
}

export function main(argv) {
  const dir = argv[0] || "os-build/demo/frames";
  const result = validateFrames(dir);
  console.log("frames: " + result.frames.length + ", dimensions: " + result.dimensions.join(", "));
  for (const frame of result.frames) console.log("  " + frame.file + " " + frame.width + "x" + frame.height);
  if (!result.ok) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
