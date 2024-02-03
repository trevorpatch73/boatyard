from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.exceptions import NotFound
from sqlalchemy import func, or_
from ipaddress import ip_network
from . import db
import json

from .models import InfrastructureCiscoAci, CiscoACISwitch, CiscoACISwitchVpcPairs, EnvironmentTypes, LocationItems, TenantItems, ZoneItems, IPAM_CIDRS, IPAM_HOSTS, DomainItems
from .functions import handle_terraform_files, handle_aci_fabric_node_member_data, handle_aci_vpc_explict_protection_group_data

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    return render_template("home.html", user=current_user)
    
@views.route('/manage-portal', methods=['GET', 'POST'])
@login_required
def manage_portal():
    if request.method == 'POST' and 'manage_tenants_form' in request.form:
        tenant_name = request.form.get('tenant_name')
        
        existing_tenant = TenantItems.query.filter_by(tenant_name=tenant_name).first()
        if existing_tenant is not None:
            flash('Tenant already exists.', category='error')
        else:
            new_tenant = TenantItems(tenant_name=tenant_name)  # Adjust according to your model
            db.session.add(new_tenant)
            db.session.commit()
            flash('Tenant added successfully!', category='success')
            return redirect(url_for('views.manage_portal'))  # Redirect to clear the form/post request
    
    tenants = TenantItems.query.all()
    
    if request.method == 'POST' and 'manage_zones_form' in request.form:
        zone_name = request.form.get('zone_name')
        
        existing_zone = ZoneItems.query.filter_by(zone_name=zone_name).first()
        if existing_zone is not None:
            flash('zone already exists.', category='error')
        else:
            new_zone = ZoneItems(zone_name=zone_name)
            db.session.add(new_zone)
            db.session.commit()
            flash('zone added successfully!', category='success')
            return redirect(url_for('views.manage_portal'))
    
    zones = ZoneItems.query.all()
    
    if request.method == 'POST' and 'manage_envs_form' in request.form:
        env_name = request.form.get('env_name')
        
        existing_env = EnvironmentTypes.query.filter_by(types=env_name).first()
        if existing_env is not None:
            flash('env already exists.', category='error')
        else:
            new_env = EnvironmentTypes(types=env_name)
            db.session.add(new_env)
            db.session.commit()
            flash('env added successfully!', category='success')
            return redirect(url_for('views.manage_portal'))
    
    envs = EnvironmentTypes.query.all() 
    
    
    return render_template("manage_portal.html", user=current_user, tenants=tenants, zones=zones, envs=envs)   
    
@views.route('/delete-tenant/<int:id>', methods=['POST'])
@login_required
def delete_tenant(id):
    # Query the database for the infrastructure entry
    tenant_to_delete = TenantItems.query.get_or_404(id)

    # Delete the entry from the database
    db.session.delete(tenant_to_delete)
    db.session.commit()

    flash('Infrastructure entry deleted successfully!', category='success')
    return redirect(url_for('views.manage_portal')) 
    
@views.route('/delete-zone/<int:id>', methods=['POST'])
@login_required
def delete_zone(id):
    # Query the database for the infrastructure entry
    zone_to_delete = ZoneItems.query.get_or_404(id)

    # Delete the entry from the database
    db.session.delete(zone_to_delete)
    db.session.commit()

    flash('Infrastructure entry deleted successfully!', category='success')
    return redirect(url_for('views.manage_portal')) 
    
@views.route('/delete-env/<int:id>', methods=['POST'])
@login_required
def delete_env(id):
    # Query the database for the infrastructure entry
    env_to_delete = EnvironmentTypes.query.get_or_404(id)

    # Delete the entry from the database
    db.session.delete(env_to_delete)
    db.session.commit()

    flash('Infrastructure entry deleted successfully!', category='success')
    return redirect(url_for('views.manage_portal'))        

@views.route('/infrastructure', methods=['GET', 'POST'])
@login_required
def infrastructure():
    return render_template("infrastructure.html", user=current_user)
    
