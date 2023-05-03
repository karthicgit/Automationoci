#!/bin/bash
version=1.5.0
os=`uname`
platform=`uname -p`
if [[ ($os == "Linux" && $platform == "aarch64") ]]
then
    wget https://github.com/prometheus/node_exporter/releases/download/v$version/node_exporter-$version.linux-arm64.tar.gz 
elif [[ ($os == "Linux" && $platform == "x86_64") ]]
then
    wget https://github.com/prometheus/node_exporter/releases/download/v$version/node_exporter-$version.linux-amd64.tar.gz
fi
tar xvfz node_exporter-$version.*.tar.gz
cd node_exporter-$version*
./node_exporter &
cd /tmp
promfile=`hostname`.properties
ip=`ifconfig | grep "inet " |grep -v 127.0.0.1 |awk '{print $2}'`
hostname=`hostname`
comp_id=`oci-metadata |grep "Compartment OCID" |awk '{print $3}'`
/bin/cat <<EOM > $promfile
url=http://$ip:9100/metrics
namespace=dev_prometheus
nodeName=$hostname
metricDimensions=nodeName
allowMetrics=*
compartmentId=$comp_id
EOM
sleep 60
if [ -d "/var/lib/oracle-cloud-agent/plugins/oci-managementagent/polaris/agent_inst/discovery/PrometheusEmitter/" ]
then
    cd /var/lib/oracle-cloud-agent/plugins/oci-managementagent/polaris/agent_inst/discovery/PrometheusEmitter
    cp /tmp/`hostname`.properties .
fi
