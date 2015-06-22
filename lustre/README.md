Lustre Client Ganglia Metrics

These python scripts collect lustre filesystem metric for ganglia-gmond module.

The scripts attempt to collect separate metrics for each lustre
filesystem mounted on the client. In addition to typical read/write bandwidth
metrics, the scripts also attempt to collect inode-related metrics (network RPC calls from the client to the object storage servers).

Lustre client exposes metrics through linux sysfs
(ie. /proc/fs/lustre/...).  

The "llite" metrics are high-level aggergate metrics of the underlying
storage targets. On older versions of lustre, there are known bugs in
the llite values. The "osc" metrics are lower level, offering values
for each storage target (ie. LUN) that is accessed by the client. Note
that lustre client uses local (client-side) file caching which can
affect these values.