@views.route('/infrastructure/ciscoaci', methods=['GET', 'POST'])
@login_required
def infrastructure_ciscoaci():
    print("Entered infrastructure_ciscoaci route")
    # Initialize variables
    infrastructures = []
    fabric_names = []
    used_node_ids = []
    used_peer_ids = [] 
    available_node_ids = []
    available_peer_ids = []
    switches = []

    try:
        # Fetch all infrastructures and switches
        infrastructures = InfrastructureCiscoAci.query.with_entities(
            InfrastructureCiscoAci.id, 
            InfrastructureCiscoAci.fabric_name, 
            InfrastructureCiscoAci.target_apic, 
            InfrastructureCiscoAci.service_account_username,
            InfrastructureCiscoAci.git_repository,
            InfrastructureCiscoAci.git_username,
            InfrastructureCiscoAci.git_email
        ).all()
        switches = CiscoACISwitch.query.all()

        # Initialize lists for fabric names, available node IDs, and used peer IDs
        fabric_names = [inf.fabric_name for inf in infrastructures]
        used_node_ids = [switch.node_id for switch in switches]
        used_peer_ids = [switch.node_peer_id for switch in switches]
        available_node_ids = [i for i in range(101, 4001) if i not in used_node_ids]
        available_peer_ids = [i for i in range(101, 4001) if i not in used_peer_ids]

        # Handle Cisco ACI infrastructure form submission
        if request.method == 'POST' and 'infrastructure_form' in request.form:
            fabric_name = request.form.get('fabric_name')
            target_apic = request.form.get('target_apic')
            service_account_username = request.form.get('service_account_username')
            service_account_password = request.form.get('service_account_password')
            git_repository = request.form.get('git_repository')
            git_username = request.form.get('git_username')
            git_email = request.form.get('git_email')

            existing_apic = InfrastructureCiscoAci.query.filter_by(target_apic=target_apic).first()
            if existing_apic:
                flash('APIC IP already exists.', category='error')
            else:
                new_infrastructure = InfrastructureCiscoAci(
                    fabric_name=fabric_name,
                    target_apic=target_apic,
                    service_account_username=service_account_username,
                    service_account_password=generate_password_hash(service_account_password),
                    git_repository=git_repository,
                    git_username=git_username,
                    git_email=git_email
                )
                db.session.add(new_infrastructure)
                db.session.commit()
                flash('Infrastructure added successfully!', category='success')
                handle_terraform_files(git_repository, git_username, git_email)

            existing_locations = LocationItems.query.filter_by(items=fabric_name).first()
            if existing_locations:
                print(f"Location, {fabric_name} Exists")
            else:
                new_location = LocationItems(items=fabric_name)
                db.session.add(new_location)
                db.session.commit()
                flash('Location added successfully!', category='success')                

        # Handle switch form submission
        if request.method == 'POST' and 'switch_form' in request.form:
            print("Handling switch form submission")
            fabric_name = request.form.get('fabric_name')
            print(f"Fabric Name: {fabric_name}")
            node_role = request.form.get('node_role')
            pod_id = request.form.get('pod_id', type=int)
            node_id = request.form.get('node_id', type=int)
            node_peer_id = request.form.get('node_peer_id', type=int)
            serial_number = request.form.get('serial_number')
            node_name = request.form.get('node_name')

            # Logging or printing the extracted values for validation
            print(f"Attempting to add a new switch pair: Fabric Name={fabric_name}, Node ID={node_id}, Node Peer ID={node_peer_id}")
            

            existing_switch = CiscoACISwitch.query.filter_by(fabric_name=fabric_name, node_id=node_id).first()
            if existing_switch:
                flash('This node ID is already assigned for the selected fabric.', category='error')
                print("Existing switch found, not adding a new one.")
            else:
                print("Adding a new switch...")
                new_switch = CiscoACISwitch(
                    fabric_name=fabric_name,
                    node_role=node_role,
                    pod_id=pod_id,
                    node_id=node_id,
                    node_peer_id=node_peer_id,
                    serial_number=serial_number,
                    node_name=node_name
                )
                db.session.add(new_switch)
                db.session.commit()
                flash('Switch added successfully!', category='success')
                
                node_id = int(node_id)
                if node_id % 2 != 0:  # Checking if node_id is odd
                    # Querying the highest group_id
                    max_group_id = db.session.query(func.max(CiscoACISwitchVpcPairs.group_id)).filter(CiscoACISwitchVpcPairs.fabric_name == fabric_name).scalar()
                    new_group_id = 1 if max_group_id is None else max_group_id + 1
                    
                    # Validate the new_group_id is within Cisco ACI's Range
                    if 1 <= new_group_id <= 1000:
                        # Prepare the new pair for insertion
                        new_pair = CiscoACISwitchVpcPairs(
                            fabric_name=fabric_name,
                            odd_node_id=node_id,
                            even_node_id=node_peer_id,
                            group_id=new_group_id
                        )
                        
                        # Trying to insert the new pair into the database
                        try:
                            db.session.add(new_pair)
                            db.session.commit()
                            print(f"New switch pair added successfully: {new_pair}")
                            flash('Switch Pair added successfully!', category='success')
                        except Exception as e:
                            db.session.rollback()  # Rolling back in case of error
                            print(f"Error adding new pair to database: {e}")
                            flash(f'Error adding switch pair: {e}', category='error')
                    else:
                        flash('Exceeded maximum group ID value.', category='error')
                
                if new_switch:
                    print("New switch added, now looking for an IP...")
                    # Query the required network prefixes from IPAM_CIDR
                    cidr_records = IPAM_CIDRS.query.filter_by(
                        location_id=fabric_name,
                        tenant_id="global",
                        zone_id="OOB",
                        environment_id="PRD"
                    ).all()
                    print(f"Found {len(cidr_records)} CIDR records for assignment.")
                
                    # Loop through each CIDR record to find available IPs
                    for cidr in cidr_records:
                        # Find all hosts in IPAM_HOSTS for the network prefix
                        all_hosts = IPAM_HOSTS.query.filter(IPAM_HOSTS.network_prefix == cidr.network_prefix).first()
                        print(f"Fetched {len(all_hosts)} hosts for network prefix {cidr.network_prefix}")
                
                        # Find the first host with an unpopulated host_name
                        for host in all_hosts:
                            if not host.host_name:  # This checks for both None and empty string ''
                                print(f"Assigning IP {host.network_ip} to switch {node_name}")
                                # Update the IPAM_HOSTS record with the new details
                                host.host_name = node_name
                                host.domain_id = ".internal.das"
                                host.role = "SWITCH"
                
                                # Commit the changes to the database
                                try:
                                    db.session.commit()
                                    print(f"Assigned IP {host.network_ip} to switch {node_name}")
                                    flash(f'Assigned IP {host.network_ip} to switch {node_name}', category='success')
                                    break  # Exit the loop after assigning the first available IP
                                except Exception as e:
                                    db.session.rollback()
                                    print(f"Failed to assign IP to switch {node_name}: {e}")
                                    flash(f'Failed to assign IP: {e}', category='error')
                                break  # Break the loop to avoid checking more hosts if an IP was assigned
                        else:
                            # If the inner loop did not break, it means no available IP was found
                            flash('No available IP addresses found for the switch.', category='error')
                            print("No available IP addresses found for the switch.")
                            break  # Break the outer loop as well

                
            # Fetch git repository details
            find_fabric_git = InfrastructureCiscoAci.query.filter_by(fabric_name=fabric_name).first()
            
            if find_fabric_git:
                git_repository = find_fabric_git.git_repository
                git_username = find_fabric_git.git_username
                git_email = find_fabric_git.git_email
    
                # Fetch all switches data for the given fabric
                switches_data = CiscoACISwitch.query.filter_by(fabric_name=fabric_name).all()
    
                handle_aci_fabric_node_member_data(
                    git_repository, 
                    git_username, 
                    git_email,
                    fabric_name,
                    switches_data
                )
                
                # Fetch all switch pairs data for the given fabric
                switch_pair_data = CiscoACISwitchVpcPairs.query.filter_by(fabric_name=fabric_name).all()
                
                handle_aci_vpc_explict_protection_group_data(
                    git_repository, 
                    git_username, 
                    git_email,
                    fabric_name,
                    switch_pair_data
                )
                        
            else:
                print(f"No git repository information found for fabric name '{fabric_name}'")

        # After form submission handling
        # Refresh the lists
        fabric_names = [inf.fabric_name for inf in InfrastructureCiscoAci.query.all()]
        used_node_ids = [switch.node_id for switch in CiscoACISwitch.query.all()]
        used_peer_ids = [switch.node_peer_id for switch in CiscoACISwitch.query.all()]
        available_node_ids = [i for i in range(101, 4001) if i not in used_node_ids]
        available_peer_ids = [i for i in range(101, 4001) if i not in used_peer_ids]


    except Exception as e:
        print(f"An error occurred: {e}")  # Debugging: Print any errors
        flash(f"An error occurred: {e}", category='error')  # Display error message to user

    # Render the template with initialized variables
    return render_template("infrastructure_ciscoaci.html", user=current_user, 
                           infrastructures=infrastructures, fabric_names=fabric_names, 
                           available_node_ids=available_node_ids, available_peer_ids=available_peer_ids,
                           switches=switches)
                           
                           
