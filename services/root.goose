// services/root.goose — the library root (B-1, Pax ruling F3).
//
// Goose resolves `import a.b.c;` relative to the directory of the ROOT file,
// so a root at services/ makes `common.err.err` mean services/common/err/err.goose.
// Without this file every service failed to resolve its own imports — that was
// 225 of the 297 errors the corpus reported.
//
// Every service's `svc_entry` lives in its own <svc>/entry.goose, so importing a
// module never drags a second entry symbol along. The five program roots next to
// this file import the entry modules; this root typechecks the libraries.

import agenthost.agenthost;
import agenthost.channel;
import agenthost.quota;
import audit.audit;
import audit.retention;
import bootlog.bootlog;
import callmatrix.callmatrix;
import clipboard.clipboard;
import common.args.args;
import common.boot.boot;
import common.bytes.bytes;
import common.cfg.cfg;
import common.enc.enc;
import common.err.err;
import common.fmt.fmt;
import common.hash.hash;
import common.hex.hex;
import common.json.json;
import common.pool.pool;
import common.ring.ring;
import common.sort.sort;
import common.status.status;
import common.str.str;
import common.sys.sys;
import common.table.table;
import common.text.text;
import console.console;
import console.esc;
import devices.devices;
import devices.hotplug;
import dhcp.dhcp;
import display.display;
import display.text;
import dns.dns;
import example.example;
import fs.fs;
import fs.fsck;
import fs.paths;
import input.input;
import input.keymaps2;
import logd.logd;
import logd.rotate;
import logfmt.logfmt;
import net.arp;
import net.icmp;
import net.ip;
import net.loopback;
import net.packet;
import net.tcp;
import net.udp;
import netcfg.netcfg;
import netcfg.persist;
import session.login;
import session.session;
import shell.shell;
import socket.bind;
import socket.socket;
import storage.storage;
import supervisor.bootorder;
import supervisor.deps;
import supervisor.supervisor;
import time.calendar;
import time.time;
import timesync.timesync;
import updater.delta;
import updater.signature;
import updater.updater;
import watchdog.metrics;
import watchdog.watchdog;

fn main() {}
