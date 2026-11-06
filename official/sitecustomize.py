"""Load the cluster2 Harbor egress compatibility hook only for cluster2 runs."""

import os

if os.environ.get("FM_C2_HARBOR_EGRESS_COMPAT") == "1":
    from fm_local.harbor_egress_compat import install

    install()
