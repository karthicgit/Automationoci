import oci

import random,json,io
from fdk import response

#Get container instance details
def get_ci(ci_id):
    try:
        signer = oci.auth.signers.get_resource_principals_signer()
        ci_client = oci.container_instances.ContainerInstanceClient(config={}, signer=signer)
        get_container_instance_response = ci_client.get_container_instance(
            container_instance_id=ci_id)
        display_name=get_container_instance_response.data.display_name
        return display_name
    except Exception as e2:
        print(str(e2),flush=True)
        exit(1)

#Create Container Instance
def create_ci(ci_id):
    try:
        signer = oci.auth.signers.get_resource_principals_signer()
        ci_client = oci.container_instances.ContainerInstanceClient(config={}, signer=signer)
        identity_client = oci.identity.IdentityClient(config={},signer=signer)
        network_client = oci.core.VirtualNetworkClient(config={},signer=signer)
        availability_domains = identity_client.list_availability_domains(signer.tenancy_id).data
        ad_name=[]
        for ads in availability_domains:
            ad_name.append(ads.name)
        if len(ad_name) != 1:
            ad = random.choice(ad_name)
        else:
            ad = ad_name[0]
        ci_response = ci_client.get_container_instance(
            container_instance_id=ci_id).data
        ci_shape=ci_response.shape
        ci_name=ci_response.display_name
        ci_compartment_id=ci_response.compartment_id
        ci_ocpus=ci_response.shape_config.ocpus
        ci_mem=ci_response.shape_config.memory_in_gbs
        ci_volumes=ci_response.volumes
        #ci_dnsconfig=ci_response.dns_config
        ci_freeform_tags={"Created-by":"Autoscaler"}
        ci_graceful_shut_time=ci_response.graceful_shutdown_timeout_in_seconds
        vnic = network_client.get_vnic(vnic_id=ci_response.vnics[0].vnic_id).data
        ci_subnet=vnic.subnet_id

        #Fetch Volume details
        volumes=[]
        for volume in ci_volumes:
            if volume.volume_type == "EMPTYDIR":
                volumes.append(oci.container_instances.models.CreateContainerEmptyDirVolumeDetails(
                    volume_type="EMPTYDIR",
                    name=volume.name,
                    backing_store=volume.backing_store))
            else:
                volumes.append(oci.container_instances.models.CreateContainerEmptyDirVolumeDetails(
                    volume_type="CONFIGFILE",
                    name=volume.name,
                    configs=volume.configs))

        #Get container details and volume mount
        volume_mounts=[]
        containers=[]
        for container in ci_response.containers:
            get_container_response = ci_client.get_container(
                container_id=container.container_id)
            container_data=get_container_response.data
            if container_data.resource_config is None:
                ci_resource_config={}
            else:
                ci_resource_config=oci.container_instances.models.CreateContainerResourceConfigDetails(
                memory_limit_in_gbs=container_data.resource_config.memory_limit_in_gbs,
                vcpus_limit=container_data.resource_config.vcpus_limit)

            for v in container_data.volume_mounts:
                volume_mounts.append(oci.container_instances.models.CreateVolumeMountDetails(
                    volume_name=v.volume_name,
                    mount_path=v.mount_path,
                    sub_path=v.sub_path
                ))
            containers.append(oci.container_instances.models.CreateContainerDetails(
                image_url=container_data.image_url,
                display_name=container_data.display_name,
                command=container_data.command,
                arguments=container_data.arguments,
                working_directory=container_data.working_directory,
                environment_variables=container_data.environment_variables,
                volume_mounts=volume_mounts,
                is_resource_principal_disabled=container_data.is_resource_principal_disabled,
                resource_config=ci_resource_config,
                freeform_tags=ci_freeform_tags
            ))

        create_container_instance_response = ci_client.create_container_instance(
            create_container_instance_details=oci.container_instances.models.CreateContainerInstanceDetails(
                compartment_id=ci_compartment_id,
                availability_domain=ad,
                shape=ci_shape,
                shape_config=oci.container_instances.models.CreateContainerInstanceShapeConfigDetails(
                    ocpus=ci_ocpus,
                    memory_in_gbs=ci_mem),
                containers=containers,
                vnics=[
                    oci.container_instances.models.CreateContainerVnicDetails(
                        subnet_id=ci_subnet)],
                display_name=ci_name,
                # fault_domain="EXAMPLE-faultDomain-Value",
                volumes=volumes,
                #dns_config=ci_dnsconfig,
                graceful_shutdown_timeout_in_seconds=int(ci_graceful_shut_time),
                container_restart_policy="ON_FAILURE",
                freeform_tags=ci_freeform_tags))

        return f"Container created with ocid {create_container_instance_response.data.id}"
    except Exception as cr:
        print(str(cr),flush=True)

