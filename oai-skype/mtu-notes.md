# EPC

## interface `control`

    offload-off control
   
## interface `data`

    offload-off data
    ip link set dev data mtu 1536
	

## module `xt_GTPUSP.c` sur l'EPC

* modifier `SRC/SGW/sgw_config.c`

```
root@fit16:~/openair-cn/SRC/SGW# git diff
diff --git a/SRC/SGW/sgw_config.c b/SRC/SGW/sgw_config.c
index 4d27799..a623ee4 100644
--- a/SRC/SGW/sgw_config.c
+++ b/SRC/SGW/sgw_config.c
@@ -111,7 +111,7 @@ int sgw_config_process (sgw_config_t * config_pP)
     config_pP->local_to_eNB = false;

     system_cmd = bfromcstr("");
-    bassignformat (system_cmd, "modprobe xt_GTPUSP gtpu_enb_port=2152 gtpu_sgw_port=%u sgw_addr=\"%s\" ",
+    bassignformat (system_cmd, "modprobe xt_GTPUSP gtpu_enb_port=2152 gtpu_sgw_port=%u mtu=1536 sgw_addr=\"%s\" ",
         config_pP->udp_port_S1u_S12_S4_up, inet_ntoa (inaddr));
     sgw_system (system_cmd, SPGW_WARN_ON_ERROR, __FILE__, __LINE__);
     bdestroy(system_cmd);
```

#  enodeB

```
ifconfig data mtu 1536
offload-off data
```