@views.route('/delete-aci-infrastructure/<int:id>', methods=['POST'])
@login_required
def delete_aci_infrastructure(id):
    # Query the database for the infrastructure entry
    infrastructure_to_delete = InfrastructureCiscoAci.query.get_or_404(id)

    # Delete the entry from the database
    db.session.delete(infrastructure_to_delete)
    db.session.commit()

    flash('Infrastructure entry deleted successfully!', category='success')
    return redirect(url_for('views.infrastructure_ciscoaci'))
    
@views.route('/sync-aci-infrastructure/<int:id>', methods=['POST'])
@login_required
def sync_aci_infrastructure(id):
    # Query the database for the infrastructure entry
    infrastructure = InfrastructureCiscoAci.query.get_or_404(id)
    
    # Directly access attributes of the infrastructure object
    git_repository = infrastructure.git_repository
    git_username = infrastructure.git_username
    git_email = infrastructure.git_email
    
    # Run Functions
    handle_terraform_files(git_repository, git_username, git_email)

    flash('Git sync running', category='success')
    return redirect(url_for('views.infrastructure_ciscoaci'))
    
@views.route('/sync-all-switches/', methods=['POST'])
@login_required
def sync_all_switches():
    # Fetch all fabric records
    all_fabrics = InfrastructureCiscoAci.query.all()

    for fabric in all_fabrics:
        git_repository = fabric.git_repository
        git_username = fabric.git_username
        git_email = fabric.git_email
        fabric_name = fabric.fabric_name

        # Sync switches data
        switches_data = CiscoACISwitch.query.filter_by(fabric_name=fabric_name).all()
        handle_aci_fabric_node_member_data(
            git_repository, 
            git_username, 
            git_email,
            fabric_name,
            switches_data
        )
        
        # Sync switch pairs data
        switch_pair_data = CiscoACISwitchVpcPairs.query.filter_by(fabric_name=fabric_name).all()
        handle_aci_vpc_explict_protection_group_data(
            git_repository, 
            git_username, 
            git_email,
            fabric_name,
            switch_pair_data
        )

    flash('All switches synced with Git', category='success')
    return redirect(url_for('views.infrastructure_ciscoaci'))

    
