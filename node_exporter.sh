#!/bin/bash
version=1.5.0
os=`uname`
if [ $os == "Linux" ]
then
    wget https://github.com/prometheus/node_exporter/releases/download/v$version/node_exporter-$version.linux-amd64.tar.gz
    tar xvfz node_exporter-$version.linux-amd64.tar.gz
    cd node_exporter-$version*amd64
    ./node_exporter &
fi
cd /tmp
promfile=`hostname`.properties
ip=`ifconfig | grep "inet " |grep -v 127.0.0.1 |awk '{print $2}'`
hostname=`hostname`
comp_id=`oci-metadata |grep "Compartment OCID" |awk '{print $3}'`
/bin/cat <<EOM > $promfile
url=http://$ip:9100/metrics
namespace=dev_prometheus
nodeName=$hostnames
metricDimensions=nodeName
allowMetrics=*
compartmentId=$comp_id
EOM
sleep 60
if [ -d "/var/lib/oracle-cloud-agent/plugins/oci-managementagent/polaris/agent_inst/discovery/PrometheusEmitter" ]
then
    cd /var/lib/oracle-cloud-agent/plugins/oci-managementagent/polaris/agent_inst/discovery/PrometheusEmitter
    cp /tmp/`hostname`.properties .
fi