# Agent tools: the registry (OS-121)

An agent finds, trusts, and calls a tool through ONE registry.
Entry: name, version, source, license, capability set, and the
exact command surface. Trust rule: keyless tools run; anything
needing a secret declares it, and the secret never lives in the
tool's files (see WIRING.md rule card, OS-187). An agent may only
call tools in its capability set; a call outside it is refused
and recorded — same shape as the syscall refusal (OS-084).

What the human sees: the tool list with what each tool may do
and which agent may use it — plus the refusal log, which is how
you catch an agent reaching past its job.