@views.route('/edit-service-account-username/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_service_account_username(id):
    infrastructure = InfrastructureCiscoAci.query.get_or_404(id)

    if request.method == 'POST':
        new_username = request.form.get('service_account_username')
        infrastructure.service_account_username = new_username
        db.session.commit()
        return redirect(url_for('views.infrastructure_ciscoaci'))

    return render_template('edit_service_account_username.html', infrastructure=infrastructure)

@views.route('/edit-farbic-name/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_fabric_name(id):
    infrastructure = InfrastructureCiscoAci.query.get_or_404(id)

    if request.method == 'POST':
        new_fabric_name = request.form.get('fabric_name')
        infrastructure.fabric_name = new_fabric_name
        db.session.commit()
        return redirect(url_for('views.infrastructure_ciscoaci'))

    return render_template('edit_fabric_name.html', infrastructure=infrastructure)
    
@views.route('/edit-git-repository/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_git_repository(id):
    infrastructure = InfrastructureCiscoAci.query.get_or_404(id)

    if request.method == 'POST':
        new_git_repository = request.form.get('git_repository')
        infrastructure.git_repository = new_git_repository
        db.session.commit()
        return redirect(url_for('views.infrastructure_ciscoaci'))

    return render_template('edit_fabric_name.html', infrastructure=infrastructure)
    
@views.route('/edit-git-username/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_git_username(id):
    infrastructure = InfrastructureCiscoAci.query.get_or_404(id)

    if request.method == 'POST':
        new_git_username = request.form.get('git_username')
        infrastructure.git_username = new_git_username
        db.session.commit()
        return redirect(url_for('views.infrastructure_ciscoaci'))

    return render_template('edit_fabric_name.html', infrastructure=infrastructure)     
    
@views.route('/edit-git-email/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_git_email(id):
    infrastructure = InfrastructureCiscoAci.query.get_or_404(id)

    if request.method == 'POST':
        new_git_email = request.form.get('git_email')
        infrastructure.git_email = new_git_email
        db.session.commit()
        return redirect(url_for('views.infrastructure_ciscoaci'))

    return render_template('edit_fabric_name.html', infrastructure=infrastructure)      
    
@views.route('/delete-switch/<int:id>', methods=['POST'])
@login_required
def delete_switch(id):
    switch_to_delete = CiscoACISwitch.query.get_or_404(id)

    # Check if the switch is part of a VPC pair and handle it
    vpc_pair = CiscoACISwitchVpcPairs.query.filter(
        (CiscoACISwitchVpcPairs.odd_node_id == switch_to_delete.node_id) | 
        (CiscoACISwitchVpcPairs.even_node_id == switch_to_delete.node_id)
    ).first()
    
    if vpc_pair:
        # Depending on your requirement, you can delete the VPC pair or handle it differently
        db.session.delete(vpc_pair)
    
    # Now delete the switch
    db.session.delete(switch_to_delete)
    
    # Commit all changes to the database
    try:
        db.session.commit()
        flash('Switch and associated VPC pair deleted successfully!', category='success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the switch.', category='error')

    return redirect(url_for('views.infrastructure_ciscoaci'))


@views.route('/settings-switch/<int:id>', methods=['POST'])
@login_required
def settings_switch(id):
# FUTURE TO CHANGE TCAM SETTINGS AND THINGS OF THE SORT
    return redirect(url_for('views.infrastructure_ciscoaci'))    
    
@views.route('/edit-node-name/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_node_name(id):
    infrastructure = CiscoACISwitch.query.get_or_404(id)

    if request.method == 'POST':
        new_node_name = request.form.get('node_name')
        infrastructure.node_name = new_node_name
        db.session.commit()
        return redirect(url_for('views.infrastructure_ciscoaci'))

    return render_template('edit_fabric_name.html', infrastructure=infrastructure)
    
@views.route('/infrastructure/ipam', methods=['GET', 'POST'])
@login_required
def infrastructure_ipam():
    if request.method == 'POST' and 'ipam_cidrs_form' in request.form:
        network_prefix = request.form.get('network_prefix')
        network_cidr = request.form.get('network_cidr')
        full_network = f"{network_prefix}/{network_cidr}"
        location_id = request.form.get('location')
        tenant_id = request.form.get('tenant')
        zone_id = request.form.get('zone')
        environment_id = request.form.get('environment')
        application = request.form.get('application')  # Optional

        try:
            new_network = ip_network(full_network, strict=False)
        except ValueError:
            flash('Invalid network prefix/CIDR.', 'error')
            return redirect(url_for('views.infrastructure_ipam'))

        existing_cidrs = IPAM_CIDRS.query.all()
        for cidr in existing_cidrs:
            existing_network = ip_network(f"{cidr.network_prefix}/{cidr.network_cidr}", strict=False)
            if new_network == existing_network or new_network.overlaps(existing_network):
                flash('This network CIDR already exists or overlaps with an existing network.', 'error')
                return redirect(url_for('views.infrastructure_ipam'))

        new_ipam_cidr = IPAM_CIDRS(network_prefix=network_prefix,
                                   network_cidr=int(network_cidr),
                                   location_id=location_id,
                                   tenant_id=tenant_id,
                                   zone_id=zone_id,
                                   environment_id=environment_id,
                                   application=application)
        db.session.add(new_ipam_cidr)
        db.session.flush()

        # Calculate usable hosts
        usable_hosts = list(new_network.hosts())
        
        # Iterate over usable hosts and add them to IPAM_HOSTS
        for host_ip in usable_hosts:
            new_ipam_host = IPAM_HOSTS(
                network_prefix=network_prefix,
                network_cidr=new_network.prefixlen,
                network_ip=str(host_ip),
                host_name='',  
                domain_id='',  
                application=application,
                role='',  
                location_id=location_id,
                tenant_id=tenant_id,
                zone_id=zone_id,
                environment_id=environment_id
            )
            db.session.add(new_ipam_host)
        
        db.session.commit()
        flash('IPAM CIDR and HOSTS added successfully!', 'success')
        return redirect(url_for('views.infrastructure_ipam'))

    locations = LocationItems.query.all()
    tenants = TenantItems.query.all()
    zones = ZoneItems.query.all()
    environments = EnvironmentTypes.query.all()
    ipam_cidrs = IPAM_CIDRS.query.all()
    
    return render_template('infrastructure_ipam.html', ipam_cidrs=ipam_cidrs, locations=locations, tenants=tenants, zones=zones, environments=environments)

@views.route('/delete-cidr/<int:id>', methods=['POST'])
@login_required
def delete_cidr(id):
    cidr_to_delete = IPAM_CIDRS.query.get_or_404(id)
    db.session.delete(cidr_to_delete)
    db.session.commit()
    flash('CIDR deleted successfully!', category='success')
    return redirect(url_for('views.infrastructure_ipam'))
    
@views.route('/edit-cidr/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_cidr(id):
    cidr = IPAM_CIDRS.query.get_or_404(id)

    if request.method == 'POST':
        cidr.network_cidr = request.form['network_cidr']
        db.session.commit()
        flash('CIDR updated successfully!', 'success')
        return redirect(url_for('views.infrastructure_ipam'))
        
    return render_template('edit_cidr.html', cidr=cidr)

    
@views.route('/edit-cidr-location/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_cidr_location(id):
    cidr = IPAM_CIDRS.query.get_or_404(id) 

    locations = LocationItems.query.all()  

    if request.method == 'POST':
        new_location_id = request.form.get('location')  
        cidr.location_id = new_location_id  
        db.session.commit()
        flash('CIDR location updated successfully!', 'success')  
        return redirect(url_for('views.infrastructure_ipam'))

    return render_template('edit_cidr_location.html', cidr=cidr, locations=locations)

    
@views.route('/edit-cidr-tenant/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_cidr_tenant(id):
    cidr = IPAM_CIDRS.query.get_or_404(id)  

    tenants = TenantItems.query.all() 

    if request.method == 'POST':
        new_tenant_id = request.form.get('tenant')  
        cidr.tenant_id = new_tenant_id  
        db.session.commit()
        flash('CIDR tenant updated successfully!', 'success') 
        return redirect(url_for('views.infrastructure_ipam'))

    return render_template('edit_cidr_tenant.html', cidr=cidr, tenants=tenants)

    
@views.route('/edit-cidr-zone/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_cidr_zone(id):
    cidr = IPAM_CIDRS.query.get_or_404(id)

    zones = ZoneItems.query.all()

    if request.method == 'POST':
        new_zone_id = request.form.get('zone')
        cidr.zone_id = new_zone_id
        db.session.commit()
        flash('CIDR zone updated successfully!', 'success')
        return redirect(url_for('views.infrastructure_ipam'))

    return render_template('edit_cidr_zone.html', cidr=cidr, zones=zones)
       
    
@views.route('/edit-cidr-env/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_cidr_env(id):
    cidr = IPAM_CIDRS.query.get_or_404(id)  

    environments = EnvironmentTypes.query.all()  

    if request.method == 'POST':
        new_environment_id = request.form.get('env')  
        cidr.environment_id = new_environment_id 
        db.session.commit()
        flash('CIDR environment updated successfully!', 'success')  
        return redirect(url_for('views.infrastructure_ipam'))

    return render_template('edit_cidr_env.html', cidr=cidr, environments=environments)

@views.route('/edit-cidr-app/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_cidr_app(id):
    cidr = IPAM_CIDRS.query.get_or_404(id)

    if request.method == 'POST':
        new_application = request.form.get('app')  
        cidr.application = new_application  
        db.session.commit()  
        flash('CIDR application updated successfully!', 'success') 
        return redirect(url_for('views.infrastructure_ipam')) 

    return render_template('edit_cidr_app.html', cidr=cidr)
  
    
@views.route('/infrastructure/ipam/<int:id>', methods=['GET', 'POST'])
@login_required
def infrastructure_ipam_hosts(id):
    
    cidr_id=id
    
    # Query the IPAM_CIDR by ID
    cidr = IPAM_CIDRS.query.get_or_404(id)
    network_prefix = cidr.network_prefix
    
    # Query IPAM_HOSTS by the network_prefix of the found CIDR
    hosts = IPAM_HOSTS.query.filter_by(network_prefix=network_prefix).all()
    
    # Render the template with the hosts data
    return render_template('infrastructure_ipam_hosts.html', cidr_id=cidr_id, hosts=hosts, network_prefix=network_prefix)

@views.route('/edit-ipam-host-name/<int:host_id>', methods=['GET', 'POST'])
@login_required
def edit_ipam_host_name(host_id):
    cidr_id = request.args.get('cidr_id', type=int)
    host = IPAM_HOSTS.query.get_or_404(host_id)
    
    if request.method == 'POST':
        host.host_name = request.form['host_name']
        db.session.commit()
        flash('Host name updated successfully!', 'success')
        return redirect(request.referrer)

    return render_template('edit_ipam_host_name.html', host=host)

@views.route('/edit-ipam-domain-name/<int:host_id>', methods=['GET', 'POST'])
@login_required
def edit_ipam_domain_name(host_id):
    cidr_id = request.args.get('cidr_id', default="") 
    host = IPAM_HOSTS.query.get_or_404(host_id)
    domains = DomainItems.query.all()

    if request.method == 'POST':
        # Get the domain ID from the form
        domain_id = request.form['domain']
        # Query the DomainItems table to get the corresponding domain_name
        domain_item = DomainItems.query.get(domain_id)
        if domain_item:
            # Assign the domain_name string to the domain_id field of IPAM_HOSTS
            host.domain_id = domain_item.domain_name
            db.session.commit()
            flash('Domain updated successfully!', 'success')
        else:
            flash('Domain not found!', 'error')

        return redirect(request.referrer)

    return render_template('edit_ipam_domain_name.html', host=host, domains=domains, cidr_id=cidr_id)

@views.route('/edit-ipam-application/<int:host_id>', methods=['GET', 'POST'])
@login_required
def edit_ipam_application(host_id):
    cidr_id = request.args.get('cidr_id', type=int)
    host = IPAM_HOSTS.query.get_or_404(host_id)
    
    if request.method == 'POST':
        host.application = request.form['app']
        db.session.commit()
        flash('Application updated successfully!', 'success')
        return redirect(request.referrer)

    return render_template('edit_ipam_application.html', host=host, cidr_id=cidr_id)


@views.route('/edit-ipam-role/<int:host_id>', methods=['GET', 'POST'])
@login_required
def edit_ipam_role(host_id):
    cidr_id = request.args.get('cidr_id', type=int)
    host = IPAM_HOSTS.query.get_or_404(host_id)
    
    if request.method == 'POST':
        host.role = request.form['role']
        db.session.commit()
        flash('Role updated successfully!', 'success')
        return redirect(request.referrer)

    return render_template('edit_ipam_role.html', host=host, cidr_id=cidr_id)
