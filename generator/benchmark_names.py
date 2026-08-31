"""Benchmark display names used by the results dashboard.

This is presentation metadata kept with the dashboard generator so tlb-results
needs no non-archive files from the tlbsim repository.
"""

FULL_NAMES = {
    "bwavess": "spec_cpu2017/603.bwaves_s",
    "bwavesr": "spec_cpu2017/503.bwaves_r",
    "bwaves": "spec_cpu2006/410.bwaves",
    "fotos": "spec_cpu2017/649.fotonik3d_s",
    "fft": "hpcc/single_fft-4GB",
    "fotor": "spec_cpu2017/549.fotonik3d_r",
    "cactusr": "spec_cpu2017/507.cactuBSSN_r",
    "cactuss": "spec_cpu2017/607.cactuBSSN_s",
    "gamess": "spec_cpu2006/416.gamess",
    "mcf": "spec_cpu2006/429.mcf",
    "xalan17": "spec_cpu2017/623.xalancbmk_s",
    "bfs": "gapbs/bfs-urand-4GB",
    "sssp": "gapbs/sssp-urand-4GB",
    "pr": "gapbs/pr-urand-4GB",
    "cc": "gapbs/cc-urand-4GB",
    "bc": "gapbs/bc-urand-4GB",
    "tc": "gapbs/tc-urand-4GB",
    "pr_u1": "gapbs/pr-urand-1GB",
    "sssp1": "gapbs/sssp-urand-1GB",
    "cactus": "spec_cpu2006/436.cactusADM",
    "bfs1": "gapbs/bfs-urand-1GB",
    "bfs2": "gapbs/bfs-urand-2GB",
    "omnet17": "spec_cpu2017/620.omnetpp_s",
    "pr_k1": "gapbs/pr-kron-1GB",
    "pr_k4": "gapbs/pr-kron-4GB",
    "xalan06": "spec_cpu2006/483.xalancbmk",
    "omnet06": "spec_cpu2006/471.omnetpp",
    "graph1": "graph500-2.1/1GB",
    "libqtm": "spec_cpu2006/462.libquantum",
    "exch2": "spec_cpu2017/648.exchange2_s",
    "rnd_acc_lcg": "hpcc/single_random_access_lcg-4GB",
    "graph4": "graph500-2.1/4GB",
    "sssp_k4": "gapbs/sssp-kron-4GB",
    "rnd_acc": "hpcc/single_random_access-4GB",
    "mcf17": "spec_cpu2017/605.mcf_s",
    "astar": "spec_cpu2006/473.astar",
    "gups": "gups/2GB",
    "bc_k4": "gapbs/bc-kron-4GB",
}


def full_name(short: str) -> str:
    try:
        return FULL_NAMES[short]
    except KeyError as exc:
        raise KeyError(f"missing dashboard benchmark name for {short!r}") from exc
