from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKeyConstraint

class User(db.Model, UserMixin):
    id          = db.Column(db.Integer, primary_key=True)
    email       = db.Column(db.String(150), unique=True)
    password    = db.Column(db.String(150))
    username    = db.Column(db.String(150))

class InfrastructureCiscoAci(db.Model):
    __tablename__ = 'infrastructure_cisco_aci'
    id                          = db.Column(db.Integer, primary_key=True)
    fabric_name                 = db.Column(db.String(150), unique=True)
    target_apic                 = db.Column(db.String(100), unique=True)
    service_account_username    = db.Column(db.String(150))
    service_account_password    = db.Column(db.String(150))
    git_repository              = db.Column(db.String(255))  
    git_username                = db.Column(db.String(150))   
    git_email                   = db.Column(db.String(150))

    # Relationships
    switches                    = relationship('CiscoACISwitch', backref='infrastructure', lazy='dynamic')
    vpc_pairs                   = relationship('CiscoACISwitchVpcPairs', backref='infrastructure', lazy='dynamic')

class CiscoACISwitch(db.Model):
    __tablename__ = 'cisco_aci_switch'
    id                          = db.Column(db.Integer, primary_key=True)
    fabric_name                 = db.Column(db.String(150), db.ForeignKey('infrastructure_cisco_aci.fabric_name'), nullable=False)
    node_role                   = db.Column(db.String(50))
    pod_id                      = db.Column(db.Integer)
    node_id                     = db.Column(db.Integer, nullable=False)
    node_peer_id                = db.Column(db.Integer)
    serial_number               = db.Column(db.String(150), unique=True)
    node_name                   = db.Column(db.String(150))
    __table_args__              = (db.UniqueConstraint('fabric_name', 'node_id', name='_fabric_node_id_uc'),)
    
    # Relationships for VPC pairs pointing to this switch
    vpc_pairs_as_odd            = relationship('CiscoACISwitchVpcPairs', foreign_keys='[CiscoACISwitchVpcPairs.fabric_name, CiscoACISwitchVpcPairs.odd_node_id]', back_populates='odd_node')
    vpc_pairs_as_even           = relationship('CiscoACISwitchVpcPairs', foreign_keys='[CiscoACISwitchVpcPairs.fabric_name, CiscoACISwitchVpcPairs.even_node_id]', back_populates='even_node')

class CiscoACISwitchVpcPairs(db.Model):
    __tablename__ = 'cisco_aci_switch_vpc_pairs'
    id                          = db.Column(db.Integer, primary_key=True)
    fabric_name                 = db.Column(db.String(150), db.ForeignKey('infrastructure_cisco_aci.fabric_name'), nullable=False)
    odd_node_id                 = db.Column(db.Integer, nullable=False)
    even_node_id                = db.Column(db.Integer, nullable=False)
    group_id                    = db.Column(db.Integer)
    
    __table_args__              = (ForeignKeyConstraint(['fabric_name', 'odd_node_id'], ['cisco_aci_switch.fabric_name', 'cisco_aci_switch.node_id']), ForeignKeyConstraint(['fabric_name', 'even_node_id'], ['cisco_aci_switch.fabric_name', 'cisco_aci_switch.node_id']))
    
    # Relationships back to the switch
    odd_node                    = relationship('CiscoACISwitch', foreign_keys=[fabric_name, odd_node_id], back_populates='vpc_pairs_as_odd')
    even_node                   = relationship('CiscoACISwitch', foreign_keys=[fabric_name, even_node_id], back_populates='vpc_pairs_as_even')
    
class EnvironmentTypes(db.Model):
    __tablename__ = 'environment_types'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    types = db.Column(db.String(150), unique=True)
    
class LocationItems(db.Model):
    __tablename__ = 'location_items'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    items = db.Column(db.String(150), unique=True)
    
class TenantItems(db.Model):
    __tablename__ = 'tenant_items'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tenant_name = db.Column(db.String(150), unique=True)
    
class ZoneItems(db.Model):
    __tablename__ = 'zone_items'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    zone_name = db.Column(db.String(150), unique=True)       
    
'''    
class IPAM_CIDRS(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    network_prefix  = db.Column(db.String(150))
    network_cidr    = db.Column(db.Integer)
    location        = db.Column(db.String(150))
    tenant          = db.Column(db.String(150))
    zone            = db.Column(db.String(150))
    environment     = db.Column(db.String(150))
    application     = db.Column(db.String(150))
'''