from . import db
from .models import EnvironmentTypes, LocationItems, TenantItems, ZoneItems, DomainItems

def EnvironmentTypesTableInitiate():
    # Define the list of environment types
    environment_types = [
        "PRD",
        "NPRD",
        "TEST",
        "DEV",
        "SBOX"
    ]    
    
    # Iterate over the list of types
    for type_name in environment_types:
        
        # Check if the type already exists to avoid duplicates
        existing_type = EnvironmentTypes.query.filter_by(types=type_name).first()
        
        if not existing_type:
            # Create a new EnvironmentTypes instance for each type
            new_type = EnvironmentTypes(types=type_name)
            
            # Add the new type to the session
            db.session.add(new_type)

    # Commit the session to save the changes to the database
    db.session.commit()    

   
def LocationItemsTableInitiate():
    # Define the list of items
    location_items = [
        "global"
    ]    
    
    # Iterate over the list of items
    for item_name in location_items:
        
        # Check if the item already exists to avoid duplicates
        existing_item = LocationItems.query.filter_by(items=item_name).first()
        
        if not existing_item:
            # Create a new Location instance for each item
            new_item = LocationItems(items=item_name)
            
            # Add the new item to the session
            db.session.add(new_item)

    # Commit the session to save the changes to the database
    db.session.commit()  
    
def TenantItemsTableInitiate():
    # Define the list of items
    tenant_items = [
        "global"
    ]    
    
    # Iterate over the list of items
    for item_name in tenant_items:
        
        # Check if the item already exists to avoid duplicates
        existing_item = TenantItems.query.filter_by(tenant_name=item_name).first()
        
        if not existing_item:
            # Create a new Location instance for each item
            new_item = TenantItems(tenant_name=item_name)
            
            # Add the new item to the session
            db.session.add(new_item)

    # Commit the session to save the changes to the database
    db.session.commit()  
    
def ZoneItemsTableInitiate():
    # Define the list of items
    zone_items = [
        "FE",
        "MID",
        "BE",
        "BUR",
        "MGMT",
        "INFRA",
        "MISC"
    ]    
    
    # Iterate over the list of items
    for item_name in zone_items:
        
        # Check if the item already exists to avoid duplicates
        existing_item = ZoneItems.query.filter_by(zone_name=item_name).first()
        
        if not existing_item:
            # Create a new Zone instance for each item
            new_item = ZoneItems(zone_name=item_name)
            
            # Add the new item to the session
            db.session.add(new_item)

    # Commit the session to save the changes to the database
    db.session.commit()
    
def DomainItemsTableInitiate():
    # Define the list of items
    domain_items = [
        ".internal.das"
    ]    
    
    # Iterate over the list of items
    for item_name in domain_items:
        
        # Check if the item already exists to avoid duplicates
        existing_item = DomainItems.query.filter_by(domain_name=item_name).first()
        
        if not existing_item:
            # Create a new Domain instance for each item
            new_item = DomainItems(domain_name=item_name)
            
            # Add the new item to the session
            db.session.add(new_item)

    # Commit the session to save the changes to the database
    db.session.commit()      