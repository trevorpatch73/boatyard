import os
import git
import csv
import time
from datetime import datetime

t=1

def handle_terraform_files(repo_url, git_username, git_email):
    # Convert HTTPS URL to SSH URL (if needed)
    if repo_url.startswith("https://"):
        repo_url = repo_url.replace("https://github.com/", "git@github.com:")
        repo_url = repo_url.replace(".git", "") + ".git"  # Ensure the URL ends with .git

    # Define the local repository path
    local_repository_path = os.path.join("./application/git_repos", os.path.basename(repo_url))

    # Clone the repository if it doesn't exist locally
    if not os.path.exists(local_repository_path):
        print(f"Cloning repository {repo_url} into {local_repository_path}")
        repo = git.Repo.clone_from(repo_url, local_repository_path)
    else:
        # If the repository already exists locally, pull the latest changes from the 'main' branch
        print(f"Repository {repo_url} exists locally. Pulling the latest changes from 'main' branch.")
        repo = git.Repo(local_repository_path)
        try:
            repo.git.checkout('main')
            repo.git.pull('origin', 'main')
        except Exception as e:
            print(f"Error pulling changes from 'main': {e}")
            return
    # Get current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create new branch for Terraform files
    branch_name = f"hcl_code_files__{timestamp}"
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()

    # Configure Git username and email for the commit
    repo.config_writer().set_value("user", "name", git_username).release()
    repo.config_writer().set_value("user", "email", git_email).release()

    # Define the Initial Terraform File Contents
    providers_tf_template = '''
    terraform {
      required_providers {
        aci = {
          source = "ciscodevnet/aci"
          version = "2.13.2"
        }
      }
      
      required_version = "~> 1.7.2"
      
      backend "s3" {
        bucket = "us-east1-tpatch-terraform"
        key    = "root/workspaces/github/terraform.tfstate"
        region = "us-east-1"
      }      
    }
    
    provider "aci" {
      username = var.CISCO_ACI_TERRAFORM_USERNAME
      password = var.CISCO_ACI_TERRAFORM_PASSWORD
      url      = var.CISCO_ACI_APIC_IP_ADDRESS
      insecure = true
    }
    
    variable "CISCO_ACI_TERRAFORM_USERNAME" {
      type        = string
      description = "MAPS TO ENVIRONMENTAL VARIABLE TF_VAR_CISCO_ACI_TERRAFORM_USERNAME"
    }
    
    variable "CISCO_ACI_TERRAFORM_PASSWORD" {
      type        = string
      description = "MAPS TO ENVIRONMENTAL VARIABLE TF_VAR_CISCO_ACI_TERRAFORM_PASSWORD"
      sensitive   = true
    }
    
    variable "CISCO_ACI_APIC_IP_ADDRESS" {
      type        = string
      description = "MAPS TO ENVIRONMENTAL VARIABLE TF_VAR_CISCO_ACI_APIC_IP_ADDRESS"
    }
    '''
    
    main_tf_template = '''
    # https://registry.terraform.io/providers/CiscoDevNet/aci/2.13.2/docs/resources/fabric_node_member
    # resource index key is "${each.value.NODE_ID}"
    resource "aci_fabric_node_member" "localAciFabricNodeMemberIteration" {
      for_each      = local.aci_fabric_node_member_rows
    
      name          = each.value.NODE_NAME          
      serial        = each.value.SERIAL_NUMBER 
      annotation    = "orchestrator:terraform"
      description   = "${each.value.NODE_NAME}-${each.value.SERIAL_NUMBER} registered to node-id-${each.value.NODE_ID}"          
      ext_pool_id   = "0"
      fabric_id     = "1"
      node_id       = each.value.NODE_ID       
      node_type     = "unspecified"
      pod_id        = each.value.POD_ID 
      role          = each.value.NODE_ROLE   
    }
    
    # https://registry.terraform.io/providers/CiscoDevNet/aci/2.13.2/docs/resources/leaf_interface_profile
    # resource index key is "${each.value.NODE_ID}"
    resource "aci_leaf_interface_profile" "localAciLeafInterfaceProfileIteration" {
      for_each      = local.filtered_node_role_leaf_rows
    
      name          = join("_", [each.value.NODE_ID, "INT_PROF"]) 
      description   = "Container for Interface Selectors MOs mapped to node-id-${each.value.NODE_ID}"                           
      annotation    = "orchestrator:terraform"
    }
    
    # https://registry.terraform.io/providers/CiscoDevNet/aci/2.13.2/docs/resources/access_switch_policy_group
    # resource index key is "${each.value.NODE_ID}"
    resource "aci_access_switch_policy_group" "localAciAccessSwitchPolicyGroupIteration" {
      for_each                                                  = local.filtered_node_role_leaf_rows
    
      name                                                      = join("_", [each.value.NODE_ID, "SW_POL_GRP"]) 
      description                                               = "Container for all nested config applied to node-id-${each.value.NODE_ID}"                            
      annotation                                                = "orchestrator:terraform"
      
      # SETS ALL POLICIES TO DEFAULT.
      # YOU CAN CHANGE THESE IN GUI WITHOUT DRIFT DUE TO LIFECYCLE STATEMENT.
      # FUTURE FEATURE ENHANCEMENT TO SET THESE ON SWITCH PROVISION.
      
      relation_infra_rs_bfd_ipv4_inst_pol                       = "uni/infra/bfdIpv4Inst-default"
      relation_infra_rs_bfd_ipv6_inst_pol                       = "uni/infra/bfdIpv6Inst-default"
      relation_infra_rs_bfd_mh_ipv4_inst_pol                    = "uni/infra/bfdMhIpv4Inst-default"
      relation_infra_rs_bfd_mh_ipv6_inst_pol                    = "uni/infra/bfdMhIpv6Inst-default"
      relation_infra_rs_equipment_flash_config_pol              = "uni/infra/flashconfigpol-default"
      relation_infra_rs_fc_fabric_pol                           = "uni/infra/fcfabricpol-default"
      relation_infra_rs_fc_inst_pol                             = "uni/infra/fcinstpol-default"
      relation_infra_rs_iacl_leaf_profile                       = "uni/infra/iaclleafp-default"
      relation_infra_rs_l2_node_auth_pol                        = "uni/infra/nodeauthpol-default"
      relation_infra_rs_leaf_copp_profile                       = "uni/infra/coppleafp-default"
      relation_infra_rs_leaf_p_grp_to_cdp_if_pol                = "uni/infra/cdpIfP-default"
      relation_infra_rs_leaf_p_grp_to_lldp_if_pol               = "uni/infra/lldpIfP-default"
      relation_infra_rs_mon_node_infra_pol                      = "uni/infra/moninfra-default"
      relation_infra_rs_mst_inst_pol                            = "uni/infra/mstpInstPol-default"
      relation_infra_rs_poe_inst_pol                            = "uni/infra/poeInstP-default"
      relation_infra_rs_topoctrl_fast_link_failover_inst_pol    = "uni/infra/fastlinkfailoverinstpol-default"
      relation_infra_rs_topoctrl_fwd_scale_prof_pol             = "uni/infra/fwdscalepol-default"
      
      lifecycle {
        ignore_changes = [
          relation_infra_rs_bfd_ipv4_inst_pol,
          relation_infra_rs_bfd_ipv6_inst_pol,
          relation_infra_rs_bfd_mh_ipv4_inst_pol,
          relation_infra_rs_bfd_mh_ipv6_inst_pol,
          relation_infra_rs_equipment_flash_config_pol,
          relation_infra_rs_fc_fabric_pol,
          relation_infra_rs_fc_inst_pol,
          relation_infra_rs_iacl_leaf_profile,
          relation_infra_rs_l2_node_auth_pol,
          relation_infra_rs_leaf_copp_profile,
          relation_infra_rs_leaf_p_grp_to_cdp_if_pol,
          relation_infra_rs_leaf_p_grp_to_lldp_if_pol,
          relation_infra_rs_mon_node_infra_pol,
          relation_infra_rs_mst_inst_pol,
          relation_infra_rs_poe_inst_pol,
          relation_infra_rs_topoctrl_fast_link_failover_inst_pol,
          relation_infra_rs_topoctrl_fwd_scale_prof_pol
        ]
      }        
    }
    
    # https://registry.terraform.io/providers/CiscoDevNet/aci/2.13.2/docs/resources/leaf_profile
    # resource index key is "${each.value.NODE_ID}"
    resource "aci_leaf_profile" "localAciLeafProfileIteration" {
      for_each = local.filtered_node_role_leaf_rows
    
      name                          = join("_", [each.value.NODE_ID, "SW_PROF"])
      description                   = "Attachment point for policies configuring node-id-${each.value.NODE_ID}"
      annotation                    = "orchestrator:terraform"
    
      leaf_selector {
        name                        = join("_", [each.value.NODE_ID, "LFSEL"])
        switch_association_type     = "range"
        node_block {
          name                      = join("_", ["blk", each.value.NODE_ID])
          from_                     = each.value.NODE_ID
          to_                       = each.value.NODE_ID
        }
      }
    
      relation_infra_rs_acc_port_p  = [aci_leaf_interface_profile.localAciLeafInterfaceProfileIteration["${each.value.NODE_ID}"].id]
    }
    
    # https://registry.terraform.io/providers/CiscoDevNet/aci/2.13.2/docs/resources/rest
    # resource index key is "${each.value.NODE_ID}"
    resource "aci_rest" "localAciRestLeafSWPROFAssocSWPOLGRP" {
      for_each = local.filtered_node_role_leaf_rows
    
      path    = "/api/node/mo/uni/infra/nprof-${aci_leaf_profile.localAciLeafProfileIteration["${each.value.NODE_ID}"].name}/leaves-${each.value.NODE_ID}_LFSEL-typ-range.json"
      payload = <<EOF
    {
      "infraLeafS": {
        "attributes": {
          "dn": "uni/infra/nprof-${aci_leaf_profile.localAciLeafProfileIteration["${each.value.NODE_ID}"].name}/leaves-${each.value.NODE_ID}_LFSEL-typ-range"
        },
        "children": [
          {
            "infraRsAccNodePGrp": {
              "attributes": {
                "tDn": "uni/infra/funcprof/accnodepgrp-${aci_access_switch_policy_group.localAciAccessSwitchPolicyGroupIteration["${each.value.NODE_ID}"].name}",
                "status": "created"
              },
              "children": []
            }
          }
        ]
      }
    }
    EOF
    
      depends_on = [
        aci_leaf_profile.localAciLeafProfileIteration,
        aci_access_switch_policy_group.localAciAccessSwitchPolicyGroupIteration
      ]
    }

    # https://registry.terraform.io/providers/CiscoDevNet/aci/2.13.2/docs/resources/vpc_domain_policy
    # resource index key is "${each.value.ODD_NODE_ID}:${each.value.EVEN_NODE_ID}"
    resource "aci_vpc_domain_policy" "localAciVpcDomainPolicyIteration" {
      for_each = local.aci_vpc_explicit_protection_group_rows
    
      name       = join("_", [each.value.ODD_NODE_ID, each.value.EVEN_NODE_ID, "VDP"])
      annotation = "orchestrator:terraform"
      dead_intvl = "200"
    }

    # https://registry.terraform.io/providers/CiscoDevNet/aci/2.13.2/docs/resources/vpc_explicit_protection_group
    # resource index key is "${each.value.ODD_NODE_ID}:${each.value.EVEN_NODE_ID}"
    resource "aci_vpc_explicit_protection_group" "localAciVpcExplictProtectionGroupIteration" {
      for_each = local.aci_vpc_explicit_protection_group_rows
    
      name                             = join("_", [each.value.ODD_NODE_ID, each.value.EVEN_NODE_ID, "VEPG"])
      annotation                       = "orchestrator:terraform"
      switch1                          = each.value.ODD_NODE_ID
      switch2                          = each.value.EVEN_NODE_ID
      vpc_domain_policy                = aci_vpc_domain_policy.localAciVpcDomainPolicyIteration["${each.value.ODD_NODE_ID}:${each.value.EVEN_NODE_ID}"].name
      vpc_explicit_protection_group_id = each.value.GROUP_ID
    }    
    '''
    variables_tf_template = '''
    # Terraform Variables For Cisco ACI
    '''

    outputs_tf_template = '''
    # Terraform Outputs For Cisco ACI
    '''

    locals_tf_template = '''
    locals{
        aci_fabric_node_member_iterations = csvdecode(file("./data/aci_fabric_node_member.csv"))
        
        aci_fabric_node_member_rows = {
            for i in local.aci_fabric_node_member_iterations : i.NODE_ID => {
                FABRIC_NAME     = i.FABRIC_NAME
                NODE_ROLE       = i.NODE_ROLE
                POD_ID          = i.POD_ID
                NODE_ID         = i.NODE_ID  
                NODE_PEER_ID    = i.NODE_PEER_ID
                SERIAL_NUMBER   = i.SERIAL_NUMBER
                NODE_NAME       = i.NODE_NAME
            }
        }
        
        filtered_node_role_leaf_rows = {
            for key, value in local.aci_fabric_node_member_rows : key => value
            if value.NODE_ROLE == "leaf"
        }
        
        aci_vpc_explicit_protection_group_iterations = csvdecode(file("./data/aci_vpc_explicit_protection_group.csv")) 
        
        aci_vpc_explicit_protection_group_rows = {
            for i in local.aci_vpc_explicit_protection_group_iterations : "${i.ODD_NODE_ID}:${i.EVEN_NODE_ID}" => {
                FABRIC_NAME     = i.FABRIC_NAME
                ODD_NODE_ID     = i.ODD_NODE_ID  
                EVEN_NODE_ID    = i.EVEN_NODE_ID 
                GROUP_ID        = i.GROUP_ID
            }
        }        
    }
    '''
    
    # Manual Map CSVs for initial creation 
    csv_files_headers = {
        "aci_fabric_node_member.csv": ["FABRIC_NAME", "NODE_ROLE", "POD_ID", "NODE_ID", "NODE_PEER_ID", "SERIAL_NUMBER", "NODE_NAME"],
        "aci_vpc_explicit_protection_group.csv": ["FABRIC_NAME", "ODD_NODE_ID", "EVEN_NODE_ID", "GROUP_ID"]
    }
    
    # Loop through the list of CSVs to make sure they exist    
    for csv_file, headers in csv_files_headers.items():
    
        # Path to the CSV file
        csv_file_path = os.path.join(local_repository_path, "data", csv_file)
        
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
    
        # Check if the file exists
        if not os.path.exists(csv_file_path):
            
            # The file does not exist, create it
            with open(csv_file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                time.sleep(t)
                
                print(f"Created {csv_file} with headers: {headers}")
                
                relative_csv_path = os.path.join("data", csv_file)
                repo.index.add([relative_csv_path])
                repo.index.commit(f"Created {csv_file} with headers: {headers}")
        else:
            # The file exists, do nothing
            print(f"File {csv_file} already exists.")       

    # Create Terraform files
    create_terraform_file(repo, local_repository_path, "providers.tf", providers_tf_template)
    create_terraform_file(repo, local_repository_path, "main.tf", main_tf_template)
    create_terraform_file(repo, local_repository_path, "variables.tf", variables_tf_template)
    create_terraform_file(repo, local_repository_path, "outputs.tf", outputs_tf_template)
    create_terraform_file(repo, local_repository_path, "locals.tf", locals_tf_template)

    # Commit and push the changes
    repo.index.add(["providers.tf", "main.tf", "variables.tf", "outputs.tf", "locals.tf"])
    repo.index.commit("Add Terraform files")
    origin = repo.remote("origin")
    origin.push(new_branch)

    # Mimic "git add ." by adding all changes including untracked files
    repo.git.add(A=True)
    
    # Mimic "git commit -m" by committing all staged changes
    commit_message = "Update all changes"
    repo.index.commit(commit_message)    

    # Push the changes
    print(f"Pushing changes to remote branch {new_branch}")
    origin = repo.remote(name='origin')
    origin.push(refspec=f'{new_branch}:{new_branch}')
    print(f"Changes pushed to {new_branch}")
    
    print(f"All Terraform files added to {local_repository_path} in branch {new_branch}")

def create_terraform_file(repo, repository_path, file_name, file_template):
    file_path = os.path.join(repository_path, file_name)
    with open(file_path, "w") as f:
        f.write(file_template)
    print(f"Created {file_name} in {repository_path}")
    
def handle_aci_fabric_node_member_data(git_repository, git_username, git_email, fabric_name, switches_data):
    # Convert HTTPS URL to SSH URL (if needed)
    if git_repository.startswith("https://"):
        git_repository = git_repository.replace("https://github.com/", "git@github.com:")
        git_repository = git_repository.replace(".git", "") + ".git"  # Ensure the URL ends with .git

    # Define the local repository path
    local_repository_path = os.path.join("./application/git_repos", os.path.basename(git_repository))

    # Clone the repository if it doesn't exist locally
    if not os.path.exists(local_repository_path):
        print(f"Cloning repository {git_repository} into {local_repository_path}")
        repo = git.Repo.clone_from(git_repository, local_repository_path)
    else:
        # If the repository already exists locally, pull the latest changes from the 'main' branch
        print(f"Repository {git_repository} exists locally. Pulling the latest changes from 'main' branch.")
        repo = git.Repo(local_repository_path)
        try:
            repo.git.checkout('main')
            repo.git.pull('origin', 'main')
        except Exception as e:
            print(f"Error pulling changes from 'main': {e}")
            return

    # Path to the CSV file
    csv_file_path = os.path.join(local_repository_path, "data", "aci_fabric_node_member.csv")

    # Ensure the data directory exists
    os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)

    # Write to the CSV file (overwrite if exists)
    with open(csv_file_path, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow([
                "FABRIC_NAME",
                "NODE_ROLE",
                "POD_ID",
                "NODE_ID", 
                "NODE_PEER_ID", 
                "SERIAL_NUMBER", 
                "NODE_NAME"
            ])
        for switch in switches_data:
            csvwriter.writerow([
                switch.fabric_name,
                switch.node_role,
                switch.pod_id,
                switch.node_id,
                switch.node_peer_id,
                switch.serial_number,
                switch.node_name
            ])

    # Get current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create new branch name with timestamp
    branch_name = f"aci_fabric_node_member_data_{timestamp}"
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()    
    
    # Configure Git username and email for the commit
    repo.config_writer().set_value("user", "name", git_username).release()
    repo.config_writer().set_value("user", "email", git_email).release()    
    
    # Commit and push the changes
    relative_csv_path = os.path.join("data", "aci_fabric_node_member.csv")
    repo.index.add([relative_csv_path])
    repo.index.commit(f"Updated ACI fabric node member data for '{fabric_name}' on {timestamp}")
    origin = repo.remote("origin")
    origin.push(new_branch)
    print(f"Updated ACI fabric node member data for '{fabric_name}' in repository {local_repository_path} on branch {branch_name}")
    
def handle_aci_vpc_explict_protection_group_data(git_repository, git_username, git_email, fabric_name, switch_pair_data):
    # Convert HTTPS URL to SSH URL (if needed)
    if git_repository.startswith("https://"):
        git_repository = git_repository.replace("https://github.com/", "git@github.com:")
        git_repository = git_repository.replace(".git", "") + ".git"  # Ensure the URL ends with .git

    # Define the local repository path
    local_repository_path = os.path.join("./application/git_repos", os.path.basename(git_repository))

    # Clone the repository if it doesn't exist locally
    if not os.path.exists(local_repository_path):
        print(f"Cloning repository {git_repository} into {local_repository_path}")
        repo = git.Repo.clone_from(git_repository, local_repository_path)
    else:
        # If the repository already exists locally, pull the latest changes from the 'main' branch
        print(f"Repository {git_repository} exists locally. Pulling the latest changes from 'main' branch.")
        repo = git.Repo(local_repository_path)
        try:
            repo.git.checkout('main')
            repo.git.pull('origin', 'main')
        except Exception as e:
            print(f"Error pulling changes from 'main': {e}")
            return

    # Path to the CSV file
    csv_file_path = os.path.join(local_repository_path, "data", "aci_vpc_explicit_protection_group.csv")

    # Ensure the data directory exists
    os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
    
    # Write to the CSV file (overwrite if exists)
    with open(csv_file_path, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow([
                "FABRIC_NAME",
                "ODD_NODE_ID", 
                "EVEN_NODE_ID", 
                "GROUP_ID"
            ])
        for item in switch_pair_data:
            csvwriter.writerow([
                item.fabric_name,
                item.odd_node_id,
                item.even_node_id,
                item.group_id
            ])
            
    # Get current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create new branch name with timestamp
    branch_name = f"aci_vpc_explicit_protection_group_data_{timestamp}"
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()    
    
    # Configure Git username and email for the commit
    repo.config_writer().set_value("user", "name", git_username).release()
    repo.config_writer().set_value("user", "email", git_email).release()    
    
    # Commit and push the changes
    relative_csv_path = os.path.join("data", "aci_vpc_explicit_protection_group.csv")
    repo.index.add([relative_csv_path])
    repo.index.commit(f"Updated aci_vpc_explicit_protection_group for '{fabric_name}' on {timestamp}")
    origin = repo.remote("origin")
    origin.push(new_branch)
    print(f"Updated aci_vpc_explicit_protection_group for '{fabric_name}' in repository {local_repository_path} on branch {branch_name}")            