#Delete Container instance
def list_ci(comp_id,ci_id):
    try:
        display_name=get_ci(ci_id)
        signer = oci.auth.signers.get_resource_principals_signer()
        ci_client = oci.container_instances.ContainerInstanceClient(config={}, signer=signer)
        list_container_instances_response = ci_client.list_container_instances(
            compartment_id=comp_id,
            lifecycle_state="ACTIVE",
            display_name=display_name,
            sort_order="DESC",
            sort_by="timeCreated")
        num_of_ci=len(list_container_instances_response.data.items)
        last_ci_created=list_container_instances_response.data.items[0].id
        return num_of_ci,last_ci_created
    except Exception as e1:
        print(str(e1),flush=True)


#Scale out CI
def scale_out_ci(ci_id,max_ci,comp_id):

    num_ci,last_ci = list_ci(comp_id,ci_id)

    if int(num_ci) < int(max_ci):
            print(f"Creating new container instance")
            response = create_ci(ci_id)
            return response
    else:
            print(f"Cant scale out further as max reached")
            response = "Cant scale out further as max reached"
            return response

#Scale in CI
def scale_in_ci(ci_id,min_ci,comp_id):
    signer = oci.auth.signers.get_resource_principals_signer()
    ci_client = oci.container_instances.ContainerInstanceClient(config={}, signer=signer)

    num_ci,last_ci = list_ci(comp_id,ci_id)

    if int(num_ci) > int(min_ci):
        ci_client.delete_container_instance(
            container_instance_id=last_ci)
        return f"Deleted CI with ocid {last_ci}"
    else:
        print(f"Cant scale in further as min reached")
        return f"Cant scale in further as min reached"

def handler(ctx, data: io.BytesIO=None):
    alarm_msg = {}
    cfg = ctx.Config()
    min_ci = cfg["min_ci"]
    max_ci = cfg["max_ci"]
    comp_id=cfg["compartment_id"]

    try:
        alarm_msg = json.loads(data.getvalue())
        print("INFO: Alarm message: ")
        print(alarm_msg, flush=True)
    except (Exception, ValueError) as ex:
        print(str(ex), flush=True)

    if alarm_msg["type"] == "OK_TO_FIRING" and "CIalarm" in alarm_msg["title"]:

        ci_id = alarm_msg["body"]
        test=alarm_msg["body"]

        func_response = scale_out_ci(ci_id,max_ci,comp_id)
        print("INFO: ", func_response, flush=True)
    elif alarm_msg["type"] == "FIRING_TO_OK" and "CIalarm" in alarm_msg["title"]:

        ci_id = alarm_msg["body"]

        func_response = scale_in_ci(ci_id,min_ci,comp_id)
        print("INFO: ", func_response, flush=True)
    else:
        print("Nothing to do")
        func_response = "Nothing to do, alarm is not FIRING"

    return response.Response(
        ctx,
        response_data=func_response,
        headers={"Content-Type": "application/json"}
    )
