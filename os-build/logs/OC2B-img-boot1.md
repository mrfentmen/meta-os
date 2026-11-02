# OC2B-img boot log ‚Äî boot 2 (full cloud-init run, seed metaos-oc2b-02)

VM: qemu-system-x86_64 -m 2048 -drive file=/tmp/oc2b-img/oc2b-work.qcow2,format=qcow2 -cdrom /tmp/oc2b-img/seed.iso (serial). Power-on 2026-11-02 11:11:23 EST.

```
^[[H^[[J^[[1;1H^[[H^[[J^[[1;1H  Booting `Debian GNU/Linux'
^M
^MLoading Linux 6.1.0-54-amd64 ...
^MLoading initial ramdisk ...
^M[    0.000000] Linux version 6.1.0-54-amd64 (debian-kernel@lists.debian.org) (gcc-12 (Debian 12.2.0-14+deb12u1) 12.2.0, GNU ld (GNU Binutils for Debian) 2.40) #1 SMP PREEMPT_DYNAMIC Debian 6.1.190-1 (2026-10-16)^M
[    0.000000] Command line: BOOT_IMAGE=/boot/vmlinuz-6.1.0-54-amd64 root=PARTUUID=be22c4a2-1d9c-4f22-ad33-9612ac4dae03 ro console=tty0 console=ttyS0,115200 earlyprintk=ttyS0,115200 consoleblank=0^M
[    0.000000] BIOS-provided physical RAM map:^M
[    0.000000] BIOS-e820: [mem 0x0000000000000000-0x000000000009fbff] usable^M
[    0.000000] BIOS-e820: [mem 0x000000000009fc00-0x000000000009ffff] reserved^M
[    0.000000] BIOS-e820: [mem 0x00000000000f0000-0x00000000000fffff] reserved^M
[    0.000000] BIOS-e820: [mem 0x0000000000100000-0x000000007ffdffff] usable^M
[    0.000000] BIOS-e820: [mem 0x000000007ffe0000-0x000000007fffffff] reserved^M
[    0.000000] BIOS-e820: [mem 0x00000000fffc0000-0x00000000ffffffff] reserved^M
[    0.000000] BIOS-e820: [mem 0x000000fd00000000-0x000000ffffffffff] reserved^M
[    0.000000] printk: bootconsole [earlyser0] enabled^M
[    0.000000] NX (Execute Disable) protection: active^M
[    0.000000] SMBIOS 2.8 present.^M
[    0.000000] DMI: QEMU Standard PC (i440FX + PIIX, 1996), BIOS rel-1.17.0-0-gb52ca86e094d-prebuilt.qemu.org 04/01/2014^M
[    0.000000] tsc: Fast TSC calibration failed^M
[    0.000000] AGP: No AGP bridge found^M
[    0.000000] last_pfn = 0x7ffe0 max_arch_pfn = 0x400000000^M
[    0.000000] x86/PAT: Configuration [0-7]: WB  WC  UC- UC  WB  WP  UC- WT  ^M
Memory KASLR using RDTSC...^M
[    0.000000] found SMP MP-table at [mem 0x000f54c0-0x000f54cf]^M
[    0.000000] RAMDISK: [mem 0x343f7000-0x361f2fff]^M
[    0.000000] ACPI: Early table checksum verification disabled^M
[    0.000000] ACPI: RSDP 0x00000000000F52E0 000014 (v00 BOCHS )^M
[    0.000000] ACPI: RSDT 0x000000007FFE2329 000034 (v01 BOCHS  BXPC     00000001 BXPC 00000001)^M
[    0.000000] ACPI: FACP 0x000000007FFE21DD 000074 (v01 BOCHS  BXPC     00000001 BXPC 00000001)^M
[    0.000000] ACPI: DSDT 0x000000007FFE0040 00219D (v01 BOCHS  BXPC     00000001 BXPC 00000001)^M
[    0.000000] ACPI: FACS 0x000000007FFE0000 000040^M
[    0.000000] ACPI: APIC 0x000000007FFE2251 000078 (v03 BOCHS  BXPC     00000001 BXPC 00000001)^M
[    0.000000] ACPI: HPET 0x000000007FFE22C9 000038 (v01 BOCHS  BXPC     00000001 BXPC 00000001)^M
[    0.000000] ACPI: WAET 0x000000007FFE2301 000028 (v01 BOCHS  BXPC     00000001 BXPC 00000001)^M
[    0.000000] ACPI: Reserving FACP table memory at [mem 0x7ffe21dd-0x7ffe2250]^M
[    0.000000] ACPI: Reserving DSDT table memory at [mem 0x7ffe0040-0x7ffe21dc]^M
[    0.000000] ACPI: Reserving FACS table memory at [mem 0x7ffe0000-0x7ffe003f]^M
[    0.000000] ACPI: Reserving APIC table memory at [mem 0x7ffe2251-0x7ffe22c8]^M
[    0.000000] ACPI: Reserving HPET table memory at [mem 0x7ffe22c9-0x7ffe2300]^M
[    0.000000] ACPI: Reserving WAET table memory at [mem 0x7ffe2301-0x7ffe2328]^M
[    0.000000] No NUMA configuration found^M
[    0.000000] Faking a node at [mem 0x0000000000000000-0x000000007ffdffff]^M
[    0.000000] NODE_DATA(0) allocated [mem 0x7ffb5000-0x7ffdffff]^M
[    0.000000] Zone ranges:^M
[    0.000000]   DMA      [mem 0x0000000000001000-0x0000000000ffffff]^M
[    0.000000]   DMA32    [mem 0x0000000001000000-0x000000007ffdffff]^M
[    0.000000]   Normal   empty^M
[    0.000000]   Device   empty^M
[    0.000000] Movable zone start for each node^M
[    0.000000] Early memory node ranges^M
[    0.000000]   node   0: [mem 0x0000000000001000-0x000000000009efff]^M
[    0.000000]   node   0: [mem 0x0000000000100000-0x000000007ffdffff]^M
[    0.000000] Initmem setup node 0 [mem 0x0000000000001000-0x000000007ffdffff]^M
[    0.000000] On node 0, zone DMA: 1 pages in unavailable ranges^M
[    0.000000] On node 0, zone DMA: 97 pages in unavailable ranges^M
[    0.000000] On node 0, zone DMA32: 32 pages in unavailable ranges^M
[    0.000000] ACPI: PM-Timer IO Port: 0x608^M
[    0.000000] ACPI: LAPIC_NMI (acpi_id[0xff] dfl dfl lint[0x1])^M
[    0.000000] IOAPIC[0]: apic_id 0, version 32, address 0xfec00000, GSI 0-23^M
[    0.000000] ACPI: INT_SRC_OVR (bus 0 bus_irq 0 global_irq 2 dfl dfl)^M
[    0.000000] ACPI: INT_SRC_OVR (bus 0 bus_irq 5 global_irq 5 high level)^M
[    0.000000] ACPI: INT_SRC_OVR (bus 0 bus_irq 9 global_irq 9 high level)^M
[    0.000000] ACPI: INT_SRC_OVR (bus 0 bus_irq 10 global_irq 10 high level)^M
[    0.000000] ACPI: INT_SRC_OVR (bus 0 bus_irq 11 global_irq 11 high level)^M
[    0.000000] ACPI: Using ACPI (MADT) for SMP configuration information^M
[    0.000000] ACPI: HPET id: 0x8086a201 base: 0xfed00000^M
[    0.000000] smpboot: Allowing 1 CPUs, 0 hotplug CPUs^M
[    0.000000] PM: hibernation: Registered nosave memory: [mem 0x00000000-0x00000fff]^M
[    0.000000] PM: hibernation: Registered nosave memory: [mem 0x0009f000-0x000fffff]^M
[    0.000000] [mem 0x80000000-0xfffbffff] available for PCI devices^M
[    0.000000] Booting paravirtualized kernel on bare hardware^M
[    0.000000] clocksource: refined-jiffies: mask: 0xffffffff max_cycles: 0xffffffff, max_idle_ns: 7645519600211568 ns^M
[    0.000000] setup_percpu: NR_CPUS:8192 nr_cpumask_bits:1 nr_cpu_ids:1 nr_node_ids:1^M
[    0.000000] percpu: Embedded 62 pages/cpu s217088 r8192 d28672 u2097152^M
[    0.000000] Fallback order for Node 0: 0 ^M
[    0.000000] Built 1 zonelists, mobility grouping on.  Total pages: 515808^M
[    0.000000] Policy zone: DMA32^M
[    0.000000] Kernel command line: BOOT_IMAGE=/boot/vmlinuz-6.1.0-54-amd64 root=PARTUUID=be22c4a2-1d9c-4f22-ad33-9612ac4dae03 ro console=tty0 console=ttyS0,115200 earlyprintk=ttyS0,115200 consoleblank=0^M
[    0.000000] Dentry cache hash table entries: 262144 (order: 9, 2097152 bytes, linear)^M
[    0.000000] Inode-cache hash table entries: 131072 (order: 8, 1048576 bytes, linear)^M
[    0.000000] mem auto-init: stack:all(zero), heap alloc:on, heap free:off^M
[    0.000000] AGP: Checking aperture...^M
[    0.000000] AGP: No AGP bridge found^M
[    0.000000] Memory: 223996K/2096632K available (14343K kernel code, 2338K rwdata, 9124K rodata, 2816K init, 17356K bss, 120980K reserved, 0K cma-reserved)^M
[    0.000000] SLUB: HWalign=64, Order=0-3, MinObjects=0, CPUs=1, Nodes=1^M
Poking KASLR using RDTSC...^M
[    0.000000] ftrace: allocating 40482 entries in 159 pages^M
[    0.000000] ftrace: allocated 159 pages with 6 groups^M
[    0.000000] Dynamic Preempt: voluntary^M
[    0.000000] rcu: Preemptible hierarchical RCU implementation.^M
[    0.000000] rcu: 	RCU restricting CPUs from NR_CPUS=8192 to nr_cpu_ids=1.^M
[    0.000000] 	Trampoline variant of Tasks RCU enabled.^M
[    0.000000] 	Rude variant of Tasks RCU enabled.^M
[    0.000000] 	Tracing variant of Tasks RCU enabled.^M
[    0.000000] rcu: RCU calculated value of scheduler-enlistment delay is 25 jiffies.^M
[    0.000000] rcu: Adjusting geometry for rcu_fanout_leaf=16, nr_cpu_ids=1^M
[    0.000000] NR_IRQS: 524544, nr_irqs: 256, preallocated irqs: 16^M
[    0.000000] rcu: srcu_init: Setting srcu_struct sizes based on contention.^M
[    0.000000] Console: colour VGA+ 80x25^M
[    0.000000] printk: console [tty0] enabled^M
[    0.000000] printk: console [ttyS0] enabled^M
[    0.000000] printk: console [ttyS0] enabled^M
[    0.000000] printk: bootconsole [earlyser0] disabled^M
[    0.000000] printk: bootconsole [earlyser0] disabled^M
[    0.000000] ACPI: Core revision 20220331^M
[    0.000000] clocksource: hpet: mask: 0xffffffff max_cycles: 0xffffffff, max_idle_ns: 19112604467 ns^M
[    0.000000] APIC: Switch to symmetric I/O mode setup^M
[    0.004000] ..TIMER: vector=0x30 apic1=0 pin1=2 apic2=-1 pin2=-1^M
[    0.036000] tsc: Unable to calibrate against PIT^M
[    0.036000] tsc: using HPET reference calibration^M
[    0.036000] tsc: Detected 999.404 MHz processor^M
[    0.001223] clocksource: tsc-early: mask: 0xffffffffffffffff max_cycles: 0x1ccfc809dbf, max_idle_ns: 881590448906 ns^M
[    0.002105] Calibrating delay loop (skipped), value calculated using timer frequency.. 1998.80 BogoMIPS (lpj=3997616)^M
[    0.007237] process: using AMD E400 aware idle routine^M
[    0.007681] Last level iTLB entries: 4KB 512, 2MB 255, 4MB 127^M
[    0.007986] Last level dTLB entries: 4KB 512, 2MB 255, 4MB 127, 1GB 0^M
[    0.008507] Spectre V1 : Mitigation: usercopy/swapgs barriers and __user pointer sanitization^M
[    0.009009] Spectre V2 : Mitigation: Retpolines^M
[    0.009248] Spectre V2 : Spectre v2 / SpectreRSB: Filling RSB on context switch and VMEXIT^M
[    0.011337] x86/fpu: x87 FPU will use FXSAVE^M
[    0.383042] Freeing SMP alternatives memory: 36K^M
[    0.384084] pid_max: default: 32768 minimum: 301^M
[    0.391889] LSM: Security Framework initializing^M
[    0.394124] landlock: Up and running.^M
[    0.394384] Yama: disabled by default; enable with sysctl kernel.yama.*^M
[    0.397550] AppArmor: AppArmor initialized^M
[    0.398184] TOMOYO Linux initialized^M
[    0.398868] LSM support for eBPF active^M
[    0.401443] Mount-cache hash table entries: 4096 (order: 3, 32768 bytes, linear)^M
[    0.402114] Mountpoint-cache hash table entries: 4096 (order: 3, 32768 bytes, linear)^M
[    0.487309] smpboot: CPU0: AMD QEMU Virtual CPU version 2.5+ (family: 0xf, model: 0x6b, stepping: 0x1)^M
[    0.490986] cblist_init_generic: Setting adjustable number of callback queues.^M
[    0.491352] cblist_init_generic: Setting shift to 0 and lim to 1.^M
[    0.491835] cblist_init_generic: Setting adjustable number of callback queues.^M
[    0.492161] cblist_init_generic: Setting shift to 0 and lim to 1.^M
[    0.492736] cblist_init_generic: Setting adjustable number of callback queues.^M
[    0.493062] cblist_init_generic: Setting shift to 0 and lim to 1.^M
[    0.493543] Performance Events: PMU not available due to virtualization, using software events only.^M
[    0.495087] signal: max sigframe size: 1440^M
[    0.498699] rcu: Hierarchical SRCU implementation.^M
[    0.499727] rcu: 	Max phase no-delay instances is 1000.^M
[    0.503610] NMI watchdog: Perf NMI watchdog permanently disabled^M
[    0.507615] smp: Bringing up secondary CPUs ...^M
[    0.507937] smp: Brought up 1 node, 1 CPU^M
[    0.508156] smpboot: Max logical packages: 1^M
[    0.508409] smpboot: Total of 1 processors activated (1998.80 BogoMIPS)^M
[    0.560322] node 0 deferred pages initialised in 44ms^M
[    0.576056] devtmpfs: initialized^M
[    0.580146] x86/mm: Memory block size: 128MB^M
[    0.588117] clocksource: jiffies: mask: 0xffffffff max_cycles: 0xffffffff, max_idle_ns: 7645041785100000 ns^M
[    0.590457] futex hash table entries: 256 (order: 2, 16384 bytes, linear)^M
[    0.594285] pinctrl core: initialized pinctrl subsystem^M
[    0.610616] NET: Registered PF_NETLINK/PF_ROUTE protocol family^M
[    0.615695] DMA: preallocated 256 KiB GFP_KERNEL pool for atomic allocations^M
[    0.617941] DMA: preallocated 256 KiB GFP_KERNEL|GFP_DMA pool for atomic allocations^M
[    0.617941] DMA: preallocated 256 KiB GFP_KERNEL|GFP_DMA32 pool for atomic allocations^M
[    0.617941] audit: initializing netlink subsys (disabled)^M
[    0.621941] thermal_sys: Registered thermal governor 'fair_share'^M
[    0.622365] audit: type=2000 audit(1793635930.652:1): state=initialized audit_enabled=0 res=1^M
[    0.623276] thermal_sys: Registered thermal governor 'bang_bang'^M
[    0.623293] thermal_sys: Registered thermal governor 'step_wise'^M
[    0.623559] thermal_sys: Registered thermal governor 'user_space'^M
[    0.623819] thermal_sys: Registered thermal governor 'power_allocator'^M
[    0.625023] cpuidle: using governor ladder^M
[    0.625593] cpuidle: using governor menu^M
[    0.625941] acpiphp: ACPI Hot Plug PCI Controller Driver version: 0.5^M
[    0.632438] PCI: Using configuration type 1 for base access^M
[    0.649941] kprobes: kprobe jump-optimization is enabled. All kprobes are optimized if possible.^M
[    0.707490] HugeTLB: registered 2.00 MiB page size, pre-allocated 0 pages^M
[    0.707920] HugeTLB: 28 KiB vmemmap can be freed for a 2.00 MiB page^M
[    0.722277] ACPI: Added _OSI(Module Device)^M
[    0.722580] ACPI: Added _OSI(Processor Device)^M
[    0.722789] ACPI: Added _OSI(Processor Aggregator Device)^M
[    0.739292] ACPI: 1 ACPI AML tables successfully acquired and loaded^M
[    0.754499] ACPI: Interpreter enabled^M
[    0.755686] ACPI: PM: (supports S0 S3 S4 S5)^M
[    0.755943] ACPI: Using IOAPIC for interrupt routing^M
[    0.756553] PCI: Using host bridge windows from ACPI; if necessary, use "pci=nocrs" and report a bug^M
[    0.756975] PCI: Using E820 reservations for host bridge windows^M
[    0.759320] ACPI: Enabled 2 GPEs in block 00 to 0F^M
[    0.798087] ACPI: PCI Root Bridge [PCI0] (domain 0000 [bus 00-ff])^M
[    0.799075] acpi PNP0A03:00: _OSC: OS supports [ASPM ClockPM Segments MSI HPX-Type3]^M
[    0.799571] acpi PNP0A03:00: _OSC: not requesting OS control; OS requires [ExtendedConfig ASPM ClockPM MSI]^M
[    0.800597] acpi PNP0A03:00: fail to add MMCONFIG information, can't access extended PCI configuration space under this bridge.^M
[    0.807635] acpiphp: Slot [3] registered^M
[    0.808006] acpiphp: Slot [4] registered^M
[    0.808273] acpiphp: Slot [5] registered^M
[    0.808548] acpiphp: Slot [6] registered^M
[    0.808796] acpiphp: Slot [7] registered^M
[    0.810033] acpiphp: Slot [8] registered^M
[    0.810314] acpiphp: Slot [9] registered^M
[    0.810653] acpiphp: Slot [10] registered^M
[    0.811839] acpiphp: Slot [11] registered^M
[    0.812104] acpiphp: Slot [12] registered^M
[    0.812375] acpiphp: Slot [13] registered^M
[    0.812623] acpiphp: Slot [14] registered^M
[    0.812874] acpiphp: Slot [15] registered^M
[    0.813123] acpiphp: Slot [16] registered^M
[    0.813371] acpiphp: Slot [17] registered^M
[    0.814075] acpiphp: Slot [18] registered^M
[    0.814414] acpiphp: Slot [19] registered^M
[    0.816020] acpiphp: Slot [20] registered^M
[    0.816578] acpiphp: Slot [21] registered^M
[    0.816837] acpiphp: Slot [22] registered^M
[    0.817088] acpiphp: Slot [23] registered^M
[    0.818020] acpiphp: Slot [24] registered^M
[    0.818285] acpiphp: Slot [25] registered^M
[    0.818559] acpiphp: Slot [26] registered^M
[    0.818810] acpiphp: Slot [27] registered^M
[    0.819059] acpiphp: Slot [28] registered^M
[    0.819704] acpiphp: Slot [29] registered^M
[    0.820372] acpiphp: Slot [30] registered^M
[    0.820630] acpiphp: Slot [31] registered^M
[    0.821052] PCI host bridge to bus 0000:00^M
[    0.821418] pci_bus 0000:00: root bus resource [io  0x0000-0x0cf7 window]^M
[    0.821844] pci_bus 0000:00: root bus resource [io  0x0d00-0xffff window]^M
[    0.821941] pci_bus 0000:00: root bus resource [mem 0x000a0000-0x000bffff window]^M
[    0.821941] pci_bus 0000:00: root bus resource [mem 0x80000000-0xfebfffff window]^M
[    0.821941] pci_bus 0000:00: root bus resource [mem 0x100000000-0x17fffffff window]^M
[    0.822503] pci_bus 0000:00: root bus resource [bus 00-ff]^M
[    0.823954] pci 0000:00:00.0: [8086:1237] type 00 class 0x060000^M
[    0.825941] pci 0000:00:01.0: [8086:7000] type 00 class 0x060100^M
[    0.825941] pci 0000:00:01.1: [8086:7010] type 00 class 0x010180^M
[    0.827160] pci 0000:00:01.1: BAR 4 [io  0xc040-0xc04f]^M
[    0.827828] pci 0000:00:01.1: BAR 0 [io  0x01f0-0x01f7]: legacy IDE quirk^M
[    0.828159] pci 0000:00:01.1: BAR 1 [io  0x03f6]: legacy IDE quirk^M
[    0.828458] pci 0000:00:01.1: BAR 2 [io  0x0170-0x0177]: legacy IDE quirk^M
[    0.828765] pci 0000:00:01.1: BAR 3 [io  0x0376]: legacy IDE quirk^M
[    0.830849] pci 0000:00:01.3: [8086:7113] type 00 class 0x068000^M
[    0.831483] pci 0000:00:01.3: quirk: [io  0x0600-0x063f] claimed by PIIX4 ACPI^M
[    0.831836] pci 0000:00:01.3: quirk: [io  0x0700-0x070f] claimed by PIIX4 SMB^M
[    0.833895] pci 0000:00:02.0: [1234:1111] type 00 class 0x030000^M
[    0.833941] pci 0000:00:02.0: BAR 0 [mem 0xfd000000-0xfdffffff pref]^M
[    0.833941] pci 0000:00:02.0: BAR 2 [mem 0xfebf0000-0xfebf0fff]^M
[    0.833941] pci 0000:00:02.0: ROM [mem 0xfebe0000-0xfebeffff pref]^M
[    0.833941] pci 0000:00:02.0: Video device with shadowed ROM at [mem 0x000c0000-0x000dffff]^M
[    0.833941] pci 0000:00:03.0: [8086:100e] type 00 class 0x020000^M
[    0.833941] pci 0000:00:03.0: BAR 0 [mem 0xfebc0000-0xfebdffff]^M
[    0.833941] pci 0000:00:03.0: BAR 1 [io  0xc000-0xc03f]^M
[    0.833941] pci 0000:00:03.0: ROM [mem 0xfeb80000-0xfebbffff pref]^M
[    0.836269] ACPI: PCI: Interrupt link LNKA configured for IRQ 10^M
[    0.838198] ACPI: PCI: Interrupt link LNKB configured for IRQ 10^M
[    0.838964] ACPI: PCI: Interrupt link LNKC configured for IRQ 11^M
[    0.839581] ACPI: PCI: Interrupt link LNKD configured for IRQ 11^M
[    0.840006] ACPI: PCI: Interrupt link LNKS configured for IRQ 9^M
[    0.841941] iommu: Default domain type: Translated ^M
[    0.841941] iommu: DMA domain TLB invalidation policy: lazy mode ^M
[    0.841941] pps_core: LinuxPPS API ver. 1 registered^M
[    0.841941] pps_core: Software ver. 5.3.6 - Copyright 2005-2007 Rodolfo Giometti <giometti@linux.it>^M
[    0.841941] PTP clock support registered^M
[    0.841941] EDAC MC: Ver: 3.0.0^M
[    0.849941] NetLabel: Initializing^M
[    0.849941] NetLabel:  domain hash size = 128^M
[    0.849941] NetLabel:  protocols = UNLABELED CIPSOv4 CALIPSO^M
[    0.849941] NetLabel:  unlabeled traffic allowed by default^M
[    0.849941] PCI: Using ACPI for IRQ routing^M
[    0.851032] pci 0000:00:02.0: vgaarb: setting as boot VGA device^M
[    0.851396] pci 0000:00:02.0: vgaarb: bridge control possible^M
[    0.851702] pci 0000:00:02.0: vgaarb: VGA device added: decodes=io+mem,owns=io+mem,locks=none^M
[    0.852095] vgaarb: loaded^M
[    0.852897] hpet: 3 channels of 0 reserved for per-cpu timers^M
[    0.853410] hpet0: at MMIO 0xfed00000, IRQs 2, 8, 0^M
[    0.853701] hpet0: 3 comparators, 64-bit 100.000000 MHz counter^M
[    0.853941] clocksource: Switched to clocksource tsc-early^M
[    0.954526] VFS: Disk quotas dquot_6.6.0^M
[    0.955023] VFS: Dquot-cache hash table entries: 512 (order 0, 4096 bytes)^M
[    0.962139] AppArmor: AppArmor Filesystem Enabled^M
[    0.962767] pnp: PnP ACPI init^M
[    0.964827] ACPI: IRQ 4 override to edge(!), high(!)^M
[    0.968153] pnp: PnP ACPI: found 6 devices^M
[    0.987931] clocksource: acpi_pm: mask: 0xffffff max_cycles: 0xffffff, max_idle_ns: 2085701024 ns^M
[    0.989324] NET: Registered PF_INET protocol family^M
[    0.991266] IP idents hash table entries: 32768 (order: 6, 262144 bytes, linear)^M
[    1.000781] tcp_listen_portaddr_hash hash table entries: 1024 (order: 2, 16384 bytes, linear)^M
[    1.001413] Table-perturb hash table entries: 65536 (order: 6, 262144 bytes, linear)^M
[    1.002824] TCP established hash table entries: 16384 (order: 5, 131072 bytes, linear)^M
[    1.003576] TCP bind hash table entries: 16384 (order: 7, 524288 bytes, linear)^M
[    1.004155] TCP: Hash tables configured (established 16384 bind 16384)^M
[    1.005826] MPTCP token hash table entries: 2048 (order: 4, 49152 bytes, linear)^M
[    1.006399] UDP hash table entries: 1024 (order: 3, 32768 bytes, linear)^M
[    1.006866] UDP-Lite hash table entries: 1024 (order: 3, 32768 bytes, linear)^M
[    1.008273] NET: Registered PF_UNIX/PF_LOCAL protocol family^M
[    1.008810] NET: Registered PF_XDP protocol family^M
[    1.011903] pci_bus 0000:00: resource 4 [io  0x0000-0x0cf7 window]^M
[    1.012244] pci_bus 0000:00: resource 5 [io  0x0d00-0xffff window]^M
[    1.012783] pci_bus 0000:00: resource 6 [mem 0x000a0000-0x000bffff window]^M
[    1.013129] pci_bus 0000:00: resource 7 [mem 0x80000000-0xfebfffff window]^M
[    1.013431] pci_bus 0000:00: resource 8 [mem 0x100000000-0x17fffffff window]^M
[    1.014240] pci 0000:00:01.0: PIIX3: Enabling Passive Release^M
[    1.014559] pci 0000:00:00.0: Limiting direct PCI/PCI transfers^M
[    1.014942] PCI: CLS 0 bytes, default 64^M
[    1.020056] Trying to unpack rootfs image as initramfs...^M
[    1.035776] Initialise system trusted keyrings^M
[    1.037591] Key type blacklist registered^M
[    1.039818] workingset: timestamp_bits=36 max_order=19 bucket_order=0^M
[    1.081939] zbud: loaded^M
[    1.097024] integrity: Platform Keyring initialized^M
[    1.097625] integrity: Machine keyring initialized^M
[    1.097866] Key type asymmetric registered^M
[    1.098131] Asymmetric key parser 'x509' registered^M
[    2.046995] tsc: Refined TSC clocksource calibration: 999.994 MHz^M
[    2.055586] clocksource: tsc: mask: 0xffffffffffffffff max_cycles: 0x1cd422f1293, max_idle_ns: 881590485101 ns^M
[    2.070937] clocksource: Switched to clocksource tsc^M
[    5.254504] Freeing initrd memory: 30704K^M
[    5.406660] alg: self-tests for CTR-KDF (hmac(sha256)) passed^M
[    5.407334] Block layer SCSI generic (bsg) driver version 0.4 loaded (major 248)^M
[    5.408931] io scheduler mq-deadline registered^M
[    5.417338] shpchp: Standard Hot Plug PCI Controller Driver version: 0.4^M
[    5.421693] Serial: 8250/16550 driver, 4 ports, IRQ sharing enabled^M
[    5.423053] 00:04: ttyS0 at I/O 0x3f8 (irq = 4, base_baud = 115200) is a 16550A^M
[    5.429256] Linux agpgart interface v0.103^M
[    5.431378] AMD-Vi: AMD IOMMUv2 functionality not available on this system - This is not a bug.^M
[    5.434576] i8042: PNP: PS/2 Controller [PNP0303:KBD,PNP0f13:MOU] at 0x60,0x64 irq 1,12^M
[    5.434576] serio: i8042 KBD port at 0x60,0x64 irq 1^M
[    5.439753] serio: i8042 AUX port at 0x60,0x64 irq 12^M
[    5.442093] mousedev: PS/2 mouse device common for all mice^M
[    5.442530] input: AT Translated Set 2 keyboard as /devices/platform/i8042/serio0/input/input0^M
[    5.442530] rtc_cmos 00:05: RTC can wake from S4^M
[    5.442530] rtc_cmos 00:05: registered as rtc0^M
[    5.442530] rtc_cmos 00:05: setting system clock to 2026-11-02T16:12:15 UTC (1793635935)^M
[    5.454118] rtc_cmos 00:05: alarms up to one day, y3k, 242 bytes nvram, hpet irqs^M
[    5.454911] ledtrig-cpu: registered to indicate activity on CPUs^M
[    5.524587] NET: Registered PF_INET6 protocol family^M
[    5.570070] Segment Routing with IPv6^M
[    5.571218] In-situ OAM (IOAM) with IPv6^M
[    5.571794] mip6: Mobile IPv6^M
[    5.572188] NET: Registered PF_PACKET protocol family^M
[    5.572834] mpls_gso: MPLS GSO support^M
[    5.574651] IPI shorthand broadcast: enabled^M
[    5.576017] sched_clock: Marking stable (5613172635, -38058843)->(5704994526, -129880734)^M
[    5.578577] registered taskstats version 1^M
[    5.579229] Loading compiled-in X.509 certificates^M
[    5.731602] Loaded X.509 cert 'Build time autogenerated kernel key: fc405883341a8944a6c6f2b9ec2bcb864fa2632f'^M
[    5.735715] zswap: loaded using pool lzo/zbud^M
[    5.737940] Key type .fscrypt registered^M
[    5.738182] Key type fscrypt-provisioning registered^M
[    5.785879] Key type encrypted registered^M
[    5.786257] AppArmor: AppArmor sha1 policy hashing enabled^M
[    5.786930] ima: No TPM chip found, activating TPM-bypass!^M
[    5.788394] ima: Allocated hash algorithm: sha256^M
[    5.791253] ima: No architecture policies found^M
[    5.796406] evm: Initialising EVM extended attributes:^M
[    5.796666] evm: security.selinux^M
[    5.796860] evm: security.SMACK64 (disabled)^M
[    5.797058] evm: security.SMACK64EXEC (disabled)^M
[    5.797263] evm: security.SMACK64TRANSMUTE (disabled)^M
[    5.797670] evm: security.SMACK64MMAP (disabled)^M
[    5.797881] evm: security.apparmor^M
[    5.798037] evm: security.ima^M
[    5.798179] evm: security.capability^M
[    5.798352] evm: HMAC attrs: 0x1^M
[    6.646610] clk: Disabling unused clocks^M
[    6.662297] Freeing unused decrypted memory: 2036K^M
[    6.725249] Freeing unused kernel image (initmem) memory: 2816K^M
[    6.725777] Write protecting the kernel read-only data: 26624k^M
[    6.729466] Freeing unused kernel image (text/rodata gap) memory: 2040K^M
[    6.730697] Freeing unused kernel image (rodata/data gap) memory: 1116K^M
[    6.957477] x86/mm: Checked W+X mappings: passed, no W+X pages found.^M
[    6.958211] Run /init as init process^M
Loading, please wait...^M
Starting systemd-udevd version 252.39-1~deb12u2^M^M
[    8.222461] Floppy drive(s): fd0 is 2.88M AMI BIOS^M
[    8.259731] FDC 0 is a S82078B^M
[    8.361889] piix4_smbus 0000:00:01.3: SMBus Host Controller at 0x700, revision 0^M
[    8.474835] e1000: Intel(R) PRO/1000 Network Driver^M
[    8.476252] e1000: Copyright (c) 1999-2006 Intel Corporation.^M
[    8.573814] ACPI: \_SB_.LNKC: Enabled at IRQ 11^M
[    8.670415] SCSI subsystem initialized^M
[    8.738101] input: ImExPS/2 Generic Explorer Mouse as /devices/platform/i8042/serio1/input/input2^M
[    9.171548] scsi host0: ata_piix^M
[    9.176864] scsi host1: ata_piix^M
[    9.177530] ata1: PATA max MWDMA2 cmd 0x1f0 ctl 0x3f6 bmdma 0xc040 irq 14^M
[    9.177895] ata2: PATA max MWDMA2 cmd 0x170 ctl 0x376 bmdma 0xc048 irq 15^M
[    9.340189] ata1: found unknown device (class 0)^M
[    9.344142] ata1.00: ATA-7: QEMU HARDDISK, 2.5+, max UDMA/100^M
[    9.344490] ata1.00: 27262976 sectors, multi 16: LBA48 ^M
[    9.345598] ata2: found unknown device (class 0)^M
[    9.346307] ata2.00: ATAPI: QEMU DVD-ROM, 2.5+, max UDMA/100^M
[    9.366539] scsi 0:0:0:0: Direct-Access     ATA      QEMU HARDDISK    2.5+ PQ: 0 ANSI: 5^M
[    9.374008] e1000 0000:00:03.0 eth0: (PCI:33MHz:32-bit) 52:54:00:12:34:56^M
[    9.374757] e1000 0000:00:03.0 eth0: Intel(R) PRO/1000 Network Connection^M
[    9.380776] scsi 1:0:0:0: CD-ROM            QEMU     QEMU DVD-ROM     2.5+ PQ: 0 ANSI: 5^M
[    9.525113] sr 1:0:0:0: [sr0] scsi3-mmc drive: 4x/4x cd/rw xa/form2 tray^M
[    9.527377] e1000 0000:00:03.0 ens3: renamed from eth0^M
[    9.591919] cdrom: Uniform CD-ROM driver Revision: 3.20^M
[    9.746050] sd 0:0:0:0: [sda] 27262976 512-byte logical blocks: (14.0 GB/13.0 GiB)^M
[    9.746935] sd 0:0:0:0: [sda] Write Protect is off^M
[    9.754338] sd 0:0:0:0: [sda] Write cache: enabled, read cache: enabled, doesn't support DPO or FUA^M
[    9.755316] sd 0:0:0:0: [sda] Preferred minimum I/O size 512 bytes^M
[    9.805931]  sda: sda1 sda14 sda15^M
[    9.812477] sd 0:0:0:0: [sda] Attached SCSI disk^M
Begin: Loading essential drivers ... done.^M
Begin: Running /scripts/init-premount ... done.^M
Begin: Mounting root file system ... Begin: Running /scripts/local-top ... done.^M
Begin: Running /scripts/local-premount ... done.^M
[   10.219887] I/O error, dev fd0, sector 0 op 0x0:(READ) flags 0x0 phys_seg 1 prio class 2^M
[   10.220387] floppy: error 10 while reading block 0^M
Warning: fsck not present, so skipping root file system^M
[   10.766447] EXT4-fs (sda1): INFO: recovery required on readonly filesystem^M
[   10.766895] EXT4-fs (sda1): write access will be enabled during recovery^M
[   11.250484] EXT4-fs (sda1): recovery complete^M
[   11.253949] EXT4-fs (sda1): mounted filesystem with ordered data mode. Quota mode: none.^M
done.^M
Begin: Running /scripts/local-bottom ... GROWROOT: NOCHANGE: partition 1 is size 27000799. it cannot be grown^M
done.^M
Begin: Running /scripts/init-bottom ... done.^M
[   11.969022] Not activating Mandatory Access Control as /sbin/tomoyo-init does not exist.^M
[   12.501204] systemd[1]: Inserted module 'autofs4'^M
[   12.668092] systemd[1]: systemd 252.39-1~deb12u2 running in system mode (+PAM +AUDIT +SELINUX +APPARMOR +IMA +SMACK +SECCOMP +GCRYPT -GNUTLS +OPENSSL +ACL +BLKID +CURL +ELFUTILS +FIDO2 +IDN2 -IDN +IPTC +KMOD +LIBCRYPTSETUP +LIBFDISK +PCRE2 -PWQUALITY +P11KIT +QRENCODE +TPM2 +BZIP2 +LZ4 +XZ +ZLIB +ZSTD -BPF_FRAMEWORK -XKBCOMMON +UTMP +SYSVINIT default-hierarchy=unified)^M
[   12.669578] systemd[1]: Detected virtualization qemu.^M
[   12.669956] systemd[1]: Detected architecture x86-64.^M
^M
Welcome to ^[[1mDebian GNU/Linux 12 (bookworm)^[[0m!^M
^M^M
[   12.680118] systemd[1]: Hostname set to <metaos>.^M
[   14.499542] I/O error, dev fd0, sector 0 op 0x0:(READ) flags 0x0 phys_seg 1 prio class 2^M
[   14.499999] floppy: error 10 while reading block 0^M
[   15.786095] systemd[1]: Condition check resulted in -.slice - Root Slice being skipped.^M
[   15.791602] systemd[1]: Condition check resulted in system.slice - System Slice being skipped.^M
[   15.803325] systemd[1]: Queued start job for default target graphical.target.^M
[   15.857178] systemd[1]: Created slice system-getty.slice - Slice /system/getty.^M
[^[[0;32m  OK  ^[[0m] Created slice ^[[0;1;39msystem-getty.slice^[[0m - Slice /system/getty.^M^M
[   15.876361] systemd[1]: Created slice system-modprobe.slice - Slice /system/modprobe.^M
[^[[0;32m  OK  ^[[0m] Created slice ^[[0;1;39msystem-modpr‚M-^@¶lice^[[0m - Slice /system/modprobe.^M^M
[   15.881078] systemd[1]: Created slice system-serial\x2dgetty.slice - Slice /system/serial-getty.^M
[^[[0;32m  OK  ^[[0m] Created slice ^[[0;1;39msystem-seria‚M-^@¶^[[0m - Slice /system/serial-getty.^M^M
[   15.885295] systemd[1]: Created slice system-systemd\x2dgrowfs.slice - Slice /system/systemd-growfs.^M
[^[[0;32m  OK  ^[[0m] Created slice ^[[0;1;39msystem-syste‚M-^@¶0m - Slice /system/systemd-growfs.^M^M
[   15.963463] systemd[1]: Created slice user.slice - User and Session Slice.^M
[^[[0;32m  OK  ^[[0m] Created slice ^[[0;1;39muser.slice^[[0m - User and Session Slice.^M^M
[   15.978574] systemd[1]: Started systemd-ask-password-console.path - Dispatch Password Requests to Console Directory Watch.^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39msystemd-ask-passwo‚M-^@¶quests to Console Directory Watch.^M^M
[   15.982296] systemd[1]: Started systemd-ask-password-wall.path - Forward Password Requests to Wall Directory Watch.^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39msystemd-ask-passwo‚M-^@¶ Requests to Wall Directory Watch.^M^M
[   15.988460] systemd[1]: Set up automount proc-sys-fs-binfmt_misc.automount - Arbitrary Executable File Formats File System Automount Point.^M
[^[[0;32m  OK  ^[[0m] Set up automount ^[[0;1;39mproc-sys-‚M-^@¶rmats File System Automount Point.^M^M
[   15.990824] systemd[1]: Expecting device dev-disk-by\x2dpartuuid-52c8442f\x2d5ff2\x2d4a03\x2d926e\x2d7f504550f77d.device - /dev/disk/by-partuuid/52c8442f-5ff2-4a03-926e-7f504550f77d...^M
         Expecting device ^[[0;1;39mdev-disk-‚M-^@¶42f-5ff2-4a03-926e-7f504550f77d...^M^M
[   15.993441] systemd[1]: Expecting device dev-ttyS0.device - /dev/ttyS0...^M
         Expecting device ^[[0;1;39mdev-ttyS0.device^[[0m - /dev/ttyS0...^M^M
[   15.994824] systemd[1]: Reached target cryptsetup.target - Local Encrypted Volumes.^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mcryptsetup.‚M-^@¶get^[[0m - Local Encrypted Volumes.^M^M
[   15.997604] systemd[1]: Reached target integritysetup.target - Local Integrity Protected Volumes.^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mintegrityse‚M-^@¶Local Integrity Protected Volumes.^M^M
[   15.998885] systemd[1]: Reached target paths.target - Path Units.^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mpaths.target^[[0m - Path Units.^M^M
[   16.000723] systemd[1]: Reached target remote-fs.target - Remote File Systems.^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mremote-fs.target^[[0m - Remote File Systems.^M^M
[   16.001956] systemd[1]: Reached target slices.target - Slice Units.^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mslices.target^[[0m - Slice Units.^M^M
[   16.002951] systemd[1]: Reached target swap.target - Swaps.^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mswap.target^[[0m - Swaps.^M^M
[   16.004774] systemd[1]: Reached target veritysetup.target - Local Verity Protected Volumes.^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mveritysetup‚M-^@¶ - Local Verity Protected Volumes.^M^M
[   16.010111] systemd[1]: Listening on systemd-fsckd.socket - fsck to fsckd communication Socket.^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39msystemd-fsckd‚M-^@¶sck to fsckd communication Socket.^M^M
[   16.013781] systemd[1]: Listening on systemd-initctl.socket - initctl Compatibility Named Pipe.^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39msystemd-initc‚M-^@¶ initctl Compatibility Named Pipe.^M^M
[   16.021396] systemd[1]: Listening on systemd-journald-audit.socket - Journal Audit Socket.^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39msystemd-journ‚M-^@¶socket^[[0m - Journal Audit Socket.^M^M
[   16.026076] systemd[1]: Listening on systemd-journald-dev-log.socket - Journal Socket (/dev/log).^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39msystemd-journ‚M-^@¶t^[[0m - Journal Socket (/dev/log).^M^M
[   16.036466] systemd[1]: Listening on systemd-journald.socket - Journal Socket.^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39msystemd-journald.socket^[[0m - Journal Socket.^M^M
[   16.040125] systemd[1]: Listening on systemd-networkd.socket - Network Service Netlink Socket.^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39msystemd-netwo‚M-^@¶ - Network Service Netlink Socket.^M^M
[   16.042762] systemd[1]: Listening on systemd-udevd-control.socket - udev Control Socket.^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39msystemd-udevd‚M-^@¶.socket^[[0m - udev Control Socket.^M^M
[   16.052188] systemd[1]: Listening on systemd-udevd-kernel.socket - udev Kernel Socket.^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39msystemd-udevd‚M-^@¶l.socket^[[0m - udev Kernel Socket.^M^M
[   16.073862] systemd[1]: Mounting dev-hugepages.mount - Huge Pages File System...^M
         Mounting ^[[0;1;39mdev-hugepages.mount^[[0m - Huge Pages File System...^M^M
[   16.128900] systemd[1]: Mounting dev-mqueue.mount - POSIX Message Queue File System...^M
         Mounting ^[[0;1;39mdev-mqueue.mount^[‚M-^@¶POSIX Message Queue File System...^M^M
[   16.185645] systemd[1]: Mounting sys-kernel-debug.mount - Kernel Debug File System...^M
         Mounting ^[[0;1;39msys-kernel-debug.‚M-^@¶^[[0m - Kernel Debug File System...^M^M
[   16.229119] systemd[1]: Mounting sys-kernel-tracing.mount - Kernel Trace File System...^M
         Mounting ^[[0;1;39msys-kernel-tracin‚M-^@¶^[[0m - Kernel Trace File System...^M^M
[   16.283043] systemd[1]: Starting kmod-static-nodes.service - Create List of Static Device Nodes...^M
         Starting ^[[0;1;39mkmod-static-nodes‚M-^@¶ate List of Static Device Nodes...^M^M
[   16.338050] systemd[1]: Starting modprobe@configfs.service - Load Kernel Module configfs...^M
         Starting ^[[0;1;39mmodprobe@configfs‚M-^@¶m - Load Kernel Module configfs...^M^M
[   16.420954] systemd[1]: Starting modprobe@dm_mod.service - Load Kernel Module dm_mod...^M
         Starting ^[[0;1;39mmodprobe@dm_mod.s‚M-^@¶[0m - Load Kernel Module dm_mod...^M^M
[   16.482876] systemd[1]: Starting modprobe@drm.service - Load Kernel Module drm...^M
         Starting ^[[0;1;39mmodprobe@drm.service^[[0m - Load Kernel Module drm...^M^M
[   16.573450] systemd[1]: Starting modprobe@efi_pstore.service - Load Kernel Module efi_pstore...^M
         Starting ^[[0;1;39mmodprobe@efi_psto‚M-^@¶- Load Kernel Module efi_pstore...^M^M
[   16.650779] systemd[1]: Starting modprobe@fuse.service - Load Kernel Module fuse...^M
         Starting ^[[0;1;39mmodprobe@fuse.ser‚M-^@¶e^[[0m - Load Kernel Module fuse...^M^M
[   16.655230] random: crng init done^M
[   16.739133] systemd[1]: Starting modprobe@loop.service - Load Kernel Module loop...^M
         Starting ^[[0;1;39mmodprobe@loop.ser‚M-^@¶e^[[0m - Load Kernel Module loop...^M^M
[   16.761675] systemd[1]: netplan-ovs-cleanup.service - OpenVSwitch configuration for cleanup was skipped because of an unmet condition check (ConditionFileIsExecutable=/usr/bin/ovs-vsctl).^M
[   16.819983] device-mapper: core: CONFIG_IMA_DISABLE_HTABLE is disabled. Duplicate IMA measurements will not be recorded in the IMA log.^M
[   16.820873] device-mapper: uevent: version 1.0.3^M
[   16.826090] device-mapper: ioctl: 4.47.0-ioctl (2022-07-28) initialised: dm-devel@redhat.com^M
[   16.842910] systemd[1]: Starting systemd-fsck-root.service - File System Check on Root Device...^M
         Starting ^[[0;1;39msystemd-fsck-root‚M-^@¶ile System Check on Root Device...^M^M
[   17.058668] systemd[1]: Starting systemd-journald.service - Journal Service...^M
         Starting ^[[0;1;39msystemd-journald.service^[[0m - Journal Service...^M^M
[   17.102446] fuse: init (API version 7.38)^M
[   17.119755] loop: module loaded^M
[   17.165048] systemd[1]: Starting systemd-modules-load.service - Load Kernel Modules...^M
         Starting ^[[0;1;39msystemd-modules-l‚M-^@¶rvice^[[0m - Load Kernel Modules...^M^M
[   17.247216] systemd[1]: Starting systemd-network-generator.service - Generate network units from Kernel command line...^M
         Starting ^[[0;1;39msystemd-network-g‚M-^@¶ units from Kernel command line...^M^M
[   17.334510] systemd[1]: Starting systemd-udev-trigger.service - Coldplug All udev Devices...^M
         Starting ^[[0;1;39msystemd-udev-trig‚M-^@¶[0m - Coldplug All udev Devices...^M^M
[   17.550374] ACPI: bus type drm_connector registered^M
[   17.554755] systemd[1]: Mounted dev-hugepages.mount - Huge Pages File System.^M
[^[[0;32m  OK  ^[[0m] Mounted ^[[0;1;39mdev-hugepages.mount^[[0m - Huge Pages File System.^M^M
[   17.608675] systemd[1]: Mounted dev-mqueue.mount - POSIX Message Queue File System.^M
[^[[0;32m  OK  ^[[0m] Mounted ^[[0;1;39mdev-mqueue.mount^[[‚M-^@¶- POSIX Message Queue File System.^M^M
[   17.629433] systemd[1]: Mounted sys-kernel-debug.mount - Kernel Debug File System.^M
[^[[0;32m  OK  ^[[0m] Mounted ^[[0;1;39msys-kernel-debug.m‚M-^@¶nt^[[0m - Kernel Debug File System.^M^M
[   17.642395] systemd[1]: Mounted sys-kernel-tracing.mount - Kernel Trace File System.^M
[^[[0;32m  OK  ^[[0m] Mounted ^[[0;1;39msys-kernel-tracing‚M-^@¶nt^[[0m - Kernel Trace File System.^M^M
[   17.695075] systemd[1]: Finished kmod-static-nodes.service - Create List of Static Device Nodes.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39mkmod-static-nodes‚M-^@¶reate List of Static Device Nodes.^M^M
[   17.724680] systemd[1]: modprobe@configfs.service: Deactivated successfully.^M
[   17.735548] systemd[1]: Finished modprobe@configfs.service - Load Kernel Module configfs.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39mmodprobe@configfs‚M-^@¶[0m - Load Kernel Module configfs.^M^M
[   17.770680] systemd[1]: modprobe@dm_mod.service: Deactivated successfully.^M
[   17.781655] systemd[1]: Finished modprobe@dm_mod.service - Load Kernel Module dm_mod.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39mmodprobe@dm_mod.s‚M-^@¶e^[[0m - Load Kernel Module dm_mod.^M^M
[   17.794793] systemd[1]: modprobe@drm.service: Deactivated successfully.^M
[   17.808790] systemd[1]: Finished modprobe@drm.service - Load Kernel Module drm.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39mmodprobe@drm.service^[[0m - Load Kernel Module drm.^M^M
[   17.825500] systemd[1]: modprobe@efi_pstore.service: Deactivated successfully.^M
[   17.838750] systemd[1]: Finished modprobe@efi_pstore.service - Load Kernel Module efi_pstore.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39mmodprobe@efi_psto‚M-^@¶m - Load Kernel Module efi_pstore.^M^M
[   17.852552] systemd[1]: modprobe@fuse.service: Deactivated successfully.^M
[   17.871283] systemd[1]: Finished modprobe@fuse.service - Load Kernel Module fuse.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39mmodprobe@fuse.service^[[0m - Load Kernel Module fuse.^M^M
[   17.875511] systemd[1]: modprobe@loop.service: Deactivated successfully.^M
[   17.884950] systemd[1]: Finished modprobe@loop.service - Load Kernel Module loop.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39mmodprobe@loop.service^[[0m - Load Kernel Module loop.^M^M
[   17.900103] systemd[1]: Finished systemd-fsck-root.service - File System Check on Root Device.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-fsck-root‚M-^@¶ File System Check on Root Device.^M^M
[   17.926409] systemd[1]: Finished systemd-modules-load.service - Load Kernel Modules.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-modules-l‚M-^@¶service^[[0m - Load Kernel Modules.^M^M
[   17.935397] systemd[1]: Finished systemd-network-generator.service - Generate network units from Kernel command line.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-network-g‚M-^@¶rk units from Kernel command line.^M^M
[   18.009113] systemd[1]: Mounting sys-fs-fuse-connections.mount - FUSE Control File System...^M
         Mounting ^[[0;1;39msys-fs-fuse-conne‚M-^@¶^[[0m - FUSE Control File System...^M^M
[   18.084791] systemd[1]: Mounting sys-kernel-config.mount - Kernel Configuration File System...^M
         Mounting ^[[0;1;39msys-kernel-config‚M-^@¶ernel Configuration File System...^M^M
[   18.192454] systemd[1]: Started systemd-fsckd.service - File System Check Daemon to report status.^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39msystemd-fsckd.serv‚M-^@¶tem Check Daemon to report status.^M^M
[   18.250385] systemd[1]: Starting systemd-remount-fs.service - Remount Root and Kernel File Systems...^M
         Starting ^[[0;1;39msystemd-remount-f‚M-^@¶nt Root and Kernel File Systems...^M^M
[   18.269836] systemd[1]: systemd-repart.service - Repartition Root Disk was skipped because no trigger condition checks were met.^M
[   18.352225] systemd[1]: Starting systemd-sysctl.service - Apply Kernel Variables...^M
         Starting ^[[0;1;39msystemd-sysctl.se‚M-^@¶ce^[[0m - Apply Kernel Variables...^M^M
[   18.660318] systemd[1]: Mounted sys-fs-fuse-connections.mount - FUSE Control File System.^M
[^[[0;32m  OK  ^[[0m] Mounted ^[[0;1;39msys-fs-fuse-connec‚M-^@¶nt^[[0m - FUSE Control File System.^M^M
[   18.673096] systemd[1]: Mounted sys-kernel-config.mount - Kernel Configuration File System.^M
[^[[0;32m  OK  ^[[0m] Mounted ^[[0;1;39msys-kernel-config.‚M-^@¶ Kernel Configuration File System.^M^M
[   18.752576] systemd[1]: Finished systemd-sysctl.service - Apply Kernel Variables.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-sysctl.service^[[0m - Apply Kernel Variables.^M^M
[   18.769119] EXT4-fs (sda1): re-mounted. Quota mode: none.^M
[   18.839886] systemd[1]: Finished systemd-remount-fs.service - Remount Root and Kernel File Systems.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-remount-f‚M-^@¶ount Root and Kernel File Systems.^M^M
[   18.886645] systemd[1]: Starting cloud-init-local.service - Initial cloud-init job (pre-networking)...^M
         Starting ^[[0;1;39mcloud-init-local.‚M-^@¶cloud-init job (pre-networking)...^M^M
[   18.901761] systemd[1]: systemd-firstboot.service - First Boot Wizard was skipped because of an unmet condition check (ConditionFirstBoot=yes).^M
[   18.967918] systemd[1]: Starting systemd-growfs@-.service - Grow File System on /...^M
         Starting ^[[0;1;39msystemd-growfs@-.‚M-^@¶ice^[[0m - Grow File System on /...^M^M
[   18.980284] systemd[1]: systemd-pstore.service - Platform Persistent Storage Archival was skipped because of an unmet condition check (ConditionDirectoryNotEmpty=/sys/fs/pstore).^M
[   19.069287] systemd[1]: Starting systemd-random-seed.service - Load/Save Random Seed...^M
         Starting ^[[0;1;39msystemd-random-se‚M-^@¶ice^[[0m - Load/Save Random Seed...^M^M
[   19.177344] systemd[1]: Starting systemd-sysusers.service - Create System Users...^M
         Starting ^[[0;1;39msystemd-sysusers.‚M-^@¶rvice^[[0m - Create System Users...^M^M
[   19.362867] systemd[1]: Started systemd-journald.service - Journal Service.^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39msystemd-journald.service^[[0m - Journal Service.^M^M
         Starting ^[[0;1;39msystemd-journal-f‚M-^@¶h Journal to Persistent Storage...^M^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-random-se‚M-^@¶rvice^[[0m - Load/Save Random Seed.^M^M
[   19.725710] EXT4-fs (sda1): resizing filesystem from 3375099 to 3375099 blocks^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-sysusers.service^[[0m - Create System Users.^M^M
         Starting ^[[0;1;39msystemd-tmpfiles-‚M-^@¶ate Static Device Nodes in /dev...^M^M
[   19.965047] systemd-journald[217]: Received client request to flush runtime journal.^M
[   20.007374] systemd-journald[217]: File /var/log/journal/dbf26591207c4e55b162bca49f347715/system.journal corrupted or uncleanly shut down, renaming and replacing.^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-growfs@-.‚M-^@¶rvice^[[0m - Grow File System on /.^M^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-tmpfiles-‚M-^@¶reate Static Device Nodes in /dev.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mlocal-fs-pr‚M-^@¶reparation for Local File Systems.^M^M
         Starting ^[[0;1;39msystemd-udevd.ser‚M-^@¶ger for Device Events and Files...^M^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-journal-f‚M-^@¶ush Journal to Persistent Storage.^M^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-udev-trig‚M-^@¶e^[[0m - Coldplug All udev Devices.^M^M
[   21.644064] hrtimer: interrupt took 12348073 ns^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39msystemd-udevd.serv‚M-^@¶nager for Device Events and Files.^M^M
[   25.718197] sd 0:0:0:0: Attached scsi generic sg0 type 0^M
[   25.746127] sr 1:0:0:0: Attached scsi generic sg1 type 5^M
[^[[0;32m  OK  ^[[0m] Found device ^[[0;1;39mdev-ttyS0.device^[[0m - /dev/ttyS0.^M^M
[   26.979328] input: Power Button as /devices/LNXSYSTM:00/LNXPWRBN:00/input/input3^M
[   27.047407] ACPI: button: Power Button [PWRF]^M
[   27.526274] parport_pc 00:03: reported by Plug and Play ACPI^M
[   27.539990] parport0: PC-style at 0x378, irq 7 [PCSPP,TRISTATE]^M
[   28.547377] ppdev: user-space parallel port driver^M
[   28.576474] bochs-drm 0000:00:02.0: vgaarb: deactivate vga console^M
[   28.582137] Console: switching to colour dummy device 80x25^M
[   28.589066] [drm] Found bochs VGA, ID 0xb0c5.^M
[   28.589334] [drm] Framebuffer size 16384 kB @ 0xfd000000, mmio @ 0xfebf0000.^M
[   28.601798] [drm] Found EDID data blob.^M
[   28.620822] [drm] Initialized bochs-drm 1.0.0 20130925 for 0000:00:02.0 on minor 0^M
[   28.680153] fbcon: bochs-drmdrmfb (fb0) is primary device^M
[   28.722812] Console: switching to colour frame buffer device 160x50^M
[   28.776529] bochs-drm 0000:00:02.0: [drm] fb0: bochs-drmdrmfb frame buffer device^M
[^[[0;32m  OK  ^[[0m] Found device ^[[0;1;39mdev-disk-by\x‚M-^@¶77d.device^[[0m - QEMU_HARDDISK 15.^M^M
         Mounting ^[[0;1;39mboot-efi.mount^[[0m - /boot/efi...^M^M
[   29.836567] kvm: Nested Virtualization enabled^M
[   29.837039] SVM: kvm: Nested Paging disabled^M
[   29.838428] SVM: PMU virtualization is disabled^M
[   29.848052] FAT-fs (sda15): Volume was not properly unmounted. Some data may be corrupt. Please run fsck.^M
[^[[0;32m  OK  ^[[0m] Mounted ^[[0;1;39mboot-efi.mount^[[0m - /boot/efi.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mlocal-fs.target^[[0m - Local File Systems.^M^M
         Starting ^[[0;1;39mapparmor.service^[[0m - Load AppArmor profiles...^M^M
         Starting ^[[0;1;39msystemd-binfmt.se‚M-^@¶et Up Additional Binary Formats...^M^M
[   30.171031] powernow_k8: Power state transitions not supported^M
         Starting ^[[0;1;39msystemd-tmpfiles-‚M-^@¶te System Files and Directories...^M^M
         Mounting ^[[0;1;39mproc-sys-fs-binfm‚M-^@¶utable File Formats File System...^M^M
[^[[0;32m  OK  ^[[0m] Mounted ^[[0;1;39mproc-sys-fs-binfmt‚M-^@¶ecutable File Formats File System.^M^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-binfmt.se‚M-^@¶ Set Up Additional Binary Formats.^M^M
[   31.025332] audit: type=1400 audit(1793635961.071:2): apparmor="STATUS" operation="profile_load" profile="unconfined" name="lsb_release" pid=277 comm="apparmor_parser"^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-tmpfiles-‚M-^@¶eate System Files and Directories.^M^M
         Starting ^[[0;1;39msystemd-resolved.‚M-^@¶e^[[0m - Network Name Resolution...^M^M
         Starting ^[[0;1;39msystemd-timesyncd‚M-^@¶ - Network Time Synchronization...^M^M
[   31.237359] audit: type=1400 audit(1793635961.279:3): apparmor="STATUS" operation="profile_load" profile="unconfined" name="nvidia_modprobe" pid=278 comm="apparmor_parser"^M
[   31.238201] audit: type=1400 audit(1793635961.279:4): apparmor="STATUS" operation="profile_load" profile="unconfined" name="nvidia_modprobe//kmod" pid=278 comm="apparmor_parser"^M
         Starting ^[[0;1;39msystemd-update-ut‚M-^@¶rd System Boot/Shutdown in UTMP...^M^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-update-ut‚M-^@¶cord System Boot/Shutdown in UTMP.^M^M
[   32.004460] audit: type=1400 audit(1793635962.051:5): apparmor="STATUS" operation="profile_load" profile="unconfined" name="/usr/lib/NetworkManager/nm-dhcp-client.action" pid=281 comm="apparmor_parser"^M
[   32.005399] audit: type=1400 audit(1793635962.051:6): apparmor="STATUS" operation="profile_load" profile="unconfined" name="/usr/lib/NetworkManager/nm-dhcp-helper" pid=281 comm="apparmor_parser"^M
[   32.006235] audit: type=1400 audit(1793635962.051:7): apparmor="STATUS" operation="profile_load" profile="unconfined" name="/usr/lib/connman/scripts/dhclient-script" pid=281 comm="apparmor_parser"^M
[   32.010369] audit: type=1400 audit(1793635962.051:8): apparmor="STATUS" operation="profile_load" profile="unconfined" name="/{,usr/}sbin/dhclient" pid=281 comm="apparmor_parser"^M
[   32.204944] audit: type=1400 audit(1793635962.251:9): apparmor="STATUS" operation="profile_load" profile="unconfined" name="/usr/bin/man" pid=283 comm="apparmor_parser"^M
[   32.205829] audit: type=1400 audit(1793635962.251:10): apparmor="STATUS" operation="profile_load" profile="unconfined" name="man_filter" pid=283 comm="apparmor_parser"^M
[   32.239626] audit: type=1400 audit(1793635962.251:11): apparmor="STATUS" operation="profile_load" profile="unconfined" name="man_groff" pid=283 comm="apparmor_parser"^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39mapparmor.service^[[0m - Load AppArmor profiles.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39msystemd-timesyncd.‚M-^@¶0m - Network Time Synchronization.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mtime-set.target^[[0m - System Time Set.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39msystemd-resolved.s‚M-^@¶ice^[[0m - Network Name Resolution.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mnss-lookup.‚M-^@¶m - Host and Network Name Lookups.^M^M
[   37.174835] cloud-init[289]: Cloud-init v. 22.4.2 running 'init-local' at Mon, 02 Nov 2026 16:12:46 +0000. Up 36.95 seconds.^M
[   37.331309] I/O error, dev fd0, sector 0 op 0x0:(READ) flags 0x0 phys_seg 1 prio class 2^M
[   37.337846] floppy: error 10 while reading block 0^M
[   37.495857] I/O error, dev fd0, sector 0 op 0x0:(READ) flags 0x0 phys_seg 1 prio class 2^M
[   37.501411] floppy: error 10 while reading block 0^M
[   37.588522] I/O error, dev fd0, sector 0 op 0x0:(READ) flags 0x0 phys_seg 1 prio class 2^M
[   37.596624] floppy: error 10 while reading block 0^M
[   37.703094] I/O error, dev fd0, sector 0 op 0x0:(READ) flags 0x0 phys_seg 1 prio class 2^M
[   37.707318] floppy: error 10 while reading block 0^M
[   37.795447] I/O error, dev fd0, sector 0 op 0x0:(READ) flags 0x0 phys_seg 1 prio class 2^M
[   37.799765] floppy: error 10 while reading block 0^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39mcloud-init-local.‚M-^@¶l cloud-init job (pre-networking).^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mnetwork-pre‚M-^@¶get^[[0m - Preparation for Network.^M^M
         Starting ^[[0;1;39msystemd-networkd.‚M-^@¶ice^[[0m - Network Configuration...^M^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39msystemd-rfkil‚M-^@¶l Switch Status /dev/rfkill Watch.^M^M
[   42.180514] cfg80211: Loading compiled-in X.509 certificates for regulatory database^M
[   42.199508] cfg80211: Loaded X.509 cert 'benh@debian.org: 577e021cb980e0e820821ba7b54b4961b8b4fadf'^M
[   42.209346] cfg80211: Loaded X.509 cert 'romain.perier@gmail.com: 3abbc6ec146e09d1b6016ab9d6cf71dd233f0328'^M
[   42.220481] cfg80211: Loaded X.509 cert 'sforshee: 00b28ddf47aef9cea7'^M
[   42.228506] cfg80211: Loaded X.509 cert 'wens: 61c038651aabdcf94bd0ac7ff06c7248db18c600'^M
[   42.237907] platform regulatory.0: firmware: failed to load regulatory.db (-2)^M
[   42.242519] firmware_class: See https://wiki.debian.org/Firmware for information about missing firmware^M
[   42.259003] platform regulatory.0: firmware: failed to load regulatory.db (-2)^M
[   42.263366] platform regulatory.0: Direct firmware load for regulatory.db failed with error -2^M
[   42.286422] cfg80211: failed to load regulatory.db^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39msystemd-networkd.service^[[0m - Network Configuration.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mnetwork.target^[[0m - Network.^M^M
         Starting ^[[0;1;39msystemd-networkd-‚M-^@¶it for Network to be Configured...^M^M
[   42.525421] e1000: ens3 NIC Link is Up 1000 Mbps Full Duplex, Flow Control: RX^M
[   42.540020] IPv6: ADDRCONF(NETDEV_CHANGE): ens3: link becomes ready^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-networkd-‚M-^@¶Wait for Network to be Configured.^M^M
         Starting ^[[0;1;39mcloud-init.servic‚M-^@¶ job (metadata service crawler)...^M^M
[   47.811088] cloud-init[325]: Cloud-init v. 22.4.2 running 'init' at Mon, 02 Nov 2026 16:13:35 +0000. Up 47.63 seconds.^M
[   47.934960] cloud-init[325]: ci-info: ++++++++++++++++++++++++++++++++++++++Net device info++++++++++++++++++++++++++++++++++++++^M
[   47.936717] cloud-init[325]: ci-info: +--------+------+----------------------------+---------------+--------+-------------------+^M
[   47.942949] cloud-init[325]: ci-info: | Device |  Up  |          Address           |      Mask     | Scope  |     Hw-Address    |^M
[   47.944279] cloud-init[325]: ci-info: +--------+------+----------------------------+---------------+--------+-------------------+^M
[   47.946031] cloud-init[325]: ci-info: |  ens3  | True |         10.0.2.15          | 255.255.255.0 | global | 52:54:00:12:34:56 |^M
[   47.950221] cloud-init[325]: ci-info: |  ens3  | True | fec0::5054:ff:fe12:3456/64 |       .       |  site  | 52:54:00:12:34:56 |^M
[   47.951407] cloud-init[325]: ci-info: |  ens3  | True | fe80::5054:ff:fe12:3456/64 |       .       |  link  | 52:54:00:12:34:56 |^M
[   47.953596] cloud-init[325]: ci-info: |   lo   | True |         127.0.0.1          |   255.0.0.0   |  host  |         .         |^M
[   47.958844] cloud-init[325]: ci-info: |   lo   | True |          ::1/128           |       .       |  host  |         .         |^M
[   47.960107] cloud-init[325]: ci-info: +--------+------+----------------------------+---------------+--------+-------------------+^M
[   47.966351] cloud-init[325]: ci-info: ++++++++++++++++++++++++++++Route IPv4 info+++++++++++++++++++++++++++++^M
[   47.967564] cloud-init[325]: ci-info: +-------+-------------+----------+-----------------+-----------+-------+^M
[   47.968465] cloud-init[325]: ci-info: | Route | Destination | Gateway  |     Genmask     | Interface | Flags |^M
[   47.970324] cloud-init[325]: ci-info: +-------+-------------+----------+-----------------+-----------+-------+^M
[   47.973964] cloud-init[325]: ci-info: |   0   |   0.0.0.0   | 10.0.2.2 |     0.0.0.0     |    ens3   |   UG  |^M
[   47.977692] cloud-init[325]: ci-info: |   1   |   10.0.2.0  | 0.0.0.0  |  255.255.255.0  |    ens3   |   U   |^M
[   47.978996] cloud-init[325]: ci-info: |   2   |   10.0.2.2  | 0.0.0.0  | 255.255.255.255 |    ens3   |   UH  |^M
[   47.983748] cloud-init[325]: ci-info: |   3   |   10.0.2.3  | 0.0.0.0  | 255.255.255.255 |    ens3   |   UH  |^M
[   47.985405] cloud-init[325]: ci-info: +-------+-------------+----------+-----------------+-----------+-------+^M
[   47.991100] cloud-init[325]: ci-info: +++++++++++++++++++Route IPv6 info+++++++++++++++++++^M
[   47.992295] cloud-init[325]: ci-info: +-------+-------------+---------+-----------+-------+^M
[   47.994002] cloud-init[325]: ci-info: | Route | Destination | Gateway | Interface | Flags |^M
[   48.002690] cloud-init[325]: ci-info: +-------+-------------+---------+-----------+-------+^M
[   48.004002] cloud-init[325]: ci-info: |   0   |  fe80::/64  |    ::   |    ens3   |   U   |^M
[   48.004797] cloud-init[325]: ci-info: |   1   |  fec0::/64  |    ::   |    ens3   |   Ue  |^M
[   48.009764] cloud-init[325]: ci-info: |   2   |     ::/0    | fe80::2 |    ens3   |  UGe  |^M
[   48.010798] cloud-init[325]: ci-info: |   4   |    local    |    ::   |    ens3   |   U   |^M
[   48.011698] cloud-init[325]: ci-info: |   5   |    local    |    ::   |    ens3   |   U   |^M
[   48.012467] cloud-init[325]: ci-info: |   6   |  multicast  |    ::   |    ens3   |   U   |^M
[   48.013214] cloud-init[325]: ci-info: +-------+-------------+---------+-----------+-------+^M
[   66.194269] cloud-init[325]: Generating public/private rsa key pair.^M
[   66.199212] cloud-init[325]: Your identification has been saved in /etc/ssh/ssh_host_rsa_key^M
[   66.207197] cloud-init[325]: Your public key has been saved in /etc/ssh/ssh_host_rsa_key.pub^M
[   66.208657] cloud-init[325]: The key fingerprint is:^M
[   66.209500] cloud-init[325]: SHA256:SZElRgxX6SOFPG+AWxqfsDPF9qE4mozG8W0z5NVl2us root@metaos^M
[   66.215616] cloud-init[325]: The key's randomart image is:^M
[   66.217692] cloud-init[325]: +---[RSA 3072]----+^M
[   66.218918] cloud-init[325]: |      .B*=o.     |^M
[   66.222089] cloud-init[325]: |      +o%o+ o    |^M
[   66.225853] cloud-init[325]: |       %.@ *     |^M
[   66.226975] cloud-init[325]: |  .   X.*.O .    |^M
[   66.230495] cloud-init[325]: | . = * =So . .   |^M
[   66.237430] cloud-init[325]: |  + = *     .    |^M
[   66.244587] cloud-init[325]: | .   . o   .     |^M
[   66.251437] cloud-init[325]: |            E    |^M
[   66.252636] cloud-init[325]: |                 |^M
[   66.257956] cloud-init[325]: +----[SHA256]-----+^M
[   66.272383] cloud-init[325]: Generating public/private dsa key pair.^M
[   66.276700] cloud-init[325]: Your identification has been saved in /etc/ssh/ssh_host_dsa_key^M
[   66.280693] cloud-init[325]: Your public key has been saved in /etc/ssh/ssh_host_dsa_key.pub^M
[   66.283613] cloud-init[325]: The key fingerprint is:^M
[   66.288074] cloud-init[325]: SHA256:FnaNuHVbA7a/8v+ALKDFaPDSVaHQfquhVR/LytcaxaE root@metaos^M
[   66.299081] cloud-init[325]: The key's randomart image is:^M
[   66.300309] cloud-init[325]: +---[DSA 1024]----+^M
[   66.322773] cloud-init[325]: |      ..  o.o    |^M
[   66.337401] cloud-init[325]: |       ..+ + o   |^M
[   66.341214] cloud-init[325]: |    .  .* + + +  |^M
[   66.347503] cloud-init[325]: |     + =.=o..* o |^M
[   66.374156] cloud-init[325]: |    . = So +Eo+  |^M
[   66.378680] cloud-init[325]: |     o +o...+o . |^M
[   66.386377] cloud-init[325]: |      .o +..=.o  |^M
[   66.412411] cloud-init[325]: |      . . o..+.. |^M
[   66.496990] cloud-init[325]: |           .....+|^M
[   66.558028] cloud-init[325]: +----[SHA256]-----+^M
[   66.559465] cloud-init[325]: Generating public/private ecdsa key pair.^M
[   66.561463] cloud-init[325]: Your identification has been saved in /etc/ssh/ssh_host_ecdsa_key^M
[   66.563775] cloud-init[325]: Your public key has been saved in /etc/ssh/ssh_host_ecdsa_key.pub^M
[   66.567758] cloud-init[325]: The key fingerprint is:^M
[   66.569161] cloud-init[325]: SHA256:JuzsL3ix+j3HVGP794+vUSpf2kEYbNdYTqabV2l+mWQ root@metaos^M
[   66.571135] cloud-init[325]: The key's randomart image is:^M
[   66.575327] cloud-init[325]: +---[ECDSA 256]---+^M
[   66.576519] cloud-init[325]: |                +|^M
[   66.582230] cloud-init[325]: |            .  Bo|^M
[   66.583766] cloud-init[325]: |             +oE+|^M
[   66.584587] cloud-init[325]: |     .      = Oo+|^M
[   66.591678] cloud-init[325]: |      o S  o +o=+|^M
[   66.593108] cloud-init[325]: |     o.o  . . .+.|^M
[   66.598364] cloud-init[325]: |     .oo o  ..o..|^M
[   66.599496] cloud-init[325]: |    ..+.. o  o.*o|^M
[   66.603674] cloud-init[325]: |    .+oooo    =+B|^M
[   66.604949] cloud-init[325]: +----[SHA256]-----+^M
[   66.615759] cloud-init[325]: Generating public/private ed25519 key pair.^M
[   66.616943] cloud-init[325]: Your identification has been saved in /etc/ssh/ssh_host_ed25519_key^M
[   66.623319] cloud-init[325]: Your public key has been saved in /etc/ssh/ssh_host_ed25519_key.pub^M
[   66.631492] cloud-init[325]: The key fingerprint is:^M
[   66.632593] cloud-init[325]: SHA256:DO3r8t7yDbRmBWI/OaHJNz5WDjWaV4FwHx4nust7sUc root@metaos^M
[   66.633432] cloud-init[325]: The key's randomart image is:^M
[   66.634077] cloud-init[325]: +--[ED25519 256]--+^M
[   66.635008] cloud-init[325]: |          ....= .|^M
[   66.636980] cloud-init[325]: |       .   ..+ * |^M
[   66.643580] cloud-init[325]: |      . + o + +  |^M
[   66.644620] cloud-init[325]: |       * = B +   |^M
[   66.645345] cloud-init[325]: |        S % =    |^M
[   66.647284] cloud-init[325]: |         = % .. E|^M
[   66.648048] cloud-init[325]: |        . O +  + |^M
[   66.649940] cloud-init[325]: |      ...= + .o .|^M
[   66.654422] cloud-init[325]: |       ++oo o. . |^M
[   66.658499] cloud-init[325]: +----[SHA256]-----+^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39mcloud-init.servic‚M-^@¶it job (metadata service crawler).^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mcloud-confi‚M-^@¶t^[[0m - Cloud-config availability.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mnetwork-online.target^[[0m - Network is Online.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39msysinit.target^[[0m - System Initialization.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39mapt-daily.timer^[[0m - Daily apt download activities.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39mapt-daily-upgrade.‚M-^@¶ apt upgrade and clean activities.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39mdpkg-db-backup.tim‚M-^@¶ Daily dpkg database backup timer.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39me2scrub_all.timer^[‚M-^@¶etadata Check for All Filesystems.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39mfstrim.timer^[[0m - Discard unused blocks once a week.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39mman-db.timer^[[0m - Daily man-db regeneration.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39msystemd-tmpfiles-c‚M-^@¶ Cleanup of Temporary Directories.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mtimers.target^[[0m - Timer Units.^M^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39mcloud-init-ho‚M-^@¶ - cloud-init hotplug hook socket.^M^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39mdbus.socket^[[‚M-^@¶- D-Bus System Message Bus Socket.^M^M
[^[[0;32m  OK  ^[[0m] Listening on ^[[0;1;39muuidd.socket^[‚M-^@¶m - UUID daemon activation socket.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39msockets.target^[[0m - Socket Units.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mbasic.target^[[0m - Basic System.^M^M
         Starting ^[[0;1;39mcloud-config.serv‚M-^@¶tings specified in cloud-config...^M^M
         Starting ^[[0;1;39mdbus.service^[[0m - D-Bus System Message Bus...^M^M
         Starting ^[[0;1;39me2scrub_reap.serv‚M-^@¶e ext4 Metadata Check Snapshots...^M^M
         Starting ^[[0;1;39mssh.service^[[0m - OpenBSD Secure Shell server...^M^M
         Starting ^[[0;1;39msystemd-logind.se‚M-^@¶ice^[[0m - User Login Management...^M^M
         Starting ^[[0;1;39msystemd-user-sess‚M-^@¶vice^[[0m - Permit User Sessions...^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39mdbus.service^[[0m - D-Bus System Message Bus.^M^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39msystemd-user-sess‚M-^@¶ervice^[[0m - Permit User Sessions.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39mgetty@tty1.service^[[0m - Getty on tty1.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39mserial-getty@ttyS0‚M-^@¶rvice^[[0m - Serial Getty on ttyS0.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mgetty.target^[[0m - Login Prompts.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39mssh.service^[[0m - OpenBSD Secure Shell server.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39msystemd-logind.service^[[0m - User Login Management.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39munattended-upgrade‚M-^@¶0m - Unattended Upgrades Shutdown.^M^M
^M^M
Debian GNU/Linux 12 metaos ttyS0^M
^M
metaos login: [   74.884419] cloud-init[394]: Cloud-init v. 22.4.2 running 'modules:config' at Mon, 02 Nov 2026 16:14:00 +0000. Up 73.00 seconds.^M
[   76.000288] cloud-init[394]: Generating locales (this might take a while)...^M
[   76.179475] cloud-init[394]: Generation complete.^M
[   76.572389] systemd-journald[217]: File /var/log/journal/dbf26591207c4e55b162bca49f347715/user-1000.journal corrupted or uncleanly shut down, renaming and replacing.^M
[   77.952511] cloud-init[394]: *** update-locale: Error: invalid locale settings:  LANG=en_US.UTF-8^M
[   77.982837] cloud-init[394]: 2026-11-02 16:14:05,877 - util.py[WARNING]: Running module locale (<module 'cloudinit.config.cc_locale' from '/usr/lib/python3/dist-packages/cloudinit/config/cc_locale.py'>) failed^M
[   84.595341] cloud-init[444]: Cloud-init v. 22.4.2 running 'modules:final' at Mon, 02 Nov 2026 16:14:12 +0000. Up 84.18 seconds.^M
         Stopping ^[[0;1;39mgetty@tty1.service^[[0m - Getty on tty1...^M^M
[^[[0;32m  OK  ^[[0m] Stopped ^[[0;1;39mgetty@tty1.service^[[0m - Getty on tty1.^M^M
[^[[0;32m  OK  ^[[0m] Started ^[[0;1;39mgetty@tty1.service^[[0m - Getty on tty1.^M^M
ci-info: ++++++++++++++++++++++++++++++++++++++Authorized keys from /home/relay/.ssh/authorized_keys for user relay++++++++++++++++++++++++++++++++++++++^M
ci-info: +-------------+-------------------------------------------------------------------------------------------------+---------+--------------------+^M
ci-info: |   Keytype   |                                       Fingerprint (sha256)                                      | Options |      Comment       |^M
ci-info: +-------------+-------------------------------------------------------------------------------------------------+---------+--------------------+^M
ci-info: | ssh-ed25519 | 22:a1:01:1e:b1:e0:7e:2b:a6:ab:b3:a5:48:8d:9d:2d:42:51:c8:4a:c8:aa:5b:1c:25:1b:fe:7f:be:7f:94:1a |    -    | test@tests-MBP.lan |^M
ci-info: +-------------+-------------------------------------------------------------------------------------------------+---------+--------------------+^M
<14>Nov  2 11:14:20 cloud-init: #############################################################^M
<14>Nov  2 11:14:20 cloud-init: -----BEGIN SSH HOST KEY FINGERPRINTS-----^M
<14>Nov  2 11:14:20 cloud-init: 1024 SHA256:FnaNuHVbA7a/8v+ALKDFaPDSVaHQfquhVR/LytcaxaE root@metaos (DSA)^M
<14>Nov  2 11:14:20 cloud-init: 256 SHA256:JuzsL3ix+j3HVGP794+vUSpf2kEYbNdYTqabV2l+mWQ root@metaos (ECDSA)^M
<14>Nov  2 11:14:20 cloud-init: 256 SHA256:DO3r8t7yDbRmBWI/OaHJNz5WDjWaV4FwHx4nust7sUc root@metaos (ED25519)^M
<14>Nov  2 11:14:21 cloud-init: 3072 SHA256:SZElRgxX6SOFPG+AWxqfsDPF9qE4mozG8W0z5NVl2us root@metaos (RSA)^M
<14>Nov  2 11:14:21 cloud-init: -----END SSH HOST KEY FINGERPRINTS-----^M
<14>Nov  2 11:14:21 cloud-init: #############################################################^M
-----BEGIN SSH HOST KEY KEYS-----^M
ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBHcJHoDwyYrkWxf65qnxTP6nhalYEn+3GCy/RSxpeG5G8sb5p8OsdNoqE7wHOCkFPcboe2+bUCOvGpvk/lcOalQ= root@metaos^M
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPaVk2mjnhz+tjYv7roapfuxi1+jqbIuEb+QjjJLPIcE root@metaos^M
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC75sAR67Rg7rDwo7Hm5uCmUH0DJ2/T986hdPrqhXZyGHet2WydJhpxR7dU4zX6KJt0klkRsElxaq1YkOw6gEM7LlHtRaFgedxUeTxC8GWwAPQWvyDNnWrYgwkO9A5VJgx/JwkpDCoWJahPG/UW0pPmISvWekzXgZd1ueSoWFHFjzjNdOY4G1mwRqQhlJga8AzOKkppER5p4/1Y4KsP32bxF/4/0zzo9eMJC4ABQY4YGyRlmEneQEswJzorF3fDGkB/j6bKZE5pPuKh8Uef0CsMPSXZIi3fm+6FlkGuWQ7Pt6ERYmXUwKVEJ+9dc9aEgn/GlwoYs7wCGEIwq3czqAnFijoJvczlD7lwvKLP0F+q7HAWF8jcfePssXlsSrH6x+olfC0rCcnDEXfMFirZ0x8d3ahJcVO2i/Ncamroj8EmT5E2gjnK9hT/UxAv1zOzLqs+rmybDrJo8q+XlREI3fImbWf3S73qVfPgKf1SfYYA2Ip7880fH72ngDtAw1pHAEc= root@metaos^M
-----END SSH HOST KEY KEYS-----^M
[   93.241422] cloud-init[444]: Cloud-init v. 22.4.2 finished at Mon, 02 Nov 2026 16:14:21 +0000. Datasource DataSourceNoCloud [seed=/dev/sr0][dsmode=net].  Up 93.20 seconds^M
[^[[0;32m  OK  ^[[0m] Finished ^[[0;1;39mcloud-final.servi‚M-^@¶ Execute cloud user/final scripts.^M^M
[^[[0;32m  OK  ^[[0m] Reached target ^[[0;1;39mcloud-init.target^[[0m - Cloud-init target.^M^M
```
