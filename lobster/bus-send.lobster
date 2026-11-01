// bus-send.lobster + bus-recv.lobster (OS-173): two scripts exchange
// one message on the dev-carrier relay pattern (a channel dir; send
// appends, recv drains). Run send, then recv.

// --- send side
write_file("bus/general/0001.txt", "from lobster-agent: K5 tasks sleep and wake")
print "sent 0001.txt"